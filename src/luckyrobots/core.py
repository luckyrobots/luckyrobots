import os
import time
import sys
import json
import threading
import socket
import multiprocessing
import psutil
import tempfile
import atexit

from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from .comms import create_instructions, run_server
from .event_handler import event_emitter, on
from .download import check_binary
from .library_dev import library_dev
from .run_executable import is_luckeworld_running, run_luckeworld_executable

LOCK_FILE = os.path.join(tempfile.gettempdir(), 'luckeworld_lock')

def send_message(commands):
    print("send_message", commands)
    for command in commands:
        create_instructions(command)

def start(binary_path=None, send_bytes=False):
    if binary_path is None:
        binary_path = check_binary()    
    if not os.path.exists(binary_path):
        print(f"I couldn't find the binary at {binary_path}, are you sure it's running and capture mode is on?")
        os._exit(1)
    



    if sys.platform == "darwin":  # macOS
        directory_to_watch = os.path.join(binary_path, "luckyrobots.app", "Contents", "UE", "luckyrobots", "robotdata")
    else:  # Windows and other platforms
        directory_to_watch = os.path.join(binary_path, "luckyrobots", "robotdata")
    
    # Create the directory if it doesn't exist
    os.makedirs(directory_to_watch, exist_ok=True)
        
    Handler.set_send_bytes(send_bytes)
    
    if is_luckeworld_running():
        print("LuckyRobots is already running. Skipping launch.")
    else:
        # Start the LuckEWorld executable
        run_luckeworld_executable(directory_to_watch)

    library_dev()

    # Run the server in a separate thread
    server_thread = threading.Thread(target=run_server, daemon=True)
    server_thread.start()
    
    # Wait for the server to start
    max_wait_time = 10  # Maximum wait time in seconds
    start_time = time.time()
    while time.time() - start_time < max_wait_time:
        try:
            # Try to connect to the server
            with socket.create_connection(("localhost", 3000), timeout=1):
                break
        except (ConnectionRefusedError, socket.timeout):
            time.sleep(0.1)
    else:
        print("Warning: Server may not have started properly")
    
    # Emit the start event
    event_emitter.emit("start")

    print("*" * 60)
    print("                                                                                ")
    print("                                                                                ")
    print("▄▄▌  ▄• ▄▌ ▄▄· ▄ •▄  ▄· ▄▌▄▄▄        ▄▄▄▄·       ▄▄▄▄▄.▄▄ · ")
    print("██•  █▪██▌▐█ ▌▪█▌▄▌▪▐█▪██▌▀▄ █·▪     ▐█ ▀█▪▪     •██  ▐█ ▀. ")
    print("██▪  █▌▐█▌██ ▄▄▐▀▀▄·▐█▌▐█▪▐▀▀▄  ▄█▀▄ ▐█▀▀█▄ ▄█▀▄  ▐█.▪▄▀▀▀█▄")
    print("▐█▌▐▌▐█▄█▌▐███▌▐█.█▌ ▐█▀·.▐█•█▌▐█▌.▐▌██▄▪▐█▐█▌.▐▌ ▐█▌·▐█▄▪▐█")
    print(".▀▀▀  ▀▀▀ ·▀▀▀ ·▀  ▀  ▀ • .▀  ▀ ▀█▄▀▪·▀▀▀▀  ▀█▄▀▪ ▀▀▀  ▀▀▀▀ ")
    print("                                                                                ")
    print("                                                                                ")
    print("Lucky Robots application started successfully.")
    print("To move the robot from your python code, choose a level on the game, and tick the HTTP checkbox.")
    print("To receive the camera feed from your python code, choose a level on the game, and tick the Capture checkbox.")    
    print("*" * 60)
    
    watcher = Watcher(directory_to_watch)
    watcher.run()

if __name__ == '__main__':
    multiprocessing.freeze_support()
    start()

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
    send_bytes = False
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
                event_emitter.emit("robot_output", Handler.image_stack)
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

# Remove this line if remove_lock_file is not defined or used:
# atexit.register(remove_lock_file)