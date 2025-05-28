"""Data models for messaging system.

This module defines the data models used for request and response messaging.
"""

from typing import Any, Dict, Optional
from ...core.models import ObservationModel

from pydantic import BaseModel, Field


class ServiceRequest(BaseModel):
    """Base class for service requests"""

    pass


class ServiceResponse(BaseModel):
    """Base class for service responses"""

    success: bool = Field(
        default=True, description="Whether the service call was successful"
    )
    message: str = Field(
        default="", description="A message describing the service call"
    )

    request_type: str = Field(
        description="Type of response (reset_response or step_response)"
    )
    request_id: str = Field(description="Unique identifier")
    time_stamp: str = Field(alias="timeStamp", description="Timestamp value")

    observation: ObservationModel = Field(description="Observation data")
    info: Dict[str, str] = Field(description="Additional information")

    class Config:
        populate_by_name = True


class ResetRequest(ServiceRequest):
    """Request to reset the robot"""

    seed: Optional[int] = Field(
        default=None, description="The seed to reset the robot with"
    )
    options: Optional[Dict[str, Any]] = Field(
        default=None, description="Options for the reset"
    )


class ResetResponse(ServiceResponse):
    """Response to reset request"""

    pass


class Reset:
    """Reset the robot"""

    Request = ResetRequest
    Response = ResetResponse


class StepRequest(ServiceRequest):
    """Request to step the robot with an action"""

    actuator_values: list = Field(
        description="The array of actuator values to control the robot with"
    )


class StepResponse(ServiceResponse):
    """Response to step request"""

    pass


class Step:
    """Step the robot with an action"""

    Request = StepRequest
    Response = StepResponse
