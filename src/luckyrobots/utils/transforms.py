"""Transform system for robot coordinate frames.

This module provides a system for tracking and transforming between different coordinate
frames over time, similar to the tf system in ROS.
"""

import math
import threading
import time
from typing import Dict, List, Optional, Tuple, Union

import numpy as np


class Transform:
    """Represents a 3D transform between coordinate frames"""

    def __init__(
        self,
        translation: Optional[List[float]] = None,
        rotation: Optional[List[float]] = None,
    ):
        """Initialize a new transform.

        Args:
            translation: [x, y, z] translation vector
            rotation: [x, y, z, w] quaternion rotation
        """
        self.translation = np.array(translation or [0.0, 0.0, 0.0])
        self.rotation = np.array(
            rotation or [0.0, 0.0, 0.0, 1.0]
        )  # Default to identity quaternion
        self.timestamp = time.time()

    def as_matrix(self) -> np.ndarray:
        """Convert the transform to a 4x4 homogeneous transformation matrix.

        Returns:
            4x4 transformation matrix
        """
        # Extract quaternion components
        x, y, z, w = self.rotation

        # Compute rotation matrix from quaternion
        xx = x * x
        xy = x * y
        xz = x * z
        xw = x * w
        yy = y * y
        yz = y * z
        yw = y * w
        zz = z * z
        zw = z * w

        # Create the rotation matrix
        rot = np.array(
            [
                [1 - 2 * (yy + zz), 2 * (xy - zw), 2 * (xz + yw), 0],
                [2 * (xy + zw), 1 - 2 * (xx + zz), 2 * (yz - xw), 0],
                [2 * (xz - yw), 2 * (yz + xw), 1 - 2 * (xx + yy), 0],
                [0, 0, 0, 1],
            ]
        )

        # Add the translation
        rot[0, 3] = self.translation[0]
        rot[1, 3] = self.translation[1]
        rot[2, 3] = self.translation[2]

        return rot

    @classmethod
    def from_matrix(cls, matrix: np.ndarray) -> "Transform":
        """Create a Transform from a 4x4 homogeneous transformation matrix.

        Args:
            matrix: 4x4 transformation matrix

        Returns:
            A new Transform object
        """
        # Extract translation
        translation = [matrix[0, 3], matrix[1, 3], matrix[2, 3]]

        # Extract rotation and convert to quaternion
        rot = matrix[:3, :3]

        # Compute quaternion from rotation matrix
        trace = rot[0, 0] + rot[1, 1] + rot[2, 2]

        if trace > 0:
            s = 0.5 / math.sqrt(trace + 1.0)
            w = 0.25 / s
            x = (rot[2, 1] - rot[1, 2]) * s
            y = (rot[0, 2] - rot[2, 0]) * s
            z = (rot[1, 0] - rot[0, 1]) * s
        elif rot[0, 0] > rot[1, 1] and rot[0, 0] > rot[2, 2]:
            s = 2.0 * math.sqrt(1.0 + rot[0, 0] - rot[1, 1] - rot[2, 2])
            w = (rot[2, 1] - rot[1, 2]) / s
            x = 0.25 * s
            y = (rot[0, 1] + rot[1, 0]) / s
            z = (rot[0, 2] + rot[2, 0]) / s
        elif rot[1, 1] > rot[2, 2]:
            s = 2.0 * math.sqrt(1.0 + rot[1, 1] - rot[0, 0] - rot[2, 2])
            w = (rot[0, 2] - rot[2, 0]) / s
            x = (rot[0, 1] + rot[1, 0]) / s
            y = 0.25 * s
            z = (rot[1, 2] + rot[2, 1]) / s
        else:
            s = 2.0 * math.sqrt(1.0 + rot[2, 2] - rot[0, 0] - rot[1, 1])
            w = (rot[1, 0] - rot[0, 1]) / s
            x = (rot[0, 2] + rot[2, 0]) / s
            y = (rot[1, 2] + rot[2, 1]) / s
            z = 0.25 * s

        rotation = [x, y, z, w]

        return cls(translation=translation, rotation=rotation)

    def inverse(self) -> "Transform":
        """Return the inverse of this transform.

        Returns:
            A new Transform representing the inverse transform
        """
        # Invert the matrix and create a new transform
        matrix = self.as_matrix()
        inv_matrix = np.linalg.inv(matrix)
        return self.from_matrix(inv_matrix)

    def __mul__(self, other: "Transform") -> "Transform":
        """Compose this transform with another transform.

        Args:
            other: The other transform to compose with

        Returns:
            A new Transform representing the composition
        """
        # Combine the matrices and create a new transform
        matrix = self.as_matrix() @ other.as_matrix()
        return self.from_matrix(matrix)


