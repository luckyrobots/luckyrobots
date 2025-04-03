import asyncio
import os
import time
import sys
import json
import threading
import tempfile
import platform
from fastapi import FastAPI, WebSocket
import uvicorn
import logging
import random
import signal

from .watcher import Watcher
from .handler import Handler
from .download import check_binary
from .library_dev import library_dev
from .run_executable import is_luckyworld_running, run_luckyworld_executable



LOCK_FILE = os.path.join(tempfile.gettempdir(), 'luckeworld_lock')


app = FastAPI()


class LuckyRobots:
    delegate_object = None
    websocket = None
    port = 3000
    host = "0.0.0.0"
    
    
    @staticmethod
    def set_delegate_object(delegate_object):
        LuckyRobots.set_delegate_object(delegate_object)

    @staticmethod
    def get_websocket():
        return LuckyRobots.websocket

    @staticmethod
    async def message_received(message,data=None):
        # print("LuckyRobots message_received", message)
        if LuckyRobots.receiver_function is not None:
            await LuckyRobots.receiver_function(message,data)

    @staticmethod
    def message_received_sync(message,data=None):
        # print("LuckyRobots message_received_sync", message)
        asyncio.run(LuckyRobots.message_received(message,data))
        
    @staticmethod
    def message_receiver(func):        
        # Check if the function is asynchronous
        if not asyncio.iscoroutinefunction(func):
            # Get the function's name and try to get its location
            func_name = func.__name__
            try:
                func_location = f" in {func.__code__.co_filename}"
            except AttributeError:
                func_location = ""
            
            error_message = (
                f"Error: The message receiver function '{func_name}'{func_location} "
                "must be asynchronous. Use 'async def' to define the function."
            )
            print(error_message)
            LuckyRobots.run_exit_handler()
        
        """Decorator to set the receiver function"""
        LuckyRobots.receiver_function = func
        return func


    @staticmethod
    async def send_message(message):
        if LuckyRobots.websocket is not None:
            await LuckyRobots.websocket.send_text(message)
        else:
            print("WebSocket connection is not established yet.", LuckyRobots.websocket)


    @staticmethod
    async def send_commands(commands):
        def get_random_int():
            return random.randint(0, 1000000)
        
        if isinstance(commands, list):
            instructions = {"LuckyCode": []}
        
            for command in commands:
                instructions["LuckyCode"].append({
                    "ID": str(command["id"]) if isinstance(command, dict) and 'id' in command else str(get_random_int()),
                    "code": str(command["code"]) if isinstance(command, dict) and 'code' in command else str(command),
                    "time": str(int(time.time() * 1000)),
                    "callback": "off"
                })
        else:
            instructions = commands 

        print("instructions", instructions)
        
        # Add this line to actually send the commands
        await LuckyRobots.send_message(json.dumps(instructions))
        
    @staticmethod
    @app.websocket("/ws")
    async def websocket_endpoint(websocket: WebSocket):

        try:
            await websocket.accept()
            print("WebSocket connection established")
            LuckyRobots.websocket = websocket
            # asyncio.run(event_emitter.emit("start",ws))
            
            
        except Exception as e:
            print(f"Failed to establish WebSocket connection: {e}")
            return


        try:
            while True:
                data = await websocket.receive_text()
                await LuckyRobots.message_received(data)
                # handle_event(data)
        except Exception as e:
            print(f"WebSocket error: {e}")
        finally:
            ws = None
            print("WebSocket connection closed")

    def run_server():
        # event_emitter.emit("message", "running server on port 3000")
        # asyncio.get_event_loop().run_until_complete(event_emitter.emit("message", "running server on port 3000"))
        # Configure logging
        logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
        
        # Run the server with custom log config
        uvicorn.run(app, host=LuckyRobots.host, port=LuckyRobots.port, log_level="warning")

    @staticmethod
    def start(binary_path=None, send_bytes=False):
        

        if binary_path is None:
            binary_path = check_binary("./Binary")    
        if not os.path.exists(binary_path):
            print(f"I couldn't find the binary at {binary_path}, please download the latest version of Lucky Robots from:")
            print("")
            print("https://luckyrobots.com/luckyrobots/luckyworld/releases")
            print("")
            print("and unzip it in the same directory as your file ie ./Binary folder")
            print("")
            print("Linux: your executable will be     ./Binary/Luckyrobots.sh")
            print("Windows: your executable will be   ./Binary/Luckyrobots.exe")
            print("MacOS: your executable will be     ./Binary/Luckyrobots.app")
            print("")
            print("If you are running this from a different directory, you can change the lr.start(binary_path='...') parameter to the full path of the binary.")            
            os._exit(1)
        



        if sys.platform == "darwin":  # macOS
            directory_to_watch = os.path.join(binary_path, "luckyrobots.app", "Contents", "UE", "luckyrobots", "robotdata")
        else:  # Windows and other platforms
            directory_to_watch = os.path.join(binary_path, "luckyrobots", "robotdata")
        
        # Create the directory if it doesn't exist
        os.makedirs(directory_to_watch, exist_ok=True)
            
        Handler.set_send_bytes(send_bytes)
        Handler.set_lucky_robots(LuckyRobots)  # Set the LuckyRobots class in Handler
        
        if is_luckyworld_running():
            print("LuckyRobots is already running. Skipping launch.")
        else:
            # Start the LuckEWorld executable
            if "--lr-no-executable" not in sys.argv:
                run_luckyworld_executable(directory_to_watch)

        library_dev() 

        # Run the server in a separate thread
        server_thread = threading.Thread(target=LuckyRobots.run_server, daemon=True)
        server_thread.start()

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
        if platform.system() == "Darwin":
            print("*" * 60)
            print("For macOS users:")
            print("Please be patient. The application may take up to a minute to open on its first launch.")
            print("If the application doesn't appear, please follow these steps:")
            print("1. Open System Settings")
            print("2. Navigate to Privacy & Security")
            print("3. Scroll down and click 'Allow' next to the 'luckyrobots' app")
            print("*" * 60)    
        print("Lucky Robots application started successfully.")
        print("To move the robot from your python code, choose a level on the game, and tick the HTTP checkbox.")
        print("To receive the camera feed from your python code, choose a level on the game, and tick the Capture checkbox.")    
        print("*" * 60)
        
        # Check if the system is macOS

        # Set up a signal handler for SIGINT (Ctrl+C)
        

        def sigint_handler(signum, frame):
            print("\nCtrl+C pressed. Running exit handler...")
            LuckyRobots.run_exit_handler(ctrlc_pressed=True)

        signal.signal(signal.SIGINT, sigint_handler)


        watcher = Watcher(directory_to_watch)
        watcher.run()
            
    @staticmethod     
    def run_exit_handler(ctrlc_pressed=False):

        def signal_handler(sig, frame):
            print("\nExiting gracefully...")
            # Perform any cleanup if necessary
            exit(0)

        # Register the signal handler for SIGINT (Ctrl+C)
        signal.signal(signal.SIGINT, signal_handler)

        # Set up a loop to keep the program running
        
        if ctrlc_pressed:
            print("Exiting...")
            sys.exit(0)
        else:
            print("Press Enter to exit the program")
            try:
                while True:
                    # Use input() to allow the program to be interrupted by Enter key
                    user_input = input()
                    if user_input:
                        print("Exiting...")
                        break
            except KeyboardInterrupt:
                # This block will be executed if Ctrl+C is pressed
                pass



# Remove this line if remove_lock_file is not defined or used:
# atexit.register(remove_lock_file)

# Export the necessary functions and classes
__all__ = ['LuckyRobots']
