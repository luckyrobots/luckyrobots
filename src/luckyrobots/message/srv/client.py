import asyncio
from typing import Generic, Optional, Type, TypeVar

from .service import (
    ServiceNotFoundError,
    ServiceServer,
)

T = TypeVar("T")  # Request type
R = TypeVar("R")  # Response type


class ServiceClient(Generic[T, R]):
    def __init__(self, service_type: Type[T], service_name: str):
        # ServiceClient attributes
        self.service_type = service_type
        self.service_name = service_name

        # Initialize the ServiceServer object
        self._service: Optional[ServiceServer] = None

    async def connect(self, retry_count: int = 3, retry_delay: float = 1.0) -> bool:
        """Connect to the service server"""
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
        """Call the service server"""
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

        # Call the service server
        return await self._service.call(request, service_name, timeout=timeout)
