import os
import json
import time
from watchdog.events import FileSystemEventHandler


class Handler(FileSystemEventHandler):
    file_num = 0
    image_stack = {}
    send_bytes = False
    emit_counter = 0
    lucky_robots = None  # Initialize this as None
    

    @classmethod
    def set_send_bytes(cls, value):
        cls.send_bytes = value

    @classmethod
    def set_lucky_robots(cls, lr):
        cls.lucky_robots = lr

    @staticmethod
    def on_created(event):
        if not event.is_directory:
            Handler.process_file(event.src_path, event.event_type)

    @staticmethod
    def get_file_name(file_path):
        return os.path.basename(file_path)

    @staticmethod
    def on_modified(event):
        if not event.is_directory:
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
                if Handler.lucky_robots is not None:
                    Handler.lucky_robots.message_received_sync("robot_output", Handler.image_stack)
                else:
                    print("Warning: lucky_robots is not set in Handler class")
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
                if Handler.send_bytes:
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
