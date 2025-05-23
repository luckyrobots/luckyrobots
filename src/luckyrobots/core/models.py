from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, model_validator


class CameraShape(BaseModel):
    """Shape of camera images"""

    image_width: float = Field(description="Width of the image")
    image_height: float = Field(description="Height of the image")
    channel: int = Field(description="Number of color channels")


class CameraData(BaseModel):
    """Camera data in observations"""

    camera_name: str = Field(alias="cameraName", description="Name of the camera")
    dtype: str = Field(description="Data type of the image")
    shape: CameraShape = Field(description="Shape of the image")
    file_path: str = Field(alias="filePath", description="Path to the image file")
    time_stamp: Optional[str] = Field(
        None, alias="timeStamp", description="Camera timestamp"
    )

    class Config:
        populate_by_name = True


class ObservationModel(BaseModel):
    """Observation model that matches the JSON structure"""

    observation_state: Dict[str, float] = Field(
        alias="observationState", description="State values for actuators"
    )
    observation_cameras: List[CameraData] = Field(
        alias="observationCameras", description="List of camera data"
    )

    class Config:
        populate_by_name = True


class ActionModel(BaseModel):
    """Action to control the robot"""

    joint_positions: Optional[Dict[str, float]] = Field(
        None, description="Joint positions in radians"
    )
    joint_velocities: Optional[Dict[str, float]] = Field(
        None, description="Joint velocities in radians/sec"
    )

    @model_validator(mode="after")
    def check_at_least_one_exists(self):
        if self.joint_positions is None and self.joint_velocities is None:
            raise ValueError(
                "At least one of joint_positions or joint_velocities must be provided"
            )
        return self
