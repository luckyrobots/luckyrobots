import luckyrobots as lr
from luckyrobots.events import on_message
import cv2
import numpy as np

binary_path = "./LuckEWorld.app"

@on_message("robot_output")
def handle_file_created(robot_images: list):
    if robot_images:
        print(f"Processing image: {robot_images[3]['file_path']}")
        if isinstance(robot_images, dict) and 'rgb_cam1' in robot_images:
            image_path = robot_images['rgb_cam1'].get('file_path')
            if image_path:
                print(f"Processing image: {image_path}")
                
                # Read the image using OpenCV
                img = cv2.imread(image_path)
                
                if img is None:
                    print(f"Failed to read image from {image_path}")
                    return
                
                # Display the image
                cv2.imshow('Robot Image', img)
                cv2.waitKey(1)  # Wait for 1ms to allow the image to be displayed
                
            else:
                print("No file_path found in rgb_cam1")
        else:
            print("Unexpected structure in robot_images")
    else:
        print("No robot_images received")                

lr.start(binary_path)