"""
This module extends the LuckyRobots class with ROS-like functionality including:
- Publisher/Subscriber system with WebSocket support for distributed communication
- Service system with timeout and error handling
- Parameter server for configuration
- Transform system for coordinate frames
- Node management with distributed node support
"""

import asyncio
import json
import logging
import os
import platform
import signal
import sys
import threading
import time
from pathlib import Path
from typing import Dict, Optional

import uvicorn
from fastapi import FastAPI, WebSocket, WebSocketDisconnect

from .manager import Manager
from ..message.transporter import MessageType, TransportMessage
from ..message.pubsub import Publisher
from ..message.srv.types import Reset, Step
from ..runtime.run_executable import is_luckyworld_running
from ..utils.handler import Handler
from ..utils.library_dev import library_dev
from ..utils.watcher import Watcher
from .models import CameraShape, ObservationModel, ResetModel, StepModel
from .node import Node
from .parameters import load_from_file, set_param

# Setup logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("lucky_robots")

app = FastAPI()
manager = Manager()


class LuckyRobots(Node):
    # Singleton instance
    _instance = None
    _lock = threading.RLock()

    # Configuration
    port = 3000
    host = "0.0.0.0"

    # WebSocket clients
    robot_client = None
    world_client = None

    # Node management
    _nodes: Dict[str, "Node"] = {}
    _running = False
    _shutdown_event = threading.Event()

    def __new__(cls):
        """Ensure only one instance of LuckyRobots exists"""
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(LuckyRobots, cls).__new__(cls)
            return cls._instance

    def __init__(self):
        """Initialize LuckyRobots"""
        # Skip initialization if already initialized
        if hasattr(self, "_initialized"):
            return

        # Start the websocket server right away to listen for a connection from lucky robots manager
        self._start_websocket_server()

        super().__init__("lucky_robots_manager", "", "localhost", self.port)

        self._initialized = True
        self._nodes = {}
        self._running = False
        self._shutdown_event = threading.Event()

        # Load default parameters
        self._load_default_params()

    def _load_default_params(self) -> None:
        """Load default parameters"""
        # Core parameters
        set_param("core/host", self.host)
        set_param("core/port", self.port)

        # Look for parameter files
        param_files = [
            "luckyrobots_params.json",
            os.path.expanduser("~/.luckyrobots/params.json"),
        ]

        for param_file in param_files:
            if os.path.exists(param_file):
                load_from_file(param_file)
                logger.info(f"Loaded parameters from {param_file}")

    @staticmethod
    def set_host(ip_address: str) -> None:
        """Set the host IP address for the WebSocket server"""
        LuckyRobots.host = ip_address
        set_param("core/host", ip_address)

    def register_node(self, node: "Node") -> None:
        """Register a node with the LuckyRobots instance.

        Args:
            node: The node to register
        """
        self._nodes[node.full_name] = node
        logger.info(f"Registered node: {node.full_name}")

    def _setup(self):
        """Setup the LuckyRobots core."""
        pass

    def start(
        self,
        binary_path: Optional[str] = None,
        send_bytes: bool = False,
    ) -> None:
        """Start the LuckyRobots core

        Args:
            binary_path: Path to the LuckyRobots binary
            send_bytes: Whether to send raw bytes instead of text
        """
        if self._running:
            logger.warning("LuckyRobots is already running")
            return

        binary_path = self._initialize_binary(binary_path)

        # Configure handler
        Handler.set_send_bytes(send_bytes)
        Handler.set_lucky_robots(self)

        if not is_luckyworld_running() and "--lr-no-executable" not in sys.argv:
            # Set up the directory to watch
            directory_to_watch = self._setup_watch_directory(binary_path)

            # Run the executable
            # run_luckyworld_executable(directory_to_watch)

        library_dev()

        self._setup_signal_handlers()
        self._setup_directory_watcher(binary_path)

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        # Run create_service calls in the event loop since it needs to wait for response from luckyworld
        self.reset_service = loop.run_until_complete(
            self.create_service(Reset, "/reset", self.handle_reset)
        )
        self.step_service = loop.run_until_complete(
            self.create_service(Step, "/step", self.handle_step)
        )

        loop.close()

        # Start all registered nodes
        for node in self._nodes.values():
            try:
                node.start()
            except Exception as e:
                logger.error(f"Error starting node {node.full_name}: {e}")

        super().start()

        self._running = True

    def _initialize_binary(self, binary_path: Optional[str] = None) -> str:
        """Initialize and validate binary path"""
        if binary_path is None:
            binary_path = (
                Path(__file__).parent.parent.parent.parent.parent / "LuckyWorldV2"
            )

        if not os.path.exists(binary_path):
            print(
                f"Binary not found at {binary_path}, please download the latest version of Lucky World from:"
            )
            print("\nhttps://luckyrobots.com/luckyrobots/luckyworld/releases")
            print(
                "\nand unzip it in the same directory as your file ie ./Binary folder"
            )
            print("\nLinux: your executable will be     ./Binary/LuckyWorld.sh")
            print("Windows: your executable will be   ./Binary/LuckyWorld.exe")
            print("MacOS: your executable will be     ./Binary/LuckyWorld.app")
            print(
                "\nIf you are running this from a different directory, you can change the lr.start(binary_path='...') parameter to the full path of the binary."
            )
            os._exit(1)

        return binary_path

    def _setup_watch_directory(self, binary_path: str) -> str:
        """Set up and return the directory to watch"""
        if sys.platform == "darwin":
            directory = os.path.join(
                binary_path,
                "luckyrobots.app",
                "Contents",
                "UE",
                "luckyrobots",
                "robotdata",
            )
        else:
            directory = os.path.join(binary_path, "luckyrobots", "robotdata")

        os.makedirs(directory, exist_ok=True)
        return directory

    def _start_websocket_server(self) -> None:
        """Start the WebSocket server in a background thread"""

        def run_server():
            logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
            uvicorn.run(app, host=self.host, port=self.port, log_level="warning")

        server_thread = threading.Thread(target=run_server, daemon=True)
        server_thread.start()

        # Give the server time to start
        time.sleep(1)

    async def _process_robot_message(self, message: str) -> None:
        """Process messages received from the robot client"""
        try:
            data = json.loads(message)
            message_type = data.get("msg_type")

            if message_type == "observation":
                observation = ObservationModel(**data)
                # Publish the observation to subscribers
                for publisher in Publisher.get_publishers_for_topic("/observation"):
                    publisher.publish(observation)
            elif message_type == "reset":
                reset = ResetModel(**data)
                # Publish the reset to subscribers
                for publisher in Publisher.get_publishers_for_topic("/reset"):
                    publisher.publish(reset)
            elif message_type == "step":
                step = StepModel(**data)
                # Publish the step to subscribers
                for publisher in Publisher.get_publishers_for_topic("/step"):
                    publisher.publish(step)
            else:
                logger.warning(f"Unknown message type: {message_type}")
        except json.JSONDecodeError:
            logger.error("Received invalid JSON from robot client")
        except Exception as e:
            logger.error(f"Error processing robot message: {e}")

    def _setup_directory_watcher(self, binary_path: str) -> None:
        """Set up the directory watcher in a background thread"""
        directory = self._setup_watch_directory(binary_path)

        watcher = Watcher(directory)
        watcher_thread = threading.Thread(target=watcher.run, daemon=True)
        watcher_thread.start()

    def _setup_signal_handlers(self) -> None:
        """Set up handlers for graceful shutdown"""

        def sigint_handler(signum, frame):
            print("\nCtrl+C pressed. Shutting down...")
            self.shutdown()

        signal.signal(signal.SIGINT, sigint_handler)

    def _display_welcome_message(self) -> None:
        """Display welcome message and instructions"""
        print("*" * 60)
        print(
            "                                                                                "
        )
        print(
            "                                                                                "
        )
        print("▄▄▌  ▄• ▄▌ ▄▄· ▄ •▄  ▄· ▄▌▄▄▄        ▄▄▄▄·       ▄▄▄▄▄.▄▄ · ")
        print("██•  █▪██▌▐█ ▌▪█▌▄▌▪▐█▪██▌▀▄ █·▪     ▐█ ▀█▪▪     •██  ▐█ ▀. ")
        print("██▪  █▌▐█▌██ ▄▄▐▀▀▄·▐█▌▐█▪▐▀▀▄  ▄█▀▄ ▐█▀▀█▄ ▄█▀▄  ▐█.▪▄▀▀▀█▄")
        print("▐█▌▐▌▐█▄█▌▐███▌▐█.█▌ ▐█▀·.▐█•█▌▐█▌.▐▌██▄▪▐█▐█▌.▐▌ ▐█▌·▐█▄▪▐█")
        print(".▀▀▀  ▀▀▀ ·▀▀▀ ·▀  ▀  ▀ • .▀  ▀ ▀█▄▀▪·▀▀▀▀  ▀█▄▀▪ ▀▀▀  ▀▀▀▀ ")
        print(
            "                                                                                "
        )
        print(
            "                                                                                "
        )
        if platform.system() == "Darwin":
            print("*" * 60)
            print("For macOS users:")
            print(
                "Please be patient. The application may take up to a minute to open on its first launch."
            )
            print("If the application doesn't appear, please follow these steps:")
            print("1. Open System Settings")
            print("2. Navigate to Privacy & Security")
            print("3. Scroll down and click 'Allow' next to the 'luckyrobots' app")
            print("*" * 60)
        print("Lucky Robots application started successfully.")
        print("To move the robot: Choose a level and tick the HTTP checkbox.")
        print("To receive camera feed: Choose a level and tick the Capture checkbox.")
        print("*" * 60)

    async def handle_reset(self, request: Reset.Request) -> Reset.Response:
        """Handle the reset request"""

        # Create a dummy camera shape
        camera_shape = CameraShape(image_width=640, image_height=480, channel=3)

        # Create dummy camera data with correct field names
        camera_data = {
            "cameraName": "front_camera",
            "dtype": "uint8",
            "shape": camera_shape.dict(),
            "filePath": "/tmp/dummy_image.jpg",
        }

        # Create dummy observation with correct field names
        observation = {
            "timeStamp": int(time.time() * 1000),  # Current time in milliseconds
            "id": "dummy_observation_1",
            "observationState": {
                "left_wheel": 0,
                "right_wheel": 0,
                "arm_joint1": 0,
                "arm_joint2": 0,
            },
            "observationCameras": [camera_data],
        }

        return Reset.Response(
            success=True,
            message="Reset successful",
            observation=ObservationModel(**observation),
            info={"status": "reset_complete"},
        )

    async def handle_step(self, request: Step.Request) -> Step.Response:
        """Handle the step request"""
        # Create a dummy camera shape
        camera_shape = CameraShape(image_width=640, image_height=480, channel=3)

        # Create dummy camera data with correct field names
        camera_data = {
            "cameraName": "front_camera",
            "dtype": "uint8",
            "shape": camera_shape.dict(),
            "filePath": "/tmp/dummy_image.jpg",
        }

        # Create dummy observation with correct field names
        observation = {
            "timeStamp": int(time.time() * 1000),  # Current time in milliseconds
            "id": "dummy_observation_2",
            "observationState": {
                "left_wheel": 0,
                "right_wheel": 0,
                "arm_joint1": 0,
                "arm_joint2": 0,
            },
            "observationCameras": [camera_data],
        }

        return Step.Response(
            success=True,
            message="Step successful",
            observation=ObservationModel(**observation),
            info={"status": "step_complete"},
        )

    def shutdown(self) -> None:
        """Shut down LuckyRobots and all nodes"""
        if not self._running:
            return

        self._running = False

        # Shutdown all nodes
        for node in self._nodes.values():
            try:
                node.shutdown()
            except Exception as e:
                logger.error(f"Error shutting down node {node.full_name}: {e}")

        # Shutdown this node
        super().shutdown()

        self._shutdown_event.set()
        logger.info("LuckyRobots shutdown complete")

    def spin(self) -> None:
        """Keep the main thread alive until shutdown"""
        if not self._running:
            logger.warning("LuckyRobots is not running")
            return

        self._display_welcome_message()

        logger.info("LuckyRobots spinning")
        try:
            self._shutdown_event.wait()
        except KeyboardInterrupt:
            self.shutdown()
        logger.info("LuckyRobots stopped spinning")


