import asyncio
import logging
from typing import Callable, Dict, Generic, List, Optional, Type, TypeVar

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
        self._handler: Optional[Callable[[T], R]] = None

        self.service_type = service_type
        self.service_name = service_name

        self.set_handler(handler)

        # Register this service in the class dictionary
        ServiceServer._services[service_name] = self

        logger.debug(f"Created service: {service_name}")

    def set_handler(self, handler: Callable[[T], R]) -> None:
        """Set the handler for the service"""
        self._handler = handler
        logger.debug(f"Set handler for service: {self.service_name}")

    async def call(self, request: T, service_name: str, timeout: float = 30.0) -> R:
        """Call the service"""
        if self.service_name != service_name:
            raise ValueError(
                f"Service name mismatch. Expected {self.service_name}, got {service_name}"
            )

        # Validate the request type if possible
        request_type = getattr(self.service_type, "Request")
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
        """Run the server handler and handle exceptions"""
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
        """Get a service by name"""
        return cls._services.get(service_name)

    @classmethod
    def get_all_services(cls) -> List[str]:
        """Get all services"""
        return list(cls._services.keys())


def get_service(name: str) -> Optional[ServiceServer]:
    """External helper function to get a service by name"""
    return ServiceServer.get_service(name)


def get_all_services() -> List[str]:
    """External helper function to get all services"""
    return ServiceServer.get_all_services()
