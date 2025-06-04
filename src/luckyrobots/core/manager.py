"""
WebSocket server for distributed node communication.

This module provides a WebSocket server that acts as a central hub for distributed
nodes to discover each other and communicate.
"""

import msgpack
import asyncio
import logging
from typing import Dict, Set

from fastapi import FastAPI, WebSocket

from ..message.transporter import MessageType, TransportMessage

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("manager")

# FastAPI app
app = FastAPI()


class Manager:
    def __init__(self):
        # Dict of node name to WebSocket connection
        self.active_nodes: Dict[str, WebSocket] = {}

        # Dict of topic to set of subscribed node names
        self.subscriptions: Dict[str, Set[str]] = {}

        # Dict of service name to node name
        self.services: Dict[str, str] = {}

        # Lock for thread safety
        self.lock = asyncio.Lock()

    async def register_node(self, node_name: str, websocket: WebSocket):
        """Register a node with the manager"""
        async with self.lock:
            self.active_nodes[node_name] = websocket
            logger.info(f"Node registered: {node_name}")

    async def unregister_node(self, node_name: str):
        """Unregister a node from the manager"""
        async with self.lock:
            # Remove the node from active nodes
            if node_name in self.active_nodes:
                del self.active_nodes[node_name]

            # Remove the node from subscriptions
            for topic, nodes in list(self.subscriptions.items()):
                if node_name in nodes:
                    nodes.remove(node_name)
                    if not nodes:
                        del self.subscriptions[topic]

            # Remove the node from services
            for service, provider in list(self.services.items()):
                if provider == node_name:
                    del self.services[service]

            logger.info(f"Node unregistered: {node_name}")

    async def subscribe(self, node_name: str, topic: str):
        """Subscribe a node to a topic"""
        async with self.lock:
            if topic not in self.subscriptions:
                self.subscriptions[topic] = set()
            self.subscriptions[topic].add(node_name)
            logger.debug(f"Node {node_name} subscribed to topic: {topic}")

    async def unsubscribe(self, node_name: str, topic: str):
        """Unsubscribe a node from a topic"""
        async with self.lock:
            if topic in self.subscriptions and node_name in self.subscriptions[topic]:
                self.subscriptions[topic].remove(node_name)
                if not self.subscriptions[topic]:
                    del self.subscriptions[topic]
                logger.debug(f"Node {node_name} unsubscribed from topic: {topic}")

    async def register_service(self, node_name: str, service_name: str):
        """Register a service with the manager"""
        async with self.lock:
            self.services[service_name] = node_name
            logger.debug(f"Service registered: {service_name} by node {node_name}")

    async def unregister_service(self, node_name: str, service_name: str):
        """Unregister a service from the manager"""
        async with self.lock:
            if (
                service_name in self.services
                and self.services[service_name] == node_name
            ):
                del self.services[service_name]
                logger.debug(f"Service unregistered: {service_name}")

    async def route_message(self, message: TransportMessage):
        """Route a message to the appropriate nodes"""
        try:
            # Handle message based on its type
            if message.msg_type == MessageType.PUBLISH:
                await self._route_publish(message)
            elif message.msg_type == MessageType.SERVICE_REQUEST:
                await self._route_service_request(message)
            elif message.msg_type == MessageType.SERVICE_RESPONSE:
                await self._route_service_response(message)
            else:
                # For other message types, just log and ignore
                logger.debug(
                    f"Received message of type {message.msg_type}, not routing"
                )
        except Exception as e:
            logger.error(f"Error routing message: {e}")

    async def _route_publish(self, message: TransportMessage):
        """Route a publish message to subscribed nodes"""
        topic = message.topic_or_service
        sender_node = message.node_name

        # Get the list of subscribed nodes for this topic
        async with self.lock:
            subscribers = self.subscriptions.get(topic, set()).copy()

        # Send the message to all subscribers except the sender
        for node_name in subscribers:
            if node_name != sender_node and node_name in self.active_nodes:
                try:
                    await self.active_nodes[node_name].send(
                        msgpack.dumps(message.dict())
                    )
                except Exception as e:
                    logger.error(f"Error sending to node {node_name}: {e}")

    async def _route_service_request(self, message: TransportMessage):
        """Route a service request to the appropriate node"""
        service_name = message.topic_or_service
        requester_node = message.node_name

        # Find the service provider
        async with self.lock:
            provider_node = self.services.get(service_name)

        if not provider_node:
            # Service not found, send error response
            error_response = TransportMessage(
                msg_type=MessageType.SERVICE_RESPONSE,
                node_name="node_server",
                topic_or_service=service_name,
                message_id=message.message_id,
                data={"error": f"Service {service_name} not found"},
            )

            if requester_node in self.active_nodes:
                try:
                    await self.active_nodes[requester_node].send(
                        msgpack.dumps(error_response.dict())
                    )
                except Exception as e:
                    logger.error(
                        f"Error sending error response to node {requester_node}: {e}"
                    )
            return

        # Forward the request to the service provider
        if provider_node in self.active_nodes:
            try:
                await self.active_nodes[provider_node].send_bytes(
                    msgpack.dumps(message.dict())
                )
            except Exception as e:
                logger.error(
                    f"Error forwarding service request to node {provider_node}: {e}"
                )
                raise e
        else:
            # Provider not connected, send error response
            error_response = TransportMessage(
                msg_type=MessageType.SERVICE_RESPONSE,
                node_name="node_server",
                topic_or_service=service_name,
                message_id=message.message_id,
                data={"error": f"Service provider {provider_node} is not connected"},
            )

            if requester_node in self.active_nodes:
                try:
                    await self.active_nodes[requester_node].send(
                        msgpack.dumps(error_response.dict())
                    )
                except Exception as e:
                    logger.error(
                        f"Error sending error response to node {requester_node}: {e}"
                    )

    async def _route_service_response(self, message: TransportMessage):
        """Route a service response to the appropriate node"""
        service_name = message.topic_or_service
        message_id = message.message_id

        if not message_id:
            logger.error(f"Service response missing message_id: {message}")
            return

        # Extract requester node name from message_id (format: node_name_service_name_timestamp_id)
        try:
            parts = message_id.split("_")
            requester_node = parts[0]

            # For namespaced nodes, reconstruct the full name
            if len(parts) > 4:  # There are more underscores in the node name
                requester_node = "_".join(
                    parts[:-3]
                )  # Everything except the last 3 parts
        except Exception as e:
            logger.error(
                f"Error extracting requester node from message_id {message_id}: {e}"
            )
            return

        # Forward the response to the requester
        if requester_node in self.active_nodes:
            try:
                await self.active_nodes[requester_node].send(
                    msgpack.dumps(message.dict())
                )
            except Exception as e:
                logger.error(
                    f"Error forwarding service response to node {requester_node}: {e}"
                )
        else:
            logger.warning(
                f"Requester node {requester_node} not connected for response {message_id}"
            )
