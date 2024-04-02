from datetime import datetime
import cv2
import numpy as np
import os  # Import the os module


class ImageProcessor:

    def __init__(self, frame):
        self.frame = frame

    def process_image(self, server, camera_type: str = "normal_camera"):
        print("Inside process_image method")
        while True:
            frame = server.frame_queue.get()
            if frame is None:
                break
            array = ["w 5000 1", "a 30 1"]
            server.next_move = np.random.choice(array)
            self.frame = frame  # Update self.frame with the new frame data
            resized_frame = cv2.resize(self.frame, (640, 320))  # Resize the frame
            cv2.imshow('stream', resized_frame)
            if cv2.waitKey(1) & 0xFF == ord('q'):  # Press 'q' to exit the loop
                break

            # Create the directory if it doesn't exist
            directory_path = f"images/{camera_type}"
            if not os.path.exists(directory_path):
                os.makedirs(directory_path)

            # Save the frame with a timestamp in the file name
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{directory_path}/{camera_type}_{timestamp}.jpg"
            cv2.imwrite(filename, resized_frame)
            print(f"Saved: {filename}")

        cv2.destroyAllWindows()
