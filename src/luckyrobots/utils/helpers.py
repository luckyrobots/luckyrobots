import yaml
import time
import base64
import numpy as np
import cv2
import importlib.resources
from collections import deque
import os
import pkg_resources


def get_robot_config(robot: str = None) -> dict:
    """Get the configuration for the robot"""
    
    # Method 1: Try using importlib.resources (Python 3.9+)
    try:
        try:
            with importlib.resources.files('luckyrobots.config').joinpath('robots.yaml').open('r') as f:
                config = yaml.safe_load(f)
        except AttributeError:
            # Fallback for older Python versions
            with importlib.resources.open_text('luckyrobots.config', 'robots.yaml') as f:
                config = yaml.safe_load(f)
                
        if robot is not None:
            if robot not in config:
                raise ValueError(f"Robot '{robot}' not found in configuration. Available robots: {list(config.keys())}")
            return config[robot]
        else:
            return config
            
    except (FileNotFoundError, ModuleNotFoundError, ImportError) as e:
        print(f"Method 1 failed: {e}")
        pass

    # Method 2: Try pkg_resources
    try:
        yaml_content = pkg_resources.resource_string('luckyrobots', 'config/robots.yaml').decode('utf-8')
        config = yaml.safe_load(yaml_content)
        
        if robot is not None:
            if robot not in config:
                raise ValueError(f"Robot '{robot}' not found in configuration. Available robots: {list(config.keys())}")
            return config[robot]
        else:
            return config
            
    except Exception as e:
        print(f"Method 2 failed: {e}")
        pass

    # Method 3: Try installed package location
    try:
        import luckyrobots
        package_dir = os.path.dirname(luckyrobots.__file__)
        yaml_path = os.path.join(package_dir, 'config', 'robots.yaml')
        
        if os.path.exists(yaml_path):
            with open(yaml_path, 'r') as f:
                config = yaml.safe_load(f)
                
            if robot is not None:
                if robot not in config:
                    raise ValueError(f"Robot '{robot}' not found in configuration. Available robots: {list(config.keys())}")
                return config[robot]
            else:
                return config
        else:
            print(f"Method 3: Config file not found at {yaml_path}")
            
    except Exception as e:
        print(f"Method 3 failed: {e}")
        pass

    # Method 4: Try relative to this file (development mode)
    try:
        current_dir = os.path.dirname(__file__)
        yaml_path = os.path.join(current_dir, '..', 'config', 'robots.yaml')
        yaml_path = os.path.normpath(yaml_path)
        
        if os.path.exists(yaml_path):
            with open(yaml_path, 'r') as f:
                config = yaml.safe_load(f)
                
            if robot is not None:
                if robot not in config:
                    raise ValueError(f"Robot '{robot}' not found in configuration. Available robots: {list(config.keys())}")
                return config[robot]
            else:
                return config
        else:
            print(f"Method 4: Config file not found at {yaml_path}")
            
    except Exception as e:
        print(f"Method 4 failed: {e}")
        pass

    # Method 5: Search in common locations
    search_paths = [
        os.path.join(os.path.expanduser('~'), '.luckyrobots', 'config', 'robots.yaml'),
        '/usr/local/share/luckyrobots/config/robots.yaml',
        '/opt/luckyrobots/config/robots.yaml',
    ]
    
    for yaml_path in search_paths:
        try:
            if os.path.exists(yaml_path):
                with open(yaml_path, 'r') as f:
                    config = yaml.safe_load(f)
                    
                if robot is not None:
                    if robot not in config:
                        raise ValueError(f"Robot '{robot}' not found in configuration. Available robots: {list(config.keys())}")
                    return config[robot]
                else:
                    return config
        except Exception as e:
            print(f"Search path {yaml_path} failed: {e}")
            continue

    # If all methods fail, raise a comprehensive error
    raise FileNotFoundError(
        f"Could not locate robots.yaml configuration file. "
        f"Tried importlib.resources, pkg_resources, installed package location, "
        f"relative path, and common system locations. "
        f"Please ensure the luckyrobots package is properly installed or the config file exists."
    )


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