"""Simple example showing how to display robot camera feed using OpenCV"""

import cv2
import luckyrobots as lr


@lr.message_receiver
async def handle_camera_feed(message, robot_images):
    """Setup a message receiver to handle robot camera feed"""
    # Skip if no images received
    if not robot_images:
        return
        
    # Get the front camera image path
    if 'rgb_cam1' in robot_images:
        image_path = robot_images['rgb_cam1'].get('file_path')
        
        # Read and display the image
        img = cv2.imread(image_path)
        if img is not None:
            cv2.imshow('Robot Camera Feed', img)
            
            # Press 'q' to quit
            if cv2.waitKey(1) & 0xFF == ord('q'):
                cv2.destroyAllWindows()
                await lr.stop()
                


if __name__ == "__main__":
    lr.start()