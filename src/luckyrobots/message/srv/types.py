"""Data models for messaging system.

This module defines the data models used for request and response messaging.
"""

from dataclasses import dataclass
from typing import Any, Dict, Optional, TypeVar

from ...core.models import PoseModel, TwistModel, ObservationModel

T = TypeVar("T")


@dataclass
class ServiceRequest:
    """Base class for service requests"""

    pass


@dataclass
class ServiceResponse:
    """Base class for service responses"""

    success: bool
    message: str


@dataclass
class Reset:
    """Reset the robot"""

    @dataclass
    class Request(ServiceRequest):
        """Request to reset the robot"""

        seed: Optional[int] = None

    @dataclass
    class Response(ServiceResponse):
        """Response from reset service"""

        observation: Optional[ObservationModel] = None
        info: Optional[Dict[str, Any]] = None


@dataclass
class Step:
    """Step the robot with an action"""

    @dataclass
    class Request(ServiceRequest):
        """Request to step the robot with an action"""

        pose: Optional[PoseModel] = None
        twist: Optional[TwistModel] = None

    @dataclass
    class Response(ServiceResponse):
        """Response from step service"""

        observation: Optional[ObservationModel] = None
        info: Optional[Dict[str, Any]] = None
