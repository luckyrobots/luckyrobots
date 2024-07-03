import os
import time
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

from Playground import event_emitter
from Playground.process_image import ProcessImage

image_processor = ProcessImage()

class Watcher:
    DIRECTORY_TO_WATCH = "C:\\Users\\Goran\\Downloads\\Windows06_28_2024\\Windows06_28_2024\\LuckEWorld\\CamShots"

    def __init__(self):
        self.observer = Observer()

    def run(self):
        event_handler = Handler()
        self.observer.schedule(event_handler, self.DIRECTORY_TO_WATCH, recursive=False)
        self.observer.start()
        try:
            while True:
                time.sleep(5)
        except KeyboardInterrupt:
            self.observer.stop()
        self.observer.join()


class Handler(FileSystemEventHandler):
    file_num = 0
    image_stack = []

    @staticmethod
    def on_created(event):
        if event.is_directory:
            return None
        else:
            print(f"Received created event - {event.src_path}")
            file = Handler.get_file_name(event.src_path)
            current_file_num = int(file.split('_')[0]) if file.split('_')[0].isdigit() else Handler.file_num
            file_bytes = Handler._read_file_with_retry(event.src_path)

            if current_file_num == Handler.file_num:
                Handler.image_stack.append({"file_path": event.src_path, "file_bytes": file_bytes})
            else:
                event_emitter.emit("robot_images", Handler.image_stack)
                Handler.file_num = current_file_num
                Handler.image_stack = [{"file_path": event.src_path, "file_bytes": file_bytes}]

    @staticmethod
    def get_file_name(file_path):
        return os.path.basename(file_path)

    @staticmethod
    def on_modified(event):
        if event.is_directory:
            return None
        else:
            print(f"Received modified event - {event.src_path}")

    @staticmethod
    def on_deleted(event):
        if event.is_directory:
            return None
        else:
            print(f"Received deleted event - {event.src_path}")

    @staticmethod
    def _read_file_with_retry(file_path, retries=5, delay=1):
        for attempt in range(retries):
            try:
                with open(file_path, 'rb') as f:
                    content = f.read()
                    return content
            except (PermissionError, FileNotFoundError) as e:
                print(f"Attempt {attempt + 1}: Failed to read {file_path} - {e}")
                time.sleep(delay)
        else:
            print(f"Failed to read {file_path} after {retries} attempts")


if __name__ == '__main__':
    w = Watcher()
    w.run()
