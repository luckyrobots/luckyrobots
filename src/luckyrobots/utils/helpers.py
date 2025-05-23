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


def extract_observation_from_message(message_json: dict, state_only: bool = True):
    """
    Extract the observation array (or full observation) from a websocket message_json.
    Args:
        message_json (dict): The message received from websocket (e.g., via await websocket.receive_json()).
        state_only (bool): If True, return only the observationState dict/array. If False, return the full observation dict.
    Returns:
        dict or None: The observationState dict (default) or full observation dict, or None if not found.
    """
    observation = message_json.get("observation", {})
    if not observation:
        return None
    if state_only:
        return observation.get("observationState")
    return observation

# Example usage:
# message_json = await websocket.receive_json()
# obs_array = extract_observation_from_message(message_json)
# Log: Added extract_observation_from_message to help users extract observation arrays from websocket messages. Function is flexible for full or partial extraction.

