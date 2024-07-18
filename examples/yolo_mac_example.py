import luckyrobots as lr
import cv2
import numpy as np
from ultralytics import YOLO
from PIL import Image, ImageTk
import tkinter as tk
import multiprocessing as mp
import queue

model = YOLO("YOLOv10n.pt")

def run_gui(image_queue):
    root = tk.Tk()
    root.title("YOLO Detection")
    label = tk.Label(root)
    label.pack()

    def update_image():
        try:
            img = image_queue.get_nowait()
            img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
            pil_img = Image.fromarray(img_rgb)
            max_size = (800, 600)
            pil_img.thumbnail(max_size, Image.LANCZOS)
            photo = ImageTk.PhotoImage(pil_img)
            label.config(image=photo)
            label.image = photo
        except queue.Empty:
            pass
        root.after(100, update_image)

    root.after(100, update_image)
    root.mainloop()

def main():
    image_queue = mp.Queue()
    gui_process = mp.Process(target=run_gui, args=(image_queue,))
    gui_process.start()

    @lr.on("robot_output")
    def handle_file_created(robot_images: dict):
        print("robot_images:", robot_images)
        if robot_images:
            if isinstance(robot_images, dict) and 'rgb_cam1' in robot_images:
                image_path = robot_images['rgb_cam1'].get('file_path')
                if image_path:
                    print(f"Processing image: {image_path}")
                    
                    results = model(image_path)
                    image = results[0].plot()
                    
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
                    
                    image_queue.put(img)
                else:
                    print("No file_path found in rgb_cam1")
            else:
                print("Unexpected structure in robot_images")
        else:
            print("No robot_images received")

    lr.start()

if __name__ == "__main__":
    main()