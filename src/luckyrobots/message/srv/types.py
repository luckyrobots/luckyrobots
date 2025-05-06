"""Data models for messaging system.

This module defines the data models used for request and response messaging.
"""

from typing import Any, Dict, Optional

from ...core.models import ActionModel, ObservationModel


from pydantic import BaseModel, Field


class ServiceRequest(BaseModel):
    """Base class for service requests"""

    pass


class ServiceResponse(BaseModel):
    """Base class for service responses"""

    success: bool = Field(description="Whether the service call was successful")
    message: str = Field(description="A message describing the service call")


class ResetRequest(ServiceRequest):
    """Request to reset the robot"""

    seed: Optional[int] = Field(
        default=None, description="The seed to reset the robot with"
    )


class ResetResponse(ServiceResponse):
    """Response from reset service"""

    observation: ObservationModel = Field(description="The observation from the reset")
    info: Dict[str, Any] = Field(description="Additional information about the reset")


class Reset:
    """Reset the robot"""

    Request = ResetRequest
    Response = ResetResponse


class StepRequest(ServiceRequest):
    """Request to step the robot with an action"""

    action: ActionModel = Field(description="The action to step the robot with")


class StepResponse(ServiceResponse):
    """Response from step service"""

    observation: ObservationModel = Field(description="The observation from the step")
    info: Dict[str, Any] = Field(description="Additional information about the step")


class Step:
    """Step the robot with an action"""

    Request = StepRequest
    Response = StepResponse
