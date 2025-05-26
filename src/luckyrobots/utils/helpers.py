import yaml
import time


def validate_params(scene: str = None, task: str = None, robot: str = None) -> bool:
    """Validate the parameters passed into Lucky World"""
    if scene is None:
        raise ValueError("Scene is required")
    if task is None:
        raise ValueError("Task is required")
    if robot is None:
        raise ValueError("Robot is required")

    robot_config = get_robot_config(robot)

    if scene is not None and scene not in robot_config["scenes"]:
        raise ValueError(f"Scene {scene} not available in {robot} config")
    if task is not None and task not in robot_config["tasks"]:
        raise ValueError(f"Task {task} not available in {robot} config")


def get_robot_config(robot: str = None) -> dict:
    """Get the configuration for the robot"""
    with open("src/luckyrobots/config/robots.yaml", "r") as f:
        config = yaml.safe_load(f)
        if robot is not None:
            return config[robot]        
        else:
            return config


def measure_fps(
    last_frame_time: float, frame_times: list[float], frame_window: int = 10
) -> tuple[float, list[float]]:
    """Calculate the FPS for request/response time"""
    fps = 0
    current_time = time.time()

    frame_delta = current_time - last_frame_time
    frame_times.append(frame_delta)
    last_frame_time = current_time

    if len(frame_times) % 30 == 0 or (frame_times and len(frame_times) >= frame_window):
        if len(frame_times) > 1:
            avg_frame_time = sum(frame_times) / len(frame_times)
            fps = 1.0 / avg_frame_time if avg_frame_time > 0 else 0

    return fps, frame_times
