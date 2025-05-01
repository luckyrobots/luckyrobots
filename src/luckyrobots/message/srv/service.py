"""Enhanced server implementation for request/response patterns.

This module provides an improved ServiceServer class for implementing request/response patterns
with timeout handling, error handling, and server discovery.
"""

import asyncio
import logging
import time
from typing import Any, Callable, Dict, Generic, List, Optional, Type, TypeVar, Union

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("service")

T = TypeVar("T")  # Request type
R = TypeVar("R")  # Response type


class ServiceError(Exception):
    """Base exception for service-related errors"""

    pass


class ServiceTimeoutError(ServiceError):
    """Exception raised when a service call times out"""

    pass


class ServiceNotFoundError(ServiceError):
    """Exception raised when a service is not found"""

    pass


class ServiceHandlerError(ServiceError):
    """Exception raised when a service handler raises an exception"""

    pass


class ServiceServer(Generic[T, R]):
    """Enhanced service implementation with timeout and error handling"""

    # Class dictionary to keep track of all services
    _services: Dict[str, "ServiceServer"] = {}
    _lock = asyncio.Lock()

    def __init__(
        self, service_type: Type[T], service_name: str, handler: Callable[[T], R]
    ):
        """Initialize a new service.

        Args:
            service_type: The type of service the server accepts
            service_name: The name of the service
            handler: The function to call when a request is received
        """
        self._handler: Optional[Callable[[T], R]] = None

        self.service_type = service_type
        self.service_name = service_name

        self.set_handler(handler)

        # Register this service in the class dictionary
        ServiceServer._services[service_name] = self

        logger.debug(f"Created service: {service_name}")

    def set_handler(self, handler: Callable[[T], R]) -> None:
        """Set the service handler function.

        Args:
            handler: The function to call when the server is called
        """
        self._handler = handler
        logger.debug(f"Set handler for service: {self.service_name}")

    async def call(self, request: T, service_name: str, timeout: float = 30.0) -> R:
        """Call the service with a request.

        Args:
            request: The request to send to the service
            service_name: The name of the service to call
            timeout: Timeout in seconds

        Returns:
            The response from the service

        Raises:
            ServiceTimeoutError: If the service call times out
            ServiceHandlerError: If the service handler raises an exception
            ServiceNotFoundError: If no handler is set for the service
        """
        if self.service_name != service_name:
            raise ValueError(
                f"Service name mismatch. Expected {self.service_name}, got {service_name}"
            )

        # Validate the request type if possible
        request_type = getattr(self.service_type, "Request", self.service_type)
        if not isinstance(request, request_type):
            raise TypeError(
                f"Expected request of type {request_type.__name__}, got {type(request).__name__}"
            )

        if self._handler is None:
            raise ServiceNotFoundError(
                f"No handler set for service {self.service_name}"
            )

        try:
            # Run the handler with timeout
            return await asyncio.wait_for(self._run_handler(request), timeout=timeout)
        except asyncio.TimeoutError:
            raise ServiceTimeoutError(
                f"Service call to {self.service_name} timed out after {timeout} seconds"
            )

    async def _run_handler(self, request: T) -> R:
        """Run the server handler and handle exceptions.

        Args:
            request: The request to send to the server

        Returns:
            The response from the server

        Raises:
            ServiceHandlerError: If the server handler raises an exception
        """
        try:
            # If handler is already a coroutine function, await it
            if asyncio.iscoroutinefunction(self._handler):
                result = await self._handler(request)
            else:
                # Run non-async handler in a thread pool
                loop = asyncio.get_event_loop()
                result = await loop.run_in_executor(None, self._handler, request)

            # Type check the result if possible
            response_type = getattr(self.service_type, "Response", None)
            if response_type and not isinstance(result, response_type):
                raise TypeError(
                    f"Service {self.service_name} returned {type(result).__name__}, expected {response_type.__name__}"
                )

            return result
        except Exception as e:
            logger.error(f"Error in service handler for {self.service_name}: {e}")
            raise ServiceHandlerError(
                f"Service handler for {self.service_name} raised an exception: {e}"
            )

    @classmethod
    def get_service(cls, service_name: str) -> Optional["ServiceServer"]:
        """Get a service by name.

        Args:
            name: The name of the server

        Returns:
            The service with the specified name, or None if not found
        """
        return cls._services.get(service_name)

    @classmethod
    def get_all_services(cls) -> List[str]:
        """Get a list of all available services.

        Returns:
            A list of all service names
        """
        return list(cls._services.keys())


# Convenience functions for server discovery
def get_service(name: str) -> Optional[ServiceServer]:
    """Get a service by name."""
    return ServiceServer.get_service(name)


def get_all_services() -> List[str]:
    """Get a list of all available services."""
    return ServiceServer.get_all_services()
