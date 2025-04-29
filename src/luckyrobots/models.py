"""Pydantic models for LuckyRobots data structures.

This module defines the data models that can be used to handle messages from the robotdata directory.
"""

from typing import Dict, Optional, List
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


class Observation(BaseModel):
    """Model for the complete observation containing robot state and camera data.
    
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
    observation_state: Dict[str, int] = Field(..., alias="observationState", description="State values for actuators")
    observation_cameras: List[CameraData] = Field(..., alias="observationCameras", description="List of camera data")

    class Config:
        populate_by_name = True


class MessageReceiver:
    """Base class for message receiver functions.
    
    This class defines the interface that all message receivers must implement.
    It ensures consistent handling of messages across different receiver types.
    
    Example:
        ```python
        class MyReceiver(MessageReceiver):
            async def __call__(self, msg_type: str, data: Optional[Observation] = None) -> None:
                # Process the message here
                pass
        ```
    """
    async def __call__(self, msg_type: str, data: Optional[Observation] = None) -> None:
        """Process a message with optional data.
        
        Args:
            msg_type: The message type
            data: Optional additional data, typically the observation
            
        Raises:
            NotImplementedError: If the method is not implemented by a subclass
        """
        raise NotImplementedError("Message receivers must implement this method") 