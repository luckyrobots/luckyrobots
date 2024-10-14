import luckyrobots as lr
import cv2
import numpy as np
from ultralytics import YOLO
model = YOLO("YOLOv10n.pt")
import asyncio

async def main():
    @lr.message_receiver
    async def handle_file_created(message, robot_images: list):
    
        if message == "robot_output":
            print("robot_images:", robot_images)
            if robot_images:
                
                if isinstance(robot_images, dict) and 'rgb_cam1' in robot_images:
                    image_path = robot_images['rgb_cam1'].get('file_path')
                    if image_path:
                        print(f"Processing image: {image_path}")
                        
                        results = model(image_path)
                        image = results[0].plot()
                        
                        if isinstance(image, np.ndarray):
                            # If image is already a numpy array, use it directly
                            img = image
                        else:
                            try:
                                # Convert bytes to numpy array if necessary
                                nparr = np.frombuffer(image, np.uint8)
                                # Decode the image
                                img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
                            except Exception as e:
                                print(f"Error decoding image: {str(e)}")
                                return

                        if img is None:
                            print("Failed to decode image")
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
    lr.start()

if __name__ == "__main__":
    asyncio.run(main())