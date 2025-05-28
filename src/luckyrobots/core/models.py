from typing import Dict, List, Optional, Union
from pydantic import BaseModel, Field


class CameraShape(BaseModel):
    """Shape of camera images"""

    image_width: float = Field(description="Width of the image")
    image_height: float = Field(description="Height of the image")
    channel: int = Field(description="Number of color channels")


class CameraData(BaseModel):
    """Camera data in observations"""

    camera_name: str = Field(alias="cameraName", description="Name of the camera")
    dtype: str = Field(description="Data type of the image")
    shape: Union[CameraShape, Dict[str, Union[float, int]]] = Field(
        description="Shape of the image"
    )
    time_stamp: Optional[str] = Field(
        None, alias="timeStamp", description="Camera timestamp"
    )
    image_data: Optional[str] = Field(
        None, alias="imageData", description="Base64 encoded image data"
    )

    class Config:
        populate_by_name = True


class ObservationModel(BaseModel):
    """Observation model that matches the JSON structure"""

    observation_state: Dict[str, float] = Field(
        alias="ObservationState", description="State values for actuators"
    )
    observation_cameras: Optional[List[CameraData]] = Field(
        default=None, alias="ObservationCameras", description="List of camera data"
    )

    class Config:
        populate_by_name = True
