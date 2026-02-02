"""Utility functions for LuckyRobots."""

import yaml
import importlib.resources


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
