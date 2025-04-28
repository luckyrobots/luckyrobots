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
import websockets
from pathlib import Path
from typing import Union, Any, Dict, List, Optional

from .watcher import Watcher
from .handler import Handler
from .library_dev import library_dev
from .run_executable import is_luckyworld_running, run_luckyworld_executable


LOCK_FILE = os.path.join(tempfile.gettempdir(), 'luckyworld_lock')

app = FastAPI()


class LuckyRobots:
    """Main class for handling robot communication and control"""
    
    # Class variables
    port = 3000
    host = "0.0.0.0"
    websocket_connections = set()
    
    # TODO: Add a receiver_functions dictionary to store multiple receiver functions

    @staticmethod
    async def send_message(message: Union[str, Dict[str, Any]]) -> None:
        """Send a raw text message or JSON object to all connected WebSocket clients"""
        if isinstance(message, dict):
            message = json.dumps(message)
        
        # Keep track of disconnected clients
        disconnected = set()
        
        # Send to all active connections
        for websocket in LuckyRobots.websocket_connections:
            try:
                await websocket.send_text(message)
            except Exception as e:
                print(f"Error sending message to client: {e}")
                disconnected.add(websocket)
    
        # Remove disconnected clients
        for websocket in disconnected:
            LuckyRobots.websocket_connections.remove(websocket)
            print(f"Removed disconnected client")
            
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
    
    @staticmethod
    async def _handle_websocket_messages(websocket: WebSocket) -> None:
        """Handle incoming WebSocket messages by calling the receiver function"""
        try:
            while True:
                data = await websocket.receive_text()
                if LuckyRobots.receiver_function:
                    await LuckyRobots.receiver_function(data)
        except Exception as e:
            print(f"WebSocket error: {e}")
            
    @staticmethod
    @app.websocket("/ws")
    async def websocket_endpoint(websocket: WebSocket) -> None:
        """WebSocket endpoint handler"""
        
        try:
            await websocket.accept()
            print(f"WebSocket connection established from {websocket.client.host}")
            # Add to active connections
            LuckyRobots.websocket_connections.add(websocket)
            await LuckyRobots._handle_websocket_messages(websocket)
        except Exception as e:
            print(f"WebSocket error: {e}")
        finally:
            # Remove from active connections
            LuckyRobots.websocket_connections.remove(websocket)
            print("WebSocket connection closed")
            
    @staticmethod
    def start(binary_path: Optional[str] = None, send_bytes: bool = False) -> None:
        """Start the LuckyRobots server and application
        
        Args:
            binary_path: Path to the LuckyRobots binary
            send_bytes: Whether to send raw bytes instead of text
        """
        binary_path = LuckyRobots._initialize_binary(binary_path)
        
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

        # Start the WebSocket server and client
        LuckyRobots._start_server()
        LuckyRobots._start_client()
        
        LuckyRobots._display_welcome_message()
        
        LuckyRobots._setup_signal_handlers()
        
        # Start directory watcher
        watcher = Watcher(directory_to_watch)
        watcher.run()
        
    @staticmethod
    def _initialize_binary(binary_path: Optional[str] = None) -> str:
        """Initialize and validate binary path"""
        if binary_path is None:
            binary_path = Path(__file__).parent.parent.parent.parent / "LuckyWorldV2"
            
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
                
        # Give the server time to start
        time.sleep(1)

    @staticmethod
    def _start_client():
        """Start the WebSocket client in a background thread"""
        def client_connect():
            asyncio.run(LuckyRobots._client_connect_async())
        
        client_thread = threading.Thread(target=client_connect, daemon=True)
        client_thread.start()
    
    @staticmethod
    async def _client_connect_async():
        """Async method to connect to WebSocket server and handle messages"""        
        connect_host = "127.0.0.1" if LuckyRobots.host == "0.0.0.0" else LuckyRobots.host
        uri = f"ws://{connect_host}:{LuckyRobots.port}/ws"
        
        try:
            print(f"Attempting to connect to {uri}")
            async with websockets.connect(uri) as websocket:
                print("Client connected to WebSocket server")
                
                while True:
                    response = await websocket.recv()
                    print(f"Server received: {response}")
        except Exception as e:
            print(f"Client connection error: {e}")
        finally:
            LuckyRobots.websocket_connections.remove(websocket)
            print("Client connection closed")
        
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