import yaml


def validate_params(scene: str = None, robot: str = None, task: str = None) -> bool:
    """Validate the parameters passed into Lucky World"""
    if robot is None:
        raise ValueError("Robot is required")
    if scene is None:
        raise ValueError("Scene is required")
    if task is None:
        raise ValueError("Task is required")

    robot_config = get_robot_config(robot)

    if scene is not None and scene not in robot_config["scenes"]:
        raise ValueError(f"Scene {scene} not available in {robot} config")
    if task is not None and task not in robot_config["tasks"]:
        raise ValueError(f"Task {task} not available in {robot} config")


def get_robot_config(robot: str = None) -> dict:
    """Get the configuration for the robot"""
    with open("src/luckyrobots/config/robots.yaml", "r") as f:
        config = yaml.safe_load(f)
        if robot is None:
            return config
        else:
            return config[robot]
