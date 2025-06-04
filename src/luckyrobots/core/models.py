"""
PyDantic models for the LuckyRobots framework.

This module contains the PyDantic models that are used to define
the data structures being sent over the WebSocket transport.
"""

from typing import Dict, List, Optional, Union
from pydantic import BaseModel, Field
import numpy as np
import cv2


class CameraShape(BaseModel):
    """Shape of camera images"""

    width: float = Field(description="Width of the image")
    height: float = Field(description="Height of the image")
    channel: int = Field(description="Number of color channels")


class CameraData(BaseModel):
    """Camera data in observations"""

    camera_name: str = Field(alias="CameraName", description="Name of the camera")
    dtype: str = Field(description="Data type of the image")
    shape: Union[CameraShape, Dict[str, Union[float, int]]] = Field(
        description="Shape of the image"
    )
    time_stamp: Optional[str] = Field(
        None, alias="TimeStamp", description="Camera timestamp"
    )
    image_data: Optional[bytes] = Field(
        None, alias="ImageData", description="Image data"
    )

    def process_image(self) -> None:
        """Process the base64 image data into a numpy array"""
        if self.image_data is None:
            return None

        nparr = np.frombuffer(self.image_data, np.uint8)
        self.image_data = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

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

    def process_all_cameras(self) -> None:
        """Process all camera images in the observation"""
        if self.observation_cameras is None:
            return

        for camera in self.observation_cameras:
            camera.process_image()

    class Config:
        populate_by_name = True
