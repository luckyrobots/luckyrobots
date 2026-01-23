"""
PyDantic models for the LuckyRobots framework.

This module contains the PyDantic models that are used to define
the data structures for communication with LuckyEngine.
"""

from typing import Any, Dict, List, Optional, Union
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
    # gRPC-specific fields
    width: Optional[int] = Field(default=None, description="Image width from gRPC")
    height: Optional[int] = Field(default=None, description="Image height from gRPC")
    channels: Optional[int] = Field(
        default=None, description="Number of channels from gRPC"
    )
    format: Optional[str] = Field(
        default=None, description="Image format (raw, jpeg, png)"
    )
    frame_number: Optional[int] = Field(
        default=None, description="Frame number from gRPC stream"
    )

    def process_image(self) -> None:
        """Process the image data into a numpy array"""
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

    class Config:
        populate_by_name = True
        arbitrary_types_allowed = True


class ObservationModel(BaseModel):
    """Observation model for robot state and sensor data"""

    observation_state: Dict[str, float] = Field(
        default_factory=dict,
        alias="ObservationState",
        description="State values for joints/actuators",
    )
    observation_cameras: Optional[List[CameraData]] = Field(
        default=None, alias="ObservationCameras", description="List of camera data"
    )

    # gRPC-specific observation fields
    observation_vector: Optional[List[float]] = Field(
        default=None, description="Flat observation vector from gRPC AgentFrame"
    )
    action_vector: Optional[List[float]] = Field(
        default=None, description="Last action vector echoed from gRPC"
    )
    timestamp_ms: Optional[int] = Field(
        default=None, description="Timestamp in milliseconds from gRPC"
    )
    frame_number: Optional[int] = Field(
        default=None, description="Frame number from gRPC stream"
    )

    def process_all_cameras(self) -> None:
        """Process all camera images in the observation"""
        if self.observation_cameras is None:
            return

        for camera in self.observation_cameras:
            camera.process_image()

    @classmethod
    def from_grpc_agent_frame(
        cls,
        frame: Any,
        joint_names: Optional[List[str]] = None,
    ) -> "ObservationModel":
        """
        Create ObservationModel from a gRPC AgentFrame message.

        Args:
            frame: gRPC AgentFrame message.
            joint_names: Optional list of joint names to map observations.
        """
        observations = list(frame.observations) if frame.observations else []
        actions = list(frame.actions) if frame.actions else []

        # Build observation state dict
        observation_state = {}
        if joint_names:
            for i, name in enumerate(joint_names):
                if i < len(observations):
                    observation_state[name] = observations[i]
        else:
            # Use indices as keys if no names provided
            for i, val in enumerate(observations):
                observation_state[f"obs_{i}"] = val

        return cls(
            observation_state=observation_state,
            observation_vector=observations,
            action_vector=actions,
            timestamp_ms=frame.timestamp_ms,
            frame_number=frame.frame_number,
        )

    @classmethod
    def from_grpc_joint_state(
        cls,
        joint_state: Any,
        joint_names: Optional[List[str]] = None,
    ) -> "ObservationModel":
        """
        Create ObservationModel from a gRPC JointState message.

        Args:
            joint_state: gRPC JointState message.
            joint_names: Optional list of joint names.
        """
        positions = list(joint_state.positions) if joint_state.positions else []
        velocities = list(joint_state.velocities) if joint_state.velocities else []

        observation_state = {}
        if joint_names:
            for i, name in enumerate(joint_names):
                if i < len(positions):
                    observation_state[name] = positions[i]
                if i < len(velocities):
                    observation_state[f"{name}_vel"] = velocities[i]
        else:
            for i, pos in enumerate(positions):
                observation_state[f"qpos_{i}"] = pos
            for i, vel in enumerate(velocities):
                observation_state[f"qvel_{i}"] = vel

        return cls(
            observation_state=observation_state,
            observation_vector=positions + velocities,
        )

    class Config:
        populate_by_name = True
