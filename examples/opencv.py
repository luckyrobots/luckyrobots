import luckyrobots as lr
from luckyrobots.events import on_message
import cv2
import numpy as np

@on_message("robot_images_created")
def handle_file_created(robot_images: list):
    if robot_images:
        print(f"Processing image: {robot_images[3]['file_path']}")
        image = robot_images[3]["file_bytes"]

        try:
            # Convert bytes to numpy array
            nparr = np.frombuffer(image, np.uint8)
            # Decode the image
            img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            
            if img is None:
                print("Failed to decode image")
                return
            
            # Display the image
            cv2.imshow('Robot Image', img)
            cv2.waitKey(1)  # Wait for 1ms to allow the image to be displayed

        except Exception as e:
            print(f"Error processing image: {str(e)}")

lr.start("/media/devrim/4gb/Projects/luckeworld-jun10/LuckyRobot/Build/linux/Linux06_28_2024")