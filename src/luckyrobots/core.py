import os
import queue
import time
import sys
import json  # Added this import

from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler


class EventEmitter:
    def __init__(self):
        self.listeners = {}

    def on(self, event, callback):
        if event not in self.listeners:
            self.listeners[event] = []
        self.listeners[event].append(callback)

    def emit(self, event, *args, **kwargs):
        if event in self.listeners:
            for callback in self.listeners[event]:
                callback(*args, **kwargs)

event_emitter = EventEmitter()

def on_message(event):
    def decorator(callback):
        event_emitter.on(event, callback)
        return callback
    return decorator


class Watcher:
    def __init__(self, directory_path):
        self.observer = Observer()
        self.directory_path = directory_path

    def run(self):
        event_handler = Handler()
        self.observer.schedule(event_handler, self.directory_path, recursive=False)
        self.observer.start()
        try:
            while self.observer.is_alive():
                self.observer.join(1)
        except KeyboardInterrupt:
            self.observer.stop()
        self.observer.join()


class Handler(FileSystemEventHandler):
    file_num = 0
    image_stack = {}
    send_bytes = False  # Add this line
    emit_counter = 0

    @classmethod
    def set_send_bytes(cls, value):
        cls.send_bytes = value

    @staticmethod
    def on_created(event):
        if event.is_directory:
            return None
        else:
            pass

    @staticmethod
    def get_file_name(file_path):
        return os.path.basename(file_path)

    @staticmethod
    def on_modified(event):
        if event.is_directory:
            return None
        else:
            # print(f"Received modified event - {event.src_path}")
            Handler.process_file(event.src_path, event.event_type)

    @staticmethod
    def process_file(file_path, event_type):
        file = Handler.get_file_name(file_path)
        current_file_num = int(file.split('_')[0]) if file.split('_')[0].isdigit() else Handler.file_num
        
        if current_file_num == Handler.file_num:
            Handler.add_file(file_path)
        else:
            # emit.counter 5 to give file watcher some warmup time.
            if len(Handler.image_stack) > 0 and Handler.emit_counter > 5:
                print(Handler.emit_counter)
                event_emitter.emit("robot_images_created", Handler.image_stack)
            Handler.emit_counter += 1
            Handler.file_num = current_file_num
            Handler.add_file(file_path)
            
            # print(Handler.image_stack)
        # print(f"Processed file from {event_type} event: {file_path}")

    @staticmethod
    def add_file(file_path):
        file = Handler.get_file_name(file_path)
        file_bytes = None
        file_type = file.split('_', 1)[1].rsplit('.', 1)[0]
        if file_path not in Handler.image_stack:
            if file.endswith('.txt'):
                try:
                    with open(file_path, 'r') as f:
                        file_content = f.read()
                        file_bytes = json.loads(file_content)
                except json.JSONDecodeError:
                    print(f"Error decoding JSON from {file_path}")
                    file_bytes = {}
                except IOError as e:
                    print(f"Error reading file {file_path}: {e}")
                    file_bytes = {}
            else:
                    # Check if send_bytes is True
                if Handler.send_bytes:  # Change this line
                    file_bytes = Handler._read_file_with_retry(file_path)
                else:
                    file_bytes = None
            
            Handler.image_stack[file_type] = {"file_path": file_path, "contents": file_bytes}        


    @staticmethod
    def on_deleted(event):
        if event.is_directory:
            return None
        else:
            # print(f"Received deleted event - {event.src_path}")
            pass

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


def start(binary_path, send_bytes=False):
    if binary_path is None:
        raise ValueError("binary_path is not set.")
    
    if sys.platform == "darwin":  # macOS
        directory_to_watch = os.path.join(binary_path, "Contents", "UE", "LuckEWorld", "CamShots")
    else:  # Windows and other platforms
        directory_to_watch = os.path.join(binary_path, "LuckEWorld", "CamShots")
    
    if not os.path.exists(directory_to_watch):
        raise FileNotFoundError(f"I couldn't find the binary at the path, are you sure it's running and capture mode is on?")
    
    Handler.set_send_bytes(send_bytes)  # Add this line
    watcher = Watcher(directory_to_watch)
    watcher.run()