"""Example showing YOLO object detection with Tkinter GUI display for macOS compatibility"""
import cv2
import queue
import asyncio
import numpy as np
import tkinter as tk
import luckyrobots as lr
import multiprocessing as mp

from ultralytics import YOLO
from PIL import Image, ImageTk

# Initialize YOLO model
model = YOLO("YOLOv10n.pt")

# GUI constants
WINDOW_TITLE = "YOLO Detection"
MAX_DISPLAY_SIZE = (800, 600)
GUI_UPDATE_INTERVAL = 100  # milliseconds


def run_gui(image_queue):
    """Run the Tkinter GUI in a separate process"""
    root = tk.Tk()
    root.title(WINDOW_TITLE)
    label = tk.Label(root)
    label.pack()

    def update_image():
        """Update the displayed image from the queue"""
        try:
            # Get the latest image from queue
            img = image_queue.get_nowait()
            
            # Convert BGR to RGB and create PIL image
            img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
            pil_img = Image.fromarray(img_rgb)
            
            # Resize image while maintaining aspect ratio
            pil_img.thumbnail(MAX_DISPLAY_SIZE, Image.LANCZOS)
            
            # Update the label with new image
            photo = ImageTk.PhotoImage(pil_img)
            label.config(image=photo)
            label.image = photo  # Keep a reference to prevent garbage collection
        except queue.Empty:
            pass
        
        # Schedule next update
        root.after(GUI_UPDATE_INTERVAL, update_image)

    root.after(GUI_UPDATE_INTERVAL, update_image)
    root.mainloop()


@lr.message_receiver
async def handle_camera_feed(message, robot_images):
    # Skip if not robot output or no images received
    if message != "robot_output":
        return
    
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
    
    # Send image to GUI process
    handle_camera_feed.image_queue.put(img)


async def main():
    """Example showing YOLO detection with Tkinter GUI display for macOS compatibility"""
    # Create a shared queue for inter-process communication
    image_queue = mp.Queue()
    handle_camera_feed.image_queue = image_queue
    
    # Start GUI process
    gui_process = mp.Process(target=run_gui, args=(image_queue,))
    gui_process.start()
    
    # Start robot communication
    lr.start()


if __name__ == "__main__":
    asyncio.run(main())