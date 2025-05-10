from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, model_validator


class CameraShape(BaseModel):
    image_width: int = Field(..., description="Width of the image")
    image_height: int = Field(..., description="Height of the image")
    channel: int = Field(..., description="Number of color channels")


class CameraData(BaseModel):
    camera_name: str = Field(..., alias="cameraName", description="Name of the camera")
    dtype: str = Field(..., description="Data type of the image")
    shape: CameraShape = Field(..., description="Shape of the image")
    file_path: str = Field(..., alias="filePath", description="Path to the image file")


class ObservationModel(BaseModel):
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
    observation: ObservationModel = Field(..., description="Observation of the robot")
    info: Dict[str, Any] = Field(..., description="Information about the reset")


class StepModel(BaseModel):
    observation: ObservationModel = Field(..., description="Observation of the robot")
    info: Dict[str, Any] = Field(..., description="Information about the step")


class PoseModel(BaseModel):
    position: Dict[str, float] = Field(..., description="Position")
    orientation: Dict[str, float] = Field(..., description="Orientation")


class TwistModel(BaseModel):
    linear: Dict[str, float] = Field(..., description="Linear velocity")
    angular: Dict[str, float] = Field(..., description="Angular velocity")


class ActionModel(BaseModel):
    pose: Optional[PoseModel] = Field(None, description="Pose of the robot")
    twist: Optional[TwistModel] = Field(None, description="Twist of the robot")

    @model_validator(mode="after")
    def check_at_least_one_exists(self):
        if self.pose is None and self.twist is None:
            raise ValueError("At least one of pose or twist must be provided")
        return self
