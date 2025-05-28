import yaml
import time
import base64
import numpy as np
import cv2
import pkg_resources
from collections import deque


def validate_params(scene: str = None, task: str = None, robot: str = None) -> bool:
    """Validate the parameters passed into Lucky World"""
    if scene is None:
        raise ValueError("Scene is required")
    if task is None:
        raise ValueError("Task is required")
    if robot is None:
        raise ValueError("Robot is required")

    robot_config = get_robot_config(robot)

    if scene is not None and scene not in robot_config["available_scenes"]:
        raise ValueError(f"Scene {scene} not available in {robot} config")
    if task is not None and task not in robot_config["available_tasks"]:
        raise ValueError(f"Task {task} not available in {robot} config")
    

def get_robot_config(robot: str = None) -> dict:
    """Get the configuration for the robot"""
    config_path = pkg_resources.resource_filename('luckyrobots', 'config/robots.yaml')
    with open(config_path, "r") as f:
        config = yaml.safe_load(f)
        if robot is not None:
            return config[robot]
        else:
            return config


def process_images(observation_cameras: list) -> dict:
    """Process the images from the observation cameras"""
    processed_cameras = {}
    for camera in observation_cameras:
        image_data = camera.image_data
        camera_name = camera.camera_name

        image_bytes = base64.b64decode(image_data)
        nparr = np.frombuffer(image_bytes, np.uint8)
        image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

        processed_cameras[camera_name] = image

        cv2.imshow(camera_name, image)
        cv2.waitKey(1)

    return processed_cameras


class FPS:
    def __init__(self, frame_window: int = 30):
        self.frame_window = frame_window
        self.frame_times = deque(maxlen=frame_window)  # Automatically maintains size
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