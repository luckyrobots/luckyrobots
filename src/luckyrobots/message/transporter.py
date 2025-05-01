"""
WebSocket-based transport layer for the LuckyRobots messaging system.

This module provides the WebSocketTransport class which handles message
serialization and communication over WebSockets between distributed nodes.
"""

import asyncio
import json
import logging
import threading
import time
import uuid
import websockets
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

from concurrent import futures
from pydantic import BaseModel, ValidationError

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("transport")


class MessageType(str, Enum):
    """Types of messages that can be sent over the transport layer"""

    PUBLISH = "publish"
    SUBSCRIBE = "subscribe"
    UNSUBSCRIBE = "unsubscribe"
    SERVICE_REQUEST = "service_request"
    SERVICE_RESPONSE = "service_response"
    SERVICE_REGISTER = "service_register"
    SERVICE_UNREGISTER = "service_unregister"
    NODE_ANNOUNCE = "node_announce"
    NODE_SHUTDOWN = "node_shutdown"


class TransportMessage(BaseModel):
    """Message format for transport layer communication"""

    msg_type: MessageType
    node_name: str
    uuid: str
    topic_or_service: str
    data: Optional[dict] = None
    message_id: Optional[str] = None  # For correlating requests and responses


class Transporter:
    """WebSocket-based transport layer for distributed communication"""

    def __init__(
        self,
        node_name: str,
        uuid: str,
        host: str = "localhost",
        port: int = 3000,
        reconnect_interval: float = 5.0,
    ):
        """Initialize the transport layer.

        Args:
            node_name: The name of the node this transport belongs to
            uuid: The unique identifier for the node
            host: Host name or IP address of the WebSocket server
            port: Port number of the WebSocket server
            reconnect_interval: Time between reconnection attempts in seconds
        """
        self.node_name = node_name
        self.uuid = uuid
        self.server_uri = f"ws://{host}:{port}/nodes"
        self.reconnect_interval = reconnect_interval

        # Websocket connections
        self._connection = None
        self._connected = asyncio.Event()
        self._connection_task = None
        self._should_run = True

        # Message handlers
        self._topic_handlers: Dict[str, List[Callable[[Any], None]]] = {}
        self._service_handlers: Dict[str, Callable[[Any], Any]] = {}
        self._response_futures: Dict[str, asyncio.Future] = {}

        self._start_background_tasks()

    def _start_background_tasks(self):
        """Start background tasks for handling connections and messages"""
        # Create a new event loop for the background thread
        self._loop = asyncio.new_event_loop()

        # Create and start the thread
        self._thread = threading.Thread(target=self._run_event_loop, daemon=True)
        self._thread.start()

        # Wait for the loop to be set up
        while not hasattr(self, "_loop_ready") or not self._loop_ready:
            time.sleep(0.01)

    def _run_event_loop(self):
        """Run the event loop in the background thread"""
        asyncio.set_event_loop(self._loop)
        self._loop_ready = True

        # Start the connection task
        self._connection_task = self._loop.create_task(self._maintain_connection())

        # Run the event loop
        self._loop.run_forever()

    async def _maintain_connection(self):
        """Maintain a WebSocket connection to the server, reconnecting as needed"""
        while self._should_run:
            try:
                async with websockets.connect(self.server_uri) as websocket:
                    self._connection = websocket
                    self._connected.set()
                    logger.info(f"Node {self.node_name} connected to WebSocket server")

                    # Announce this node
                    await self._announce_node()

                    # Re-subscribe to all topics
                    await self._resubscribe()

                    # Re-register all services
                    await self._reregister_services()

                    # Handle messages
                    await self._handle_messages()
            except (websockets.ConnectionClosed, ConnectionRefusedError) as e:
                self._connected.clear()
                self._connection = None
                logger.warning(
                    f"WebSocket connection lost: {e}. Reconnecting in {self.reconnect_interval} seconds"
                )
                await asyncio.sleep(self.reconnect_interval)
            except Exception as e:
                logger.error(f"Unexpected error in WebSocket connection: {e}")
                self._connected.clear()
                self._connection = None
                await asyncio.sleep(self.reconnect_interval)

    async def _announce_node(self):
        """Announce this node to the network"""
        message = TransportMessage(
            msg_type=MessageType.NODE_ANNOUNCE,
            node_name=self.node_name,
            uuid=self.uuid,
            topic_or_service="",
        )
        await self._send_message(message)

    async def _resubscribe(self):
        """Re-subscribe to all topics after reconnection"""
        for topic in self._topic_handlers:
            message = TransportMessage(
                msg_type=MessageType.SUBSCRIBE,
                node_name=self.node_name,
                uuid=self.uuid,
                topic_or_service=topic,
            )
            await self._send_message(message)

    async def _reregister_services(self):
        """Re-register all services after reconnection"""
        for service in self._service_handlers:
            message = TransportMessage(
                msg_type=MessageType.SERVICE_REGISTER,
                node_name=self.node_name,
                uuid=self.uuid,
                topic_or_service=service,
            )
            await self._send_message(message)

    async def _handle_messages(self):
        """Handle incoming messages from the WebSocket connection"""
        while self._connection and self._should_run:
            try:
                message_text = await self._connection.recv()
                try:
                    # Parse the message
                    message_data = json.loads(message_text)
                    message = TransportMessage(**message_data)

                    # Handle the message based on its type
                    await self._process_message(message)
                except (json.JSONDecodeError, ValidationError) as e:
                    logger.error(f"Error parsing message: {e}, message: {message_text}")
            except websockets.ConnectionClosed:
                logger.info("WebSocket connection closed")
                break
            except Exception as e:
                logger.error(f"Error handling message: {e}")

    async def _process_message(self, message: TransportMessage):
        """Process an incoming message based on its type.

        Args:
            message: The message to process
        """
        if message.msg_type == MessageType.PUBLISH:
            # Handle published messages
            if message.topic_or_service in self._topic_handlers:
                for handler in self._topic_handlers[message.topic_or_service]:
                    try:
                        handler(message.data)
                    except Exception as e:
                        logger.error(f"Error in message handler: {e}")

        elif message.msg_type == MessageType.SERVICE_REQUEST:
            # Handle service requests
            if message.topic_or_service in self._service_handlers:
                handler = self._service_handlers[message.topic_or_service]
                try:
                    # Process the request
                    result = await self._run_service_handler(handler, message.data)

                    # Send the response
                    response = TransportMessage(
                        msg_type=MessageType.SERVICE_RESPONSE,
                        node_name=self.node_name,
                        uuid=self.uuid,
                        topic_or_service=message.topic_or_service,
                        message_id=message.message_id,
                        data=result,
                    )
                    await self._send_message(response)
                except Exception as e:
                    logger.error(f"Error handling service request: {e}")
                    # Send error response
                    error_response = TransportMessage(
                        msg_type=MessageType.SERVICE_RESPONSE,
                        node_name=self.node_name,
                        uuid=self.uuid,
                        topic_or_service=message.topic_or_service,
                        message_id=message.message_id,
                        data={"error": str(e), "success": False},
                    )
                    await self._send_message(error_response)

        elif message.msg_type == MessageType.SERVICE_RESPONSE:
            # Handle service responses
            if message.message_id in self._response_futures:
                future = self._response_futures[message.message_id]
                if not future.done():
                    future.set_result(message.data)
                del self._response_futures[message.message_id]

    async def _run_service_handler(self, handler: Callable, request_data: dict) -> dict:
        """Run a service handler function.

        Args:
            handler: The handler function
            request_data: The request data

        Returns:
            The response data
        """
        try:
            # If the handler is asynchronous, await it
            if asyncio.iscoroutinefunction(handler):
                # This part is correct, but we need to ensure the result is properly awaited
                result = await handler(request_data)
            else:
                # Run non-async handler in a thread pool
                loop = asyncio.get_running_loop()
                result = await loop.run_in_executor(None, handler, request_data)

            # Check if the result itself is a coroutine (sometimes happens with wrapped functions)
            if asyncio.iscoroutine(result):
                result = await result

            # Ensure result is JSON serializable
            if hasattr(result, "dict"):
                return result.dict()
            elif isinstance(result, dict):
                return result
            else:
                # Try to convert to dict if possible
                try:
                    return dict(result)
                except (TypeError, ValueError):
                    return {"value": result, "success": True}
        except Exception as e:
            logger.error(f"Error in service handler: {e}")
            raise

    async def _send_message(self, message: TransportMessage):
        """Send a message over the WebSocket connection.

        Args:
            message: The message to send
        """
        if not self._connection:
            await self._connected.wait()

        try:
            await self._connection.send(message.json())
        except websockets.ConnectionClosed:
            logger.warning("Could not send message, connection closed")
            self._connected.clear()
        except Exception as e:
            logger.error(f"Error sending message: {e}")

    def publish(self, topic: str, message: Any):
        """Publish a message to a topic.

        Args:
            topic: The topic to publish to
            message: The message to publish
        """
        # Ensure message is serializable
        if hasattr(message, "dict"):
            data = message.dict()
        elif hasattr(message, "to_dict"):
            data = message.to_dict()
        elif isinstance(message, dict):
            data = message
        else:
            data = {"value": message}

        transport_message = TransportMessage(
            msg_type=MessageType.PUBLISH,
            node_name=self.node_name,
            uuid=self.uuid,
            topic_or_service=topic,
            data=data,
        )

        # Schedule the send operation in the event loop
        future = asyncio.run_coroutine_threadsafe(
            self._send_message(transport_message), self._loop
        )
        try:
            # Wait for a short time to catch immediate errors
            future.result(timeout=0.1)
        except futures.TimeoutError:
            # This is expected - we don't need to wait for completion
            pass
        except Exception as e:
            logger.error(f"Error publishing to topic {topic}: {e}")

    def subscribe(self, topic: str, callback: Callable[[Any], None]):
        """Subscribe to a topic.

        Args:
            topic: The topic to subscribe to
            callback: The callback function to call when a message is received
        """
        # Add the callback to the topic handlers
        if topic not in self._topic_handlers:
            self._topic_handlers[topic] = []
        self._topic_handlers[topic].append(callback)

        # Send a subscribe message
        transport_message = TransportMessage(
            msg_type=MessageType.SUBSCRIBE,
            node_name=self.node_name,
            uuid=self.uuid,
            topic_or_service=topic,
        )

        # Schedule the send operation in the event loop
        future = asyncio.run_coroutine_threadsafe(
            self._send_message(transport_message), self._loop
        )
        try:
            # Wait for a short time to catch immediate errors
            future.result(timeout=0.1)
        except futures.TimeoutError:
            # This is expected - we don't need to wait for completion
            pass
        except Exception as e:
            logger.error(f"Error subscribing to topic {topic}: {e}")

    def unsubscribe(self, topic: str, callback: Callable[[Any], None]):
        """Unsubscribe from a topic.

        Args:
            topic: The topic to unsubscribe from
            callback: The callback function to remove
        """
        # Remove the callback from the topic handlers
        if topic not in self._topic_handlers:
            return

        if callback in self._topic_handlers[topic]:
            self._topic_handlers[topic].remove(callback)

        # If no more handlers, send an unsubscribe message
        if not self._topic_handlers[topic]:
            transport_message = TransportMessage(
                msg_type=MessageType.UNSUBSCRIBE,
                node_name=self.node_name,
                uuid=self.uuid,
                topic_or_service=topic,
            )

            # Schedule the send operation in the event loop
            future = asyncio.run_coroutine_threadsafe(
                self._send_message(transport_message), self._loop
            )
            try:
                # Wait for a short time to catch immediate errors
                future.result(timeout=0.1)
            except futures.TimeoutError:
                # This is expected - we don't need to wait for completion
                pass
            except Exception as e:
                logger.error(f"Error unsubscribing from topic {topic}: {e}")

            # Remove the empty list
            del self._topic_handlers[topic]

    def register_service(self, service_name: str, handler: Callable[[Any], Any]):
        """Register a service.

        Args:
            service_name: The name of the service
            handler: The handler function to call when a request is received
        """
        # Add the handler to the service handlers
        self._service_handlers[service_name] = handler

        # Send a service register message
        transport_message = TransportMessage(
            msg_type=MessageType.SERVICE_REGISTER,
            node_name=self.node_name,
            uuid=self.uuid,
            topic_or_service=service_name,
        )

        # Schedule the send operation in the event loop
        future = asyncio.run_coroutine_threadsafe(
            self._send_message(transport_message), self._loop
        )

        try:
            # Wait for a short time to catch immediate errors
            future.result(timeout=0.1)
        except futures.TimeoutError:
            # This is expected - we don't need to wait for completion
            pass
        except Exception as e:
            logger.error(f"Error registering service {service_name}: {e}")

    def unregister_service(self, service_name: str):
        """Unregister a service.

        Args:
            service_name: The name of the service
        """
        # Remove the handler from the service handlers
        if service_name in self._service_handlers:
            del self._service_handlers[service_name]

            # Send a service unregister message
            transport_message = TransportMessage(
                msg_type=MessageType.SERVICE_UNREGISTER,
                node_name=self.node_name,
                uuid=self.uuid,
                topic_or_service=service_name,
            )

            # Schedule the send operation in the event loop
            future = asyncio.run_coroutine_threadsafe(
                self._send_message(transport_message), self._loop
            )
            try:
                # Wait for a short time to catch immediate errors
                future.result(timeout=0.1)
            except futures.TimeoutError:
                # This is expected - we don't need to wait for completion
                pass
            except Exception as e:
                logger.error(f"Error unregistering service {service_name}: {e}")

    async def call_service(
        self, service_name: str, request: Any, timeout: float = 30.0
    ) -> Any:
        """Call a service.

        Args:
            service_name: The name of the service
            request: The request data
            timeout: Timeout in seconds

        Returns:
            The response data

        Raises:
            TimeoutError: If the service call times out
            Exception: If an error occurs during the service call
        """
        # Ensure request is serializable
        if hasattr(request, "dict"):
            data = request.dict()
        elif hasattr(request, "to_dict"):
            data = request.to_dict()
        elif isinstance(request, dict):
            data = request
        else:
            data = {"value": request}

        # Generate a unique message ID
        message_id = f"{self.node_name}_{service_name}_{time.time()}_{uuid.uuid4().hex}"

        # Create a future for the response within the same event loop
        loop = asyncio.get_running_loop()
        future = loop.create_future()
        self._response_futures[message_id] = future

        # Create the service request message
        transport_message = TransportMessage(
            msg_type=MessageType.SERVICE_REQUEST,
            node_name=self.node_name,
            uuid=self.uuid,
            topic_or_service=service_name,
            message_id=message_id,
            data=data,
        )

        # Send the message directly within the same event loop
        try:
            await self._send_message(transport_message)
        except Exception as e:
            # Clean up and propagate the error
            if message_id in self._response_futures:
                del self._response_futures[message_id]
            raise Exception(f"Failed to send service request: {e}")

        try:
            # Wait for the response with timeout
            return await asyncio.wait_for(future, timeout)
        except asyncio.TimeoutError:
            # Remove the future if it times out
            if message_id in self._response_futures:
                del self._response_futures[message_id]
            raise TimeoutError(
                f"Service call to {service_name} timed out after {timeout} seconds"
            )
        except Exception as e:
            # Remove the future on any error
            if message_id in self._response_futures:
                del self._response_futures[message_id]
            raise Exception(f"Service call error: {e}")

    def shutdown(self):
        """Shutdown the transport layer"""
        self._should_run = False

        # Send a node shutdown message
        transport_message = TransportMessage(
            msg_type=MessageType.NODE_SHUTDOWN,
            node_name=self.node_name,
            uuid=self.uuid,
            topic_or_service="",
        )

        # Schedule the send operation in the event loop
        try:
            future = asyncio.run_coroutine_threadsafe(
                self._send_message(transport_message), self._loop
            )

            # Wait for the message to be sent
            future.result(timeout=1.0)
        except Exception:
            pass

        # Stop the event loop
        self._loop.call_soon_threadsafe(self._loop.stop)

        # Wait for the thread to finish
        self._thread.join(timeout=2.0)
