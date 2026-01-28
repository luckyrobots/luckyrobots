"""
Utility functions and classes for LuckyRobots.
"""

import time
import yaml
import importlib.resources
from collections import deque


class FPS:
    """Utility for measuring frames per second with a rolling window.

    Usage:
        fps = FPS(frame_window=30)
        while running:
            # ... do work ...
            current_fps = fps.measure()
    """

    def __init__(self, frame_window: int = 30):
        """Initialize FPS counter.

        Args:
            frame_window: Number of frames to average over.
        """
        self.frame_window = frame_window
        self.frame_times: deque[float] = deque(maxlen=frame_window)
        self.last_frame_time = time.perf_counter()

    def measure(self) -> float:
        """Record a frame and return current FPS.

        Returns:
            Current frames per second (averaged over window).
        """
        current_time = time.perf_counter()
        frame_delta = current_time - self.last_frame_time
        self.last_frame_time = current_time

        self.frame_times.append(frame_delta)

        if len(self.frame_times) >= 2:
            avg_frame_time = sum(self.frame_times) / len(self.frame_times)
            return 1.0 / avg_frame_time if avg_frame_time > 0 else 0.0
        return 0.0


def get_robot_config(robot: str = None) -> dict:
    """Get the configuration for a robot from robots.yaml.

    Args:
        robot: Robot name. If None, returns entire config.

    Returns:
        Robot configuration dict, or full config if robot is None.
    """
    with importlib.resources.files("luckyrobots").joinpath("config/robots.yaml").open(
        "r"
    ) as f:
        config = yaml.safe_load(f)
        if robot is not None:
            return config[robot]
        else:
            return config


def validate_params(
    scene: str = None,
    robot: str = None,
    task: str = None,
    observation_type: str = None,
) -> None:
    """Validate parameters for launching LuckyEngine.

    Args:
        scene: Scene name.
        robot: Robot name.
        task: Task name.
        observation_type: Observation type.

    Raises:
        ValueError: If any parameter is invalid.
    """
    if scene is None:
        raise ValueError("Scene is required")
    if robot is None:
        raise ValueError("Robot is required")
    if task is None:
        raise ValueError("Task is required")
    if observation_type is None:
        raise ValueError("Observation type is required")

    robot_config = get_robot_config(robot)

    if scene not in robot_config["available_scenes"]:
        raise ValueError(f"Scene {scene} not available in {robot} config")
    if task not in robot_config["available_tasks"]:
        raise ValueError(f"Task {task} not available in {robot} config")
    if observation_type not in robot_config["observation_types"]:
        raise ValueError(
            f"Observation type {observation_type} not available in {robot} config"
        )