@app.websocket("/nodes")
async def nodes_endpoint(websocket: WebSocket) -> None:
    """WebSocket endpoint for node communication"""
    await websocket.accept()

    node_name = None

    try:
        # Wait for the first message, which should be a NODE_ANNOUNCE
        message_text = await websocket.receive_text()
        message_data = json.loads(message_text)
        message = TransportMessage(**message_data)

        if message.msg_type != MessageType.NODE_ANNOUNCE:
            logger.warning(
                f"First message from node should be NODE_ANNOUNCE, got {message.msg_type}"
            )
            await websocket.close(4000, "First message must be NODE_ANNOUNCE")
            return

        # Register the node
        node_name = message.node_name
        await manager.register_node(node_name, websocket)

        # Process messages until disconnection
        while True:
            message_text = await websocket.receive_text()
            try:
                message_data = json.loads(message_text)
                message = TransportMessage(**message_data)

                # Process the message based on its type
                if message.msg_type == MessageType.SUBSCRIBE:
                    await manager.subscribe(node_name, message.topic_or_service)
                elif message.msg_type == MessageType.UNSUBSCRIBE:
                    await manager.unsubscribe(node_name, message.topic_or_service)
                elif message.msg_type == MessageType.SERVICE_REGISTER:
                    await manager.register_service(node_name, message.topic_or_service)
                elif message.msg_type == MessageType.SERVICE_UNREGISTER:
                    await manager.unregister_service(
                        node_name, message.topic_or_service
                    )
                elif message.msg_type == MessageType.NODE_SHUTDOWN:
                    logger.info(f"Node {node_name} shutting down")
                    break
                else:
                    # Route other messages (PUBLISH, SERVICE_REQUEST, SERVICE_RESPONSE)
                    await manager.route_message(message)
            except json.JSONDecodeError:
                logger.error(f"Received invalid JSON from {node_name}")
            except Exception as e:
                logger.error(f"Error processing message from {node_name}: {e}")
    except WebSocketDisconnect:
        logger.info(f"Node {node_name} disconnected")