class TransformBuffer:
    """Buffer of transforms between coordinate frames"""

    def __init__(self, cache_time: float = 10.0):
        """Initialize a new transform buffer.

        Args:
            cache_time: How long to keep transforms in the buffer (in seconds)
        """
        self._transforms: Dict[str, Dict[str, List[Tuple[float, Transform]]]] = {}
        self._cache_time = cache_time
        self._lock = threading.RLock()

    def set_transform(
        self, parent_frame: str, child_frame: str, transform: Transform
    ) -> None:
        """Set a transform between two frames.

        Args:
            parent_frame: The parent frame ID
            child_frame: The child frame ID
            transform: The transform from parent to child
        """
        with self._lock:
            # Initialize dictionaries if needed
            if parent_frame not in self._transforms:
                self._transforms[parent_frame] = {}

            if child_frame not in self._transforms[parent_frame]:
                self._transforms[parent_frame][child_frame] = []

            # Add the transform
            self._transforms[parent_frame][child_frame].append(
                (transform.timestamp, transform)
            )

            # Clean up old transforms
            self._cleanup()

    def lookup_transform(
        self, target_frame: str, source_frame: str, time: Optional[float] = None
    ) -> Transform:
        """Look up a transform between two frames.

        Args:
            target_frame: The target frame ID
            source_frame: The source frame ID
            time: The time to look up the transform (defaults to latest)

        Returns:
            The transform from source to target

        Raises:
            ValueError: If the transform cannot be found
        """
        with self._lock:
            # If frames are the same, return identity transform
            if target_frame == source_frame:
                return Transform()

            # Try to find direct transform
            transform = self._find_transform(target_frame, source_frame, time)
            if transform is not None:
                return transform

            # Try to find the transform through a chain of frames
            transform = self._find_transform_chain(target_frame, source_frame, time)
            if transform is not None:
                return transform

            raise ValueError(
                f"Could not find transform from {source_frame} to {target_frame}"
            )

    def _find_transform(
        self, parent_frame: str, child_frame: str, time: Optional[float] = None
    ) -> Optional[Transform]:
        """Find a direct transform between two frames.

        Args:
            parent_frame: The parent frame ID
            child_frame: The child frame ID
            time: The time to look up the transform

        Returns:
            The transform from child to parent, or None if not found
        """
        # Check if we have a direct transform from parent to child
        if (
            parent_frame in self._transforms
            and child_frame in self._transforms[parent_frame]
        ):
            transforms = self._transforms[parent_frame][child_frame]

            # If no time specified, return the latest transform
            if time is None:
                return transforms[-1][1]

            # Find the transform closest to the requested time
            closest_transform = None
            closest_time_diff = float("inf")

            for timestamp, transform in transforms:
                time_diff = abs(timestamp - time)
                if time_diff < closest_time_diff:
                    closest_time_diff = time_diff
                    closest_transform = transform

            return closest_transform

        # Check if we have a direct transform from child to parent (inverted)
        if (
            child_frame in self._transforms
            and parent_frame in self._transforms[child_frame]
        ):
            transform = self._find_transform(child_frame, parent_frame, time)
            if transform is not None:
                return transform.inverse()

        return None

    def _find_transform_chain(
        self, target_frame: str, source_frame: str, time: Optional[float] = None
    ) -> Optional[Transform]:
        """Find a transform chain between two frames.

        Args:
            target_frame: The target frame ID
            source_frame: The source frame ID
            time: The time to look up the transform

        Returns:
            The transform from source to target, or None if not found
        """
        # This is a simple breadth-first search
        visited = set()
        queue = [(source_frame, Transform())]

        while queue:
            frame, transform_so_far = queue.pop(0)

            if frame in visited:
                continue

            visited.add(frame)

            # Check all frames that this frame has a transform to
            if frame in self._transforms:
                for next_frame, _ in self._transforms[frame].items():
                    if next_frame == target_frame:
                        # Found the target frame, return the complete transform
                        next_transform = self._find_transform(frame, next_frame, time)
                        return transform_so_far * next_transform

                    if next_frame not in visited:
                        next_transform = self._find_transform(frame, next_frame, time)
                        queue.append((next_frame, transform_so_far * next_transform))

            # Check all frames that have a transform to this frame
            for parent_frame in self._transforms:
                if frame in self._transforms[parent_frame]:
                    if parent_frame == target_frame:
                        # Found the target frame, return the complete transform
                        parent_transform = self._find_transform(
                            parent_frame, frame, time
                        )
                        return transform_so_far * parent_transform.inverse()

                    if parent_frame not in visited:
                        parent_transform = self._find_transform(
                            parent_frame, frame, time
                        )
                        queue.append(
                            (
                                parent_frame,
                                transform_so_far * parent_transform.inverse(),
                            )
                        )

        return None

    def _cleanup(self) -> None:
        """Clean up old transforms."""
        current_time = time.time()
        min_time = current_time - self._cache_time

        for parent_frame in list(self._transforms.keys()):
            for child_frame in list(self._transforms[parent_frame].keys()):
                # Filter out old transforms
                transforms = self._transforms[parent_frame][child_frame]
                self._transforms[parent_frame][child_frame] = [
                    (timestamp, transform)
                    for timestamp, transform in transforms
                    if timestamp >= min_time
                ]

                # Remove empty lists
                if not self._transforms[parent_frame][child_frame]:
                    del self._transforms[parent_frame][child_frame]

            # Remove empty dictionaries
            if not self._transforms[parent_frame]:
                del self._transforms[parent_frame]


