"""
Camera models for LuckyRobots.

These models handle camera frame data from LuckyEngine.
"""

from typing import Any, Dict, Optional, Union
from pydantic import BaseModel, Field, ConfigDict
import numpy as np
import cv2


class CameraShape(BaseModel):
    """Shape of camera images."""

    width: float = Field(description="Width of the image")
    height: float = Field(description="Height of the image")
    channel: int = Field(description="Number of color channels")


class CameraData(BaseModel):
    """Camera frame data."""

    model_config = ConfigDict(populate_by_name=True, arbitrary_types_allowed=True)

    camera_name: str = Field(alias="CameraName", description="Name of the camera")
    dtype: str = Field(default="uint8", description="Data type of the image")
    shape: Optional[Union[CameraShape, Dict[str, Union[float, int]]]] = Field(
        default=None, description="Shape of the image"
    )
    time_stamp: Optional[str] = Field(
        None, alias="TimeStamp", description="Camera timestamp"
    )
    image_data: Optional[Any] = Field(
        None, alias="ImageData", description="Image data (bytes or numpy array)"
    )
    width: Optional[int] = Field(default=None, description="Image width")
    height: Optional[int] = Field(default=None, description="Image height")
    channels: Optional[int] = Field(default=None, description="Number of channels")
    format: Optional[str] = Field(
        default=None, description="Image format (raw, jpeg, png)"
    )
    frame_number: Optional[int] = Field(default=None, description="Frame number")

    def process_image(self) -> None:
        """Process the image data into a numpy array."""
        if self.image_data is None:
            return None

        # If already a numpy array, skip processing
        if isinstance(self.image_data, np.ndarray):
            return

        # Handle bytes data
        if isinstance(self.image_data, bytes):
            nparr = np.frombuffer(self.image_data, np.uint8)

            # Check if it's raw RGBA/RGB data or encoded
            if self.format == "raw" and self.width and self.height:
                channels = self.channels or 4
                try:
                    self.image_data = nparr.reshape((self.height, self.width, channels))
                    # Convert RGBA to BGR for OpenCV compatibility
                    if channels == 4:
                        self.image_data = cv2.cvtColor(
                            self.image_data, cv2.COLOR_RGBA2BGR
                        )
                    elif channels == 3:
                        self.image_data = cv2.cvtColor(
                            self.image_data, cv2.COLOR_RGB2BGR
                        )
                except ValueError:
                    # Fallback to decode
                    self.image_data = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            else:
                # Encoded image (JPEG, PNG)
                self.image_data = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

    @classmethod
    def from_grpc_frame(cls, frame: Any, camera_name: str = "camera") -> "CameraData":
        """Create CameraData from a gRPC ImageFrame message."""
        return cls(
            camera_name=camera_name,
            dtype="uint8",
            width=frame.width,
            height=frame.height,
            channels=frame.channels,
            format=frame.format,
            time_stamp=str(frame.timestamp_ms),
            frame_number=frame.frame_number,
            image_data=frame.data,
            shape=CameraShape(
                width=frame.width,
                height=frame.height,
                channel=frame.channels,
            ),
        )
