"""Example showing real-time object detection using YOLOv10n on robot camera feed"""

import cv2
import numpy as np
import luckyrobots as lr

from pathlib import Path
from ultralytics import YOLO


@lr.message_receiver
async def handle_camera_feed(message, robot_images):
    # Skip if no images received
    if not robot_images:
        print("No robot_images received")
        return
        
    # Get the front camera image path
    if not isinstance(robot_images, dict) or 'rgb_cam1' not in robot_images:
        print("Unexpected structure in robot_images")
        return
        
    image_path = robot_images['rgb_cam1'].get('file_path')
    if not image_path:
        print("No file_path found in rgb_cam1")
        return
        
    print(f"Processing image: {image_path}")
    
    # Run YOLO detection
    results = model(image_path)
    image = results[0].plot()
    
    # Convert image to proper format for display
    if isinstance(image, np.ndarray):
        img = image
    else:
        try:
            nparr = np.frombuffer(image, np.uint8)
            img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        except Exception as e:
            print(f"Error decoding image: {str(e)}")
            return
    
    if img is None:
        print("Failed to decode image")
        return
    
    # Display the image with detections
    cv2.imshow('YOLO Detections', img)
    cv2.waitKey(1)



if __name__ == "__main__":
    # Initialize YOLO model
    model_path = Path(__file__).parent / "YOLOv10n.pt"
    model = YOLO(model_path)
    
    binary_path = Path(__file__).parent.parent.parent / "LuckyWorldV2"
    lr.start(binary_path=binary_path)