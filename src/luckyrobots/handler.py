import os
import json
import time
from watchdog.events import FileSystemEventHandler, FileSystemEvent

class Handler(FileSystemEventHandler):
    """
    This class is used to handle the file events from the LuckyRobots server.
    It will read the file and send the contents to the LuckyRobots server.
    """
    file_num = 0
    image_stack = {}
    send_bytes = False
    emit_counter = 0
    lucky_robots = None

    @classmethod
    def set_send_bytes(cls, value: bool) -> None:
        cls.send_bytes = value

    @classmethod
    def set_lucky_robots(cls, lr: object) -> None:
        cls.lucky_robots = lr

    @staticmethod
    def on_created(event: FileSystemEvent):
        """
        This method is called when a new file has been added to the directory.
        """
        if not event.is_directory:
            Handler.process_file(event.src_path, event.event_type)

    @staticmethod
    def get_file_name(file_path: str) -> str:
        return os.path.basename(file_path)

    @staticmethod
    def on_modified(event: FileSystemEvent):
        if not event.is_directory:
            Handler.process_file(event.src_path, event.event_type)

    @staticmethod
    def process_file(file_path: str, event_type: str) -> None:
        """
        This method is called when a file is modified.
        It will read the file and send it to the message receiver function after the file watcher has warmed up.
        """
        file = Handler.get_file_name(file_path)
        # Example file name: "123_camera_rgb.txt" -> file_num would be 123
        current_file_num = int(file.split('_')[0]) if file.split('_')[0].isdigit() else Handler.file_num
        
        Handler.lucky_robots.message_received_sync("robot_output", Handler.image_stack)

        
        if current_file_num == Handler.file_num:
            # Overwrite the file in the image stack if the file number is the same.
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

    @staticmethod
    def add_file(file_path: str) -> None:
        """
        This method is used to add a file to the image stack.
        """
        
        file = Handler.get_file_name(file_path)
        file_bytes = None
        file_type = file.split('_', 1)[1].rsplit('.', 1)[0]
        
        if file_path not in Handler.image_stack:
            if file.endswith('.txt'):
                # Read the file and convert it to a json object.
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
                # Read the file and convert it to a json object.
                if Handler.send_bytes:
                    file_bytes = Handler._read_file_with_retry(file_path)
                else:
                    file_bytes = None
            
            Handler.image_stack[file_type] = {"file_path": file_path, "contents": file_bytes}        


    @staticmethod
    def on_deleted(event: FileSystemEvent) -> None:
        if event.is_directory:
            return None
        else:
            # print(f"Received deleted event - {event.src_path}")
            pass

    @staticmethod
    def _read_file_with_retry(file_path: str, retries: int = 5, delay: int = 1) -> str:
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
