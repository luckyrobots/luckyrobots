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

from typing import Union, Any, Dict, List, Optional

from .watcher import Watcher
from .handler import Handler
from .download import check_binary
from .library_dev import library_dev
from .run_executable import is_luckyworld_running, run_luckyworld_executable


# Constants
LOCK_FILE = os.path.join(tempfile.gettempdir(), 'luckyworld_lock')
DEFAULT_PORT = 3000
DEFAULT_HOST = "0.0.0.0"

app = FastAPI()


class LuckyRobots:
    """Main class for handling robot communication and control"""
    
    # Class variables
    websocket = None
    port = DEFAULT_PORT
    host = DEFAULT_HOST
    
    @staticmethod
    async def send_message(message: Union[str, Dict[str, Any]]) -> None:
        """Send a raw text message or JSON object over WebSocket"""
        if LuckyRobots.websocket is not None:
            if isinstance(message, dict):
                message = json.dumps(message)
            await LuckyRobots.websocket.send_text(message)
        else:
            print("WebSocket connection is not established yet.")
            
    @staticmethod
    async def send_commands(commands: Union[str, List[Dict[str, Any]]]) -> None:
        """Send formatted robot commands
        
        Args:
            commands: List of command strings or command dictionaries
        """
        if not isinstance(commands, list):
            await LuckyRobots.send_message(commands)
            return

        instructions = {
            "LuckyCode": [
                {
                    "ID": str(command.get("id", random.randint(0, 1000000))),
                    "code": str(command.get("code", command)),
                    "time": str(int(time.time() * 1000)),
                    "callback": "off"
                }
                for command in (
                    commands if all(isinstance(c, dict) for c in commands)
                    else [{"code": c} for c in commands]
                )
            ]
        }
        
        print("Sending instructions:", instructions)
        await LuckyRobots.send_message(instructions)

    @staticmethod
    def message_receiver(func):
        """Decorator to register an async message handler function"""
        if not asyncio.iscoroutinefunction(func):
            func_name = func.__name__
            location = getattr(func, "__code__", None)
            location_str = f" in {location.co_filename}" if location else ""
            
            print(f"Error: Message receiver '{func_name}'{location_str} must be async")
            LuckyRobots.run_exit_handler()
            return func

        LuckyRobots.receiver_function = func
        return func
    
    @staticmethod
    async def message_received(message, data: Optional[Any] = None):
        if LuckyRobots.receiver_function is not None:
            await LuckyRobots.receiver_function(message, data)

    @staticmethod
    def message_received_sync(message, data: Optional[Any] = None):
        asyncio.run(LuckyRobots.message_received(message, data))
    
    @classmethod
    async def _handle_websocket_messages(cls, websocket: WebSocket) -> None:
        """Handle incoming WebSocket messages by calling the receiver function"""
        try:
            while True:
                data = await websocket.receive_text()
                if cls.receiver_function:
                    await cls.receiver_function(data)
        except Exception as e:
            print(f"WebSocket error: {e}")
            
    @classmethod
    @app.websocket("/ws")
    async def websocket_endpoint(cls, websocket: WebSocket) -> None:
        """WebSocket endpoint handler"""
        try:
            await websocket.accept()
            print("WebSocket connection established")
            cls.websocket = websocket
            await cls._handle_websocket_messages(websocket)
        except Exception as e:
            print(f"WebSocket error: {e}")
        finally:
            cls.websocket = None
            print("WebSocket connection closed")
            
    @staticmethod
    def start(binary_path: Optional[str] = None, send_bytes: bool = False) -> None:
        """Start the LuckyRobots server and application
        
        Args:
            binary_path: Path to the LuckyRobots binary
            send_bytes: Whether to send raw bytes instead of text
        """
        # Initialize binary path
        binary_path = LuckyRobots._initialize_binary(binary_path)
        
        # Set up directory watching
        directory_to_watch = LuckyRobots._setup_watch_directory(binary_path)
        
        # Configure handler
        Handler.set_send_bytes(send_bytes)
        Handler.set_lucky_robots(LuckyRobots)
        
        # Start application if needed
        if not is_luckyworld_running() and "--lr-no-executable" not in sys.argv:
            """Check if LuckyWorld is running, if not, run the executable"""
            pass
            # run_luckyworld_executable(directory_to_watch)

        library_dev()

        # Start server in background
        LuckyRobots._start_server()
        
        # Display welcome message
        LuckyRobots._display_welcome_message()
        
        # Set up signal handlers
        LuckyRobots._setup_signal_handlers()
        
        # Start directory watcher
        watcher = Watcher(directory_to_watch)
        watcher.run()
        
    @staticmethod
    def _initialize_binary(binary_path: Optional[str] = None) -> str:
        """Initialize and validate binary path"""
        if binary_path is None:
            binary_path = check_binary("./Binary")
            
        if not os.path.exists(binary_path):
            print(f"Binary not found at {binary_path}, please download the latest version of Lucky Robots from:")
            print("\nhttps://luckyrobots.com/luckyrobots/luckyworld/releases")
            print("\nand unzip it in the same directory as your file ie ./Binary folder")
            print("\nLinux: your executable will be     ./Binary/Luckyrobots.sh")
            print("Windows: your executable will be   ./Binary/Luckyrobots.exe")
            print("MacOS: your executable will be     ./Binary/Luckyrobots.app")
            print("\nIf you are running this from a different directory, you can change the lr.start(binary_path='...') parameter to the full path of the binary.")
            os._exit(1)
            
        return binary_path
    
    @staticmethod
    def _setup_watch_directory(binary_path: str) -> str:
        """Set up and return the directory to watch"""
        if sys.platform == "darwin":
            directory = os.path.join(binary_path, "luckyrobots.app", "Contents", 
                                   "UE", "luckyrobots", "robotdata")
        else:
            directory = os.path.join(binary_path, "luckyrobots", "robotdata")
            
        os.makedirs(directory, exist_ok=True)
        return directory

    @staticmethod
    def _start_server() -> None:
        """Start the WebSocket server in a background thread"""
        def run_server():
            logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
            uvicorn.run(app, host=LuckyRobots.host, port=LuckyRobots.port, log_level="warning")
            
        server_thread = threading.Thread(target=run_server, daemon=True)
        server_thread.start()

    @staticmethod
    def _display_welcome_message() -> None:
        """Display welcome message and instructions"""
        print("*" * 60)
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
        print("To move the robot: Choose a level and tick the HTTP checkbox.")
        print("To receive camera feed: Choose a level and tick the Capture checkbox.")
        print("*" * 60)

    @staticmethod
    def _setup_signal_handlers() -> None:
        """Set up handlers for graceful shutdown"""
        def sigint_handler(signum, frame):
            print("\nCtrl+C pressed. Exiting...")
            LuckyRobots.run_exit_handler(ctrlc_pressed=True)
            
        signal.signal(signal.SIGINT, sigint_handler)

    @staticmethod
    def run_exit_handler(ctrlc_pressed: bool = False) -> None:
        """Handle program exit"""
        if ctrlc_pressed:
            print("Exiting...")
            sys.exit(0)
            
        print("Press Enter to exit the program")
        try:
            while True:
                if input():
                    break
        except KeyboardInterrupt:
            pass
        finally:
            print("Exiting...")
            sys.exit(0)