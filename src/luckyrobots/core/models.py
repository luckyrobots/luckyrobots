"""
Defines the data models that can be used to handle messages over the network.
"""

from typing import Any, Dict, List

from pydantic import BaseModel, Field


class CameraShape(BaseModel):
    """Model for camera shape data"""

    image_width: int = Field(..., description="Width of the image")
    image_height: int = Field(..., description="Height of the image")
    channel: int = Field(..., description="Number of color channels")


class CameraData(BaseModel):
    """Model for camera data"""

    camera_name: str = Field(..., alias="cameraName", description="Name of the camera")
    dtype: str = Field(..., description="Data type of the image")
    shape: CameraShape = Field(..., description="Shape of the image")
    file_path: str = Field(..., alias="filePath", description="Path to the image file")


class ObservationModel(BaseModel):
    """Model for the complete observation containing robot state.

    This model represents the current state of all robot data, including:
    - Timestamp
    - ID
    - Observation state (actuator values)
    - Camera data

    Attributes:
        time_stamp: Timestamp value
        id: Unique identifier
        observation_state: State values for actuators
        observation_cameras: List of camera data
    """

    time_stamp: int = Field(..., alias="timeStamp", description="Timestamp value")
    id: str = Field(..., description="Unique identifier")
    observation_state: Dict[str, int] = Field(
        ..., alias="observationState", description="State values for actuators"
    )
    observation_cameras: List[CameraData] = Field(
        ..., alias="observationCameras", description="List of camera data"
    )

    class Config:
        populate_by_name = True


class ResetModel(BaseModel):
    """Model for the reset message"""

    observation: ObservationModel = Field(..., description="Observation of the robot")
    info: Dict[str, Any] = Field(..., description="Information about the reset")


class StepModel(BaseModel):
    """Model for the step message"""

    observation: ObservationModel = Field(..., description="Observation of the robot")
    info: Dict[str, Any] = Field(..., description="Information about the step")


class TwistModel(BaseModel):
    """Model for the twist message to be sent from the node to the core"""

    twist: Dict[str, Any] = Field(..., description="Twist to be sent to the robot")
