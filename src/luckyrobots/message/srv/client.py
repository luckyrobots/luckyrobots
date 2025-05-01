"""
Client implementation for service request/response patterns.

This module provides a ServiceClient class for making requests to services with
timeout handling, error handling, and remote service support.
"""

import asyncio
from typing import Any, Dict, Generic, Optional, Type, TypeVar

from .service import (
    ServiceNotFoundError,
    ServiceServer,
)

T = TypeVar("T")  # Request type
R = TypeVar("R")  # Response type


class ServiceClient(Generic[T, R]):
    """Client class for making requests to services"""

    def __init__(self, service_type: Type[T], service_name: str):
        """Initialize a service client.

        Args:
            service_type: The type of service to connect to
            service_name: The name of the service to connect to
        """
        # ServiceClient attributes
        self.service_type = service_type
        self.service_name = service_name

        # Initialize the ServiceServer object
        self._service: Optional[ServiceServer] = None

    async def connect(self, retry_count: int = 3, retry_delay: float = 1.0) -> bool:
        """Connect to the service.

        Args:
            retry_count: Number of connection attempts
            retry_delay: Delay between attempts in seconds

        Returns:
            True if connected successfully, False otherwise
        """
        for attempt in range(retry_count):
            self._service = ServiceServer.get_service(self.service_name)
            if self._service is not None:
                return True

            if attempt < retry_count - 1:
                await asyncio.sleep(retry_delay)

        return False

    async def call(
        self, request: T, service_name: str = None, timeout: float = 30.0
    ) -> R:
        """Call the service with a request.

        Args:
            request: The request to send to the service
            service_name: The name of the service to call (defaults to client's service_name)
            timeout: Timeout in seconds

        Returns:
            The response from the server

        Raises:
            ValueError: If the service name is incorrect
            TypeError: If the request type is incorrect
            ServiceNotFoundError: If the service is not found
            ServiceTimeoutError: If the service call times out
            ServiceError: For other service-related errors
        """
        # Default to the client's service name if none provided
        if service_name is None:
            service_name = self.service_name

        if self.service_name != service_name:
            raise ValueError(
                f"Service name mismatch. Expected {self.service_name}, got {service_name}"
            )

        # Validate request type if possible
        request_type = getattr(self.service_type, "Request", self.service_type)
        if not isinstance(request, request_type):
            raise TypeError(
                f"Expected request of type {request_type.__name__}, got {type(request).__name__}"
            )

        if self._service is None:
            connected = await self.connect()
            if not connected:
                raise ServiceNotFoundError(f"Service {self.service_name} not found")

        # Check service type compatibility if possible
        if (
            hasattr(self.service_type, "Request")
            and hasattr(self._service.service_type, "Request")
            and self.service_type.Request != self._service.service_type.Request
        ):
            raise TypeError(
                f"Service request type mismatch. Expected {self.service_type.Request.__name__}, "
                f"got {self._service.service_type.Request.__name__}"
            )

        if (
            hasattr(self.service_type, "Response")
            and hasattr(self._service.service_type, "Response")
            and self.service_type.Response != self._service.service_type.Response
        ):
            raise TypeError(
                f"Service response type mismatch. Expected {self.service_type.Response.__name__}, "
                f"got {self._service.service_type.Response.__name__}"
            )

        # Call the server
        return await self._service.call(request, service_name, timeout=timeout)