# Create a global transform buffer
transform_buffer = TransformBuffer()


# Convenience functions
def set_transform(parent_frame: str, child_frame: str, transform: Transform) -> None:
    """Set a transform between two frames."""
    transform_buffer.set_transform(parent_frame, child_frame, transform)


def lookup_transform(
    target_frame: str, source_frame: str, time: Optional[float] = None
) -> Transform:
    """Look up a transform between two frames."""
    return transform_buffer.lookup_transform(target_frame, source_frame, time)


def can_transform(target_frame: str, source_frame: str) -> bool:
    """Check if a transform is possible between two frames."""
    try:
        lookup_transform(target_frame, source_frame)
        return True
    except ValueError:
        return False


def transform_point(
    target_frame: str, source_frame: str, point: List[float]
) -> List[float]:
    """Transform a point from one frame to another.

    Args:
        target_frame: The target frame ID
        source_frame: The source frame ID
        point: The point to transform [x, y, z]

    Returns:
        The transformed point [x, y, z]
    """
    # Get the transform
    transform = lookup_transform(target_frame, source_frame)

    # Convert point to homogeneous coordinates
    point_h = np.array([point[0], point[1], point[2], 1.0])

    # Apply the transform
    result = transform.as_matrix() @ point_h

    # Convert back to 3D coordinates
    return [result[0], result[1], result[2]]


# Example usage
if __name__ == "__main__":
    # Create some transforms
    world_to_robot = Transform([0.0, 0.0, 0.0], [0.0, 0.0, 0.0, 1.0])
    robot_to_camera = Transform([0.1, 0.0, 0.2], [0.0, 0.0, 0.0, 1.0])

    # Set the transforms in the buffer
    set_transform("world", "robot", world_to_robot)
    set_transform("robot", "camera", robot_to_camera)

    # Look up a transform
    camera_to_world = lookup_transform("world", "camera")

    # Transform a point
    point_in_camera = [0.5, 0.0, 1.0]
    point_in_world = transform_point("world", "camera", point_in_camera)

    print(f"Point in camera frame: {point_in_camera}")
    print(f"Point in world frame: {point_in_world}")
