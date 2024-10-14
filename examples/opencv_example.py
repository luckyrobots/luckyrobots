import luckyrobots as lr
import cv2
import numpy as np
import asyncio

async def main():
    @lr.message_receiver
    async def message_receiver(message, robot_images: dict):
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
    
    lr.start()
             
if __name__ == "__main__":
    asyncio.run(main())