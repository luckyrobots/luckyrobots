"""
Node implementation with built-in distributed communication.

This module provides a Node class with integrated WebSocket-based distributed
communication for building ROS-like systems.
"""

import asyncio
import logging
import threading
import uuid
from typing import Any, Callable, Dict, Type

from ..message.pubsub import Publisher, Subscriber
from ..message.srv.client import ServiceClient
from ..message.srv.service import ServiceServer, ServiceError
from ..message.transporter import Transporter
from ..utils.event_loop import run_coroutine
from .parameters import get_param, has_param, set_param

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("node")


class Node:
    """Base class for all nodes in the LuckyRobots framework with distributed communication"""

    def __init__(
        self, name: str, namespace: str = "", host: str = None, port: int = None
    ):
        """Initialize a new node.

        Args:
            name: The name of the node
            namespace: Optional namespace for the node
            host: Host to connect to (defaults to parameters)
            port: Port to connect to (defaults to parameters)
        """
        self.name = name
        self.namespace = namespace.strip("/")
        self.full_name = (
            f"/{self.namespace}/{self.name}" if self.namespace else f"/{self.name}"
        )

        # Get host and port from parameters if not provided
        self.host = host or get_param("core/host", "localhost")
        self.port = port or get_param("core/port", 3000)

        # Create a unique ID for this node instance
        self.instance_id = str(uuid.uuid4())

        self._publishers: Dict[str, Publisher] = {}
        self._subscribers: Dict[str, Subscriber] = {}
        self._services: Dict[str, ServiceServer] = {}
        self._clients: Dict[str, ServiceClient] = {}
        self._running = False
        self._shutdown_event = threading.Event()

        # Initialize WebSocket transporter
        # Note: We connect to the same server for all communications
        self.transporter = Transporter(
            node_name=self.full_name,
            uuid=self.instance_id,
            host=self.host,
            port=self.port,
        )

        logger.info(f"Created node: {self.full_name} (ID: {self.instance_id})")

    def get_qualified_name(self, name: str) -> str:
        """Convert a relative name to a fully qualified name.

        Args:
            name: Relative or absolute name

        Returns:
            Fully qualified name
        """
        if name.startswith("/"):
            return name

        return f"{self.full_name}/{name}"

    def create_publisher(
        self, message_type: Type, topic: str, queue_size: int = 10
    ) -> Publisher:
        """Create a publisher for a topic.

        Args:
            message_type: The type of messages to publish
            topic: The topic to publish on
            queue_size: Maximum queue size for messages

        Returns:
            The created publisher
        """
        qualified_topic = self.get_qualified_name(topic)
        publisher = Publisher(qualified_topic, message_type, queue_size)
        self._publishers[qualified_topic] = publisher

        # Wrap the publish method to distribute messages
        original_publish = publisher.publish

        def distributed_publish(message):
            # Publish locally
            original_publish(message)

            # Publish to remote nodes via transport layer
            self.transporter.publish(qualified_topic, message)

        publisher.publish = distributed_publish

        return publisher

    def create_subscription(
        self,
        message_type: Type,
        topic: str,
        callback: Callable[[Any], None],
        queue_size: int = 10,
    ) -> Subscriber:
        """Create a subscriber for a topic.

        Args:
            message_type: The type of messages to expect
            topic: The topic to subscribe to
            callback: The function to call when a message is received
            queue_size: Maximum queue size for messages

        Returns:
            The created subscriber
        """
        qualified_topic = self.get_qualified_name(topic)
        subscriber = Subscriber(qualified_topic, message_type, callback, queue_size)
        self._subscribers[qualified_topic] = subscriber

        # Create a wrapper for the callback that handles message type conversion
        def transport_callback(data):
            # Try to convert the data to the expected message type
            if hasattr(message_type, "parse_obj"):
                try:
                    message = message_type.parse_obj(data)
                    callback(message)
                except Exception as e:
                    logger.error(f"Error converting message data: {e}")
            else:
                # If the message type doesn't have parse_obj, pass the data directly
                callback(data)

        # Subscribe to the topic on the transport layer
        self.transporter.subscribe(qualified_topic, transport_callback)

        return subscriber

    def create_client(self, service_type: Type, service_name: str) -> ServiceClient:
        """Create a client for a server.

        Args:
            service_type: The type of service to connect to
            service_name: The name of the service to connect to

        Returns:
            The created client
        """
        qualified_name = self.get_qualified_name(service_name)
        client = ServiceClient(service_type, qualified_name)
        self._clients[qualified_name] = client

        # Store the original call method
        original_call = client.call

        # Create a new call method that tries both local and remote services
        async def distributed_call(request, timeout=30.0):
            try:
                # Try to call the service locally first
                return await original_call(request, qualified_name, timeout=timeout)
            except Exception as e:
                logger.debug(f"Local service call failed: {e}, trying remote service")

                # Convert the request to a dictionary
                if hasattr(request, "dict"):
                    request_data = request.dict()
                elif hasattr(request, "to_dict"):
                    request_data = request.to_dict()
                else:
                    request_data = request

                # Call the service through the transport
                try:
                    response_data = await self.transporter.call_service(
                        qualified_name, request_data, timeout=timeout
                    )

                    # Check if response has an error
                    if isinstance(response_data, dict) and "error" in response_data:
                        raise ServiceError(
                            response_data.get("error", "Unknown service error")
                        )

                    # Convert the response to the expected response type
                    response_type = getattr(service_type, "Response", None)

                    if response_type and hasattr(response_type, "parse_obj"):
                        try:
                            return response_type.parse_obj(response_data)
                        except Exception as parse_error:
                            logger.error(
                                f"Error converting response data: {parse_error}"
                            )
                            raise ServiceError(f"Error parsing response: {parse_error}")
                    else:
                        # If no specific response type or parsing failed, return the data directly
                        return response_data
                except Exception as remote_error:
                    logger.error(f"Remote service call failed: {remote_error}")
                    raise ServiceError(f"Remote service call failed: {remote_error}")

        # Replace the call method
        client.call = distributed_call

        return client

    async def create_service(
        self, service_type: Type, service_name: str, handler: Callable[[Any], Any]
    ) -> ServiceServer:
        """Create a service for a service name.

        Args:
            service_name: The name of the service to create a server for
            service_type: The type of service the server accepts
            handler: The function to call when a request is received

        Returns:
            The created service
        """
        qualified_name = self.get_qualified_name(service_name)
        service = ServiceServer(service_type, qualified_name, handler)
        self._services[qualified_name] = service

        # Create a wrapper for the handler that handles message type conversion and async
        async def transport_handler(request_data):
            # Try to convert the request data to the expected request type
            request_type = getattr(service_type, "Request", service_type)

            if hasattr(request_type, "parse_obj"):
                try:
                    request = request_type.parse_obj(request_data)
                except Exception as e:
                    logger.error(f"Error converting request data: {e}")
                    return {"error": str(e), "success": False}
            else:
                # If the request type doesn't have parse_obj, pass the data directly
                request = request_data

            # Call the original handler and properly handle async
            try:
                if asyncio.iscoroutinefunction(handler):
                    # Await the coroutine directly
                    response = await handler(request)
                else:
                    # Run synchronous handler
                    response = handler(request)

                # If the response is also a coroutine, await it (sometimes happens with wrapped handlers)
                if asyncio.iscoroutine(response):
                    response = await response

                # Convert the response to a dictionary
                if hasattr(response, "dict"):
                    return response.dict()
                elif isinstance(response, dict):
                    return response
                else:
                    # Try to convert to dict
                    try:
                        return dict(response)
                    except (TypeError, ValueError):
                        return {"value": response, "success": True}
            except Exception as e:
                logger.error(f"Error in service handler: {e}")
                return {"error": str(e), "success": False}

        # Register with transport using the async-aware wrapper
        self.transporter.register_service(qualified_name, transport_handler)

        return service

    def create_service_client(
        self,
        service_type: Type,
        service_name: str,
        host: str = "localhost",
        port: int = 3000,
    ) -> ServiceClient:
        """Create a service client for a service name.

        Args:
            service_type: The type of service to connect to
            service_name: The name of the service to connect to
            host: WebSocket server host
            port: WebSocket server port

        Returns:
            The created service client
        """
        qualified_name = self.get_qualified_name(service_name)
        client = ServiceClient(service_type, qualified_name, host, port)
        self._clients[qualified_name] = client
        return client

    def get_param(self, name: str, default: Any = None) -> Any:
        """Get a parameter value.

        Args:
            name: Parameter name
            default: Default value to return if parameter doesn't exist

        Returns:
            The parameter value, or default if not found
        """
        # Try node-specific parameter first
        node_param = f"{self.full_name}/{name}"
        if has_param(node_param):
            return get_param(node_param)

        # Fall back to global parameter
        return get_param(name, default)

    def set_param(self, name: str, value: Any) -> None:
        """Set a parameter value.

        Args:
            name: Parameter name
            value: Parameter value
        """
        # Always set as node-specific parameter
        node_param = f"{self.full_name}/{name}"
        set_param(node_param, value)

    def start(self) -> None:
        """Start the node.

        This method should be overridden by subclasses to implement
        node-specific initialization and setup.
        """
        self._running = True
        run_coroutine(self._setup_async())
        logger.info(f"Node {self.full_name} started")

    async def _setup_async(self):
        """Setup the node.

        This method should be overridden by subclasses to implement
        node-specific setup.
        """
        pass

    def spin(self) -> None:
        """Spin the node.

        This method blocks until the node is shutdown.
        """
        logger.info(f"Node {self.full_name} spinning")
        self._shutdown_event.wait()
        logger.info(f"Node {self.full_name} stopped spinning")

    def shutdown(self) -> None:
        """Shutdown the node.

        This method should be overridden by subclasses to implement
        node-specific cleanup.
        """
        self._running = False

        # Shutdown WebSocket transporter
        self.transporter.shutdown()

        self._shutdown_event.set()
        logger.info(f"Node {self.full_name} shutdown")
