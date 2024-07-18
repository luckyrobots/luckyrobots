import luckyrobots as lr
import cv2
import numpy as np

binary_path="/home/devrim/Downloads/luckyrobots-linux-070824/Linux_07_08_2024"

@lr.on("robot_output")
def handle_file_created(robot_images: dict):
    if robot_images:
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
                
             
if __name__ == "__main__":
    lr.start()