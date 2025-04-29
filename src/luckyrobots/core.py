"""Core functionality for LuckyRobots server and client.

This module provides the main LuckyRobots class that handles:
- WebSocket server and clients setup
- Message routing and handling
- File watching and processing
- System initialization and shutdown
"""

import asyncio
import os
import time
import sys
import json
import threading
import tempfile
import platform
import uvicorn
import logging
import signal
import websockets
from pathlib import Path
from typing import Any, Dict, Optional
from fastapi import FastAPI, WebSocket

from .watcher import Watcher
from .handler import Handler
from .models import Observation
from .library_dev import library_dev
from .run_executable import is_luckyworld_running

LOCK_FILE = os.path.join(tempfile.gettempdir(), 'luckyworld_lock')

app = FastAPI()


class LuckyRobots:
    """Main class for handling robot communication and control"""
    
    port = 3000
    host = "0.0.0.0"
    robot_client = None
    world_client = None
    receiver_functions = {}
    
    available_msg_types = ['reset', 'step', 'observation', 'cmd_vel']
    
    @staticmethod
    def set_host(ip_address: str) -> None:
        """Set the host IP address for the WebSocket server"""
        LuckyRobots.host = ip_address

    @staticmethod
    async def send_message(data: Dict[str, Any]) -> None:
        """Send a dictionary as a JSON message to the Lucky World client through the robot endpoint
        
        This method is called by the Python client to send commands to Unreal.
        The message flow is:
        Python Client → /robot endpoint → handle_robot_messages → world_client (Unreal)
        
        Args:
            data: Dictionary to be sent as JSON
        """
        if not isinstance(data, dict):
            raise ValueError("Message must be a dictionary")
        
        if data['msg_type'] not in LuckyRobots.available_msg_types:
            raise ValueError(f"Invalid message type: {data['msg_type']}")
        
        message = json.dumps(data)
        
        try:
            await LuckyRobots.world_client.send_text(message)
        except Exception as e:
            print(f"Error sending message to Lucky World client: {e}")

    @staticmethod
    def message_receiver(msg_type: str = None):
        """Decorator to register an async message handler function with an optional name
        
        Args:
            msg_type: Optional unique identifier for this message receiver. If not provided, the function's __name__ will be used.
                      
        Example:
            ```python
            @lr.message_receiver(msg_type="observation_handler")
            async def handle_observation(data: Optional[Observation] = None) -> None:
                \"\"\"Handle observation updates
                
                Args:
                    data: Optional data, typically the observation
                \"\"\"
                # Process the update here
                pass
            ```
        """
        def decorator(func):
            if not asyncio.iscoroutinefunction(func):
                func_name = func.__name__
                location = getattr(func, "__code__", None)
                location_str = f" in {location.co_filename}" if location else ""
                
                print(f"Error: Message receiver '{func_name}'{location_str} must be async")
                LuckyRobots._run_exit_handler()
                return func
            
            receiver_name = msg_type or func.__name__
            LuckyRobots.receiver_functions[receiver_name] = func
            return func
        
        return decorator
    
    @staticmethod
    async def message_received(msg_type: str, data: Optional[Observation] = None) -> None:
        """Call registered message receiver functions based on file type
        
        Args:
            msg_type: The message type to process
            data: Optional additional data
        """
        if msg_type not in LuckyRobots.receiver_functions:
            print(f"No message receiver registered for {msg_type}")
            return  
        
        func = LuckyRobots.receiver_functions[msg_type]
        
        try:
            await func(data)
        except Exception as e:
            print(f"Error in message receiver '{msg_type}': {e}")

    @staticmethod
    def message_received_sync(msg_type: str, data: Optional[Observation] = None) -> None:
        """Synchronous wrapper for message_received"""
        asyncio.run(LuckyRobots.message_received(msg_type, data))
    
    @staticmethod
    @app.websocket("/robot")
    async def robot_endpoint(websocket: WebSocket) -> None:
        """WebSocket endpoint for Python clients
        
        This endpoint receives messages from Python clients and forwards them to the Unreal world.
        """
        try:
            await websocket.accept()
            LuckyRobots.robot_client = websocket
            await LuckyRobots._handle_robot_messages(websocket)
        except Exception as e:
            print(f"Python client error: {e}")
        finally:
            LuckyRobots.robot_client = None
            print("Python client disconnected")

    @staticmethod
    @app.websocket("/world")
    async def world_endpoint(websocket: WebSocket) -> None:
        """WebSocket endpoint for Lucky World clients"""
        try:
            await websocket.accept()
            LuckyRobots.world_client = websocket
            await LuckyRobots._handle_world_messages(websocket)
        except Exception as e:
            print(f"Lucky World client error: {e}")
        finally:
            LuckyRobots.world_client = None
            print("Lucky World client disconnected")

    @staticmethod
    async def _handle_world_messages(websocket: WebSocket) -> None:
        """Handle messages sent from Lucky World client"""
        try:
            while True:
                data = await websocket.receive_text()
                if data['msg_type'] not in LuckyRobots.available_msg_types:
                    print(f"Received invalid message type: {data['msg_type']}")
                    continue
                
                try:
                    # Handle the message according to the message type
                    if data['msg_type'] in ['reset', 'step']:
                        await LuckyRobots.robot_client.send_text(json.dumps(data))
                    elif data['msg_type'] == 'observation':
                        observation = Observation(**json.loads(data))
                        await LuckyRobots.message_received("observation", observation)
                except json.JSONDecodeError:
                    print("Received invalid JSON from LuckyWorld client")
        except Exception as e:
            print(f"Error handling LuckyWorld client message: {e}")

    @staticmethod
    def start(binary_path: Optional[str] = None, send_bytes: bool = False, keep_alive: bool = True) -> None:
        """Start the LuckyRobots server and application
        
        Args:
            binary_path: Path to the LuckyRobots binary
            send_bytes: Whether to send raw bytes instead of text
            keep_alive: Whether to keep the main thread alive
        """
        binary_path = LuckyRobots._initialize_binary(binary_path)
        
        # Configure handler
        Handler.set_send_bytes(send_bytes)
        Handler.set_lucky_robots(LuckyRobots)
        
        # Start application if needed
        if not is_luckyworld_running() and "--lr-no-executable" not in sys.argv:
            """Check if Lucky World is running, if not, run the executable"""
            pass
            # run_luckyworld_executable(directory_to_watch)

        library_dev()

        # Start the WebSocket server and client
        LuckyRobots._start_server()
        LuckyRobots._start_luckyrobots_client()
        
        LuckyRobots._display_welcome_message()
        
        LuckyRobots._setup_signal_handlers()        
        LuckyRobots._setup_directory_watcher(binary_path)
        
        if keep_alive: 
            while True:
                time.sleep(1)

    @staticmethod
    def _initialize_binary(binary_path: Optional[str] = None) -> str:
        """Initialize and validate binary path"""
        if binary_path is None:
            binary_path = Path(__file__).parent.parent.parent.parent / "LuckyWorldV2"
            
        if not os.path.exists(binary_path):
            print(f"Binary not found at {binary_path}, please download the latest version of Lucky World from:")
            print("\nhttps://luckyrobots.com/luckyrobots/luckyworld/releases")
            print("\nand unzip it in the same directory as your file ie ./Binary folder")
            print("\nLinux: your executable will be     ./Binary/LuckyWorld.sh")
            print("Windows: your executable will be   ./Binary/LuckyWorld.exe")
            print("MacOS: your executable will be     ./Binary/LuckyWorld.app")
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
    def _start_luckyrobots_client():
        """Start the luckyrobots client in a background thread"""
        def client_connect():
            asyncio.run(LuckyRobots._client_connect_async())
        
        client_thread = threading.Thread(target=client_connect, daemon=True)
        client_thread.start()
    
    @staticmethod
    async def _client_connect_async():
        """Async method to connect to WebSocket server and handle messages"""        
        connect_host = "127.0.0.1" if LuckyRobots.host == "0.0.0.0" else LuckyRobots.host
        uri = f"ws://{connect_host}:{LuckyRobots.port}/luckyrobots"
        
        try:
            async with websockets.connect(uri) as websocket:                
                while True:
                    response = await websocket.recv()
                    print(f"Server received: {response}")
        except Exception as e:
            print(f"Client connection error: {e}")
        
    @staticmethod
    def _display_welcome_message() -> None:
        """Display welcome message and instructions"""
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
            LuckyRobots._run_exit_handler(ctrlc_pressed=True)
            
        signal.signal(signal.SIGINT, sigint_handler)
        
    @staticmethod
    def _setup_directory_watcher(binary_path: str) -> None:
        """Set up the directory watcher in a background thread"""
        if sys.platform == "darwin":
            directory = os.path.join(binary_path, "luckyrobots.app", "Contents", 
                                   "UE", "luckyrobots", "robotdata")
        else:
            directory = os.path.join(binary_path, "luckyrobots", "robotdata")
            
        os.makedirs(directory, exist_ok=True)

        watcher = Watcher(directory)
        # Add watcher in background thread
        watcher_thread = threading.Thread(target=watcher.run, daemon=True)
        watcher_thread.start()

    @staticmethod
    def _run_exit_handler(ctrlc_pressed: bool = False) -> None:
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