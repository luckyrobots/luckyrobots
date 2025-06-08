import yaml
import time
import importlib.resources
from collections import deque


def validate_params(
    scene: str = None,
    robot: str = None,
    task: str = None,
    observation_type: str = None,
) -> bool:
    """Validate the parameters passed into Lucky World"""
    robot_config = get_robot_config(robot)

    if scene is None:
        raise ValueError("Scene is required")
    if robot is None:
        raise ValueError("Robot is required")
    if task is None:
        raise ValueError("Task is required")
    if observation_type is None:
        raise ValueError("Observation type is required")

    if scene not in robot_config["available_scenes"]:
        raise ValueError(f"Scene {scene} not available in {robot} config")
    if task not in robot_config["available_tasks"]:
        raise ValueError(f"Task {task} not available in {robot} config")
    if observation_type not in robot_config["observation_types"]:
        raise ValueError(
            f"Observation type {observation_type} not available in {robot} config"
        )


def get_robot_config(robot: str = None) -> dict:
    """Get the configuration for the robot"""
    with importlib.resources.files("luckyrobots").joinpath("config/robots.yaml").open(
        "r"
    ) as f:
        config = yaml.safe_load(f)
        if robot is not None:
            return config[robot]
        else:
            return config


class FPS:
    def __init__(self, frame_window: int = 30):
        self.frame_window = frame_window
        self.frame_times = deque(maxlen=frame_window)
        self.last_frame_time = time.perf_counter()

    def measure(self) -> float:
        current_time = time.perf_counter()
        frame_delta = current_time - self.last_frame_time
        self.last_frame_time = current_time

        # Add frame time to rolling window
        self.frame_times.append(frame_delta)

        # Calculate FPS from average frame time
        if len(self.frame_times) >= 2:  # Need at least 2 samples
            avg_frame_time = sum(self.frame_times) / len(self.frame_times)
            fps = 1.0 / avg_frame_time if avg_frame_time > 0 else 0
        else:
            fps = 0

        print(f"FPS: {fps}")
