"""
This module extends the LuckyRobots class with ROS-like functionality including:
- Publisher/Subscriber system with WebSocket support for distributed communication
- Service system with timeout and error handling
- Parameter server for configuration
- Transform system for coordinate frames
- Node management with distributed node support
"""

import msgpack
import asyncio
import logging
import os
import uuid
import platform
import signal
import sys
import threading
import time
from pathlib import Path
from typing import Dict, Optional

import uvicorn
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from websocket import create_connection

from .manager import Manager
from ..message.transporter import MessageType, TransportMessage
from ..message.srv.types import Reset, Step
from ..runtime.run_executable import is_luckyworld_running, run_luckyworld_executable
from ..utils.handler import Handler
from ..utils.library_dev import library_dev
from ..utils.watcher import Watcher
from ..core.models import ObservationModel
from .node import Node
from .parameters import load_from_file, set_param
from ..utils.event_loop import (
    get_event_loop,
    initialize_event_loop,
    shutdown_event_loop,
)

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("lucky_robots")

app = FastAPI()
manager = Manager()


class LuckyRobots(Node):
    port = 3000
    host = "0.0.0.0"

    robot_client = None
    world_client = None

    _pending_resets = {}
    _pending_steps = {}

    _nodes: Dict[str, "Node"] = {}
    _running = False
    _shutdown_event = threading.Event()

    _event_loop = None

    def __init__(self):
        """Initialize LuckyRobots"""
        initialize_event_loop()

        if not self._is_websocket_server_running():
            self._start_websocket_server()

        super().__init__("lucky_robots_manager", "", "localhost", self.port)

        app.lucky_robots = self

        self._load_default_params()

    def _is_websocket_server_running(self) -> bool:
        """Check if a WebSocket server is already running.

        Returns:
            bool: True if a WebSocket server is running, False otherwise
        """
        try:
            ws_url = f"ws://{self.host}:{self.port}/nodes"
            ws = create_connection(ws_url, timeout=1)
            ws.close()
            logger.info(f"WebSocket server running on {self.host}:{self.port}")
            return True
        except Exception as e:
            logger.info(f"WebSocket server not running on {self.host}:{self.port}")
            return False

    def _start_websocket_server(self) -> None:
        """Start the WebSocket server in a background thread"""

        def run_server():
            logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
            uvicorn.run(app, host=self.host, port=self.port, log_level="warning")

        server_thread = threading.Thread(target=run_server, daemon=True)
        server_thread.start()

        logger.info(f"Starting WebSocket server on {self.host}:{self.port}")

        # Give the server time to start
        time.sleep(0.5)

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

    async def _setup_async(self):
        """Setup the LuckyRobots core."""

        self.reset_service = await self.create_service(
            Reset, "/reset", self.handle_reset
        )
        self.step_service = await self.create_service(Step, "/step", self.handle_step)

    def start(
        self,
        scene: str = None,
        robot_type: str = None,
        task: str = None,
        binary_path: Optional[str] = None,
    ) -> None:
        """Start the LuckyRobots core

        Args:
            binary_path: Path to the LuckyRobots binary
            send_bytes: Whether to send raw bytes instead of text
        """
        if self._running:
            logger.warning("LuckyRobots is already running")
            return

        directory_to_watch = self._initialize_binary(binary_path)

        Handler.set_lucky_robots(self)

        if not is_luckyworld_running() and "--lr-no-executable" not in sys.argv:
            logger.error("LuckyWorld is not running, starting it now...")
            # run_luckyworld_executable(scene, robot_type, task, directory_to_watch)

        library_dev()

        self._setup_signal_handlers()
        self._setup_directory_watcher(directory_to_watch)

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

    def _setup_directory_watcher(self, binary_path: str) -> str:
        """Set up the directory watcher in a background thread"""
        directory = os.path.join(binary_path, "Saved")
        os.makedirs(directory, exist_ok=True)

        watcher = Watcher(directory)
        watcher_thread = threading.Thread(target=watcher.run, daemon=True)
        watcher_thread.start()

        return directory

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

    def wait_for_world_client(self, timeout=60.0):
        """Wait until a world client is connected.

        Args:
            timeout: Maximum time to wait in seconds

        Returns:
            bool: True if a world client connected within the timeout, False otherwise
        """
        logger.info(f"Waiting for world client to connect (timeout: {timeout}s)")

        start_time = time.time()

        while not self.world_client and time.time() - start_time < timeout:
            time.sleep(0.5)  # Check every half second

        if self.world_client:
            logger.info("World client connected successfully")
            return True
        else:
            logger.warning(f"No world client connected after {timeout} seconds")
            return False

    async def handle_reset(self, request: Reset.Request) -> Reset.Response:
        """Handle the reset request by forwarding to the world client.

        This method is called when a reset service request is received from a node.
        It forwards the request to the world client via WebSocket and returns
        the response.

        Args:
            request: The reset request containing optional seed

        Returns:
            Reset.Response: The response from the world client
        """
        if self.world_client is None:
            logger.error("No world client connection available")
            return Reset.Response(
                success=False,
                message="No world client connection available",
                observation=None,
                info={"error": "no_connection"},
            )

        request_id = f"{uuid.uuid4().hex}"

        shared_loop = get_event_loop()
        response_future = shared_loop.create_future()

        self._pending_resets[request_id] = response_future

        seed = request.seed if hasattr(request, "seed") else None

        message = {"type": "reset", "request_id": request_id, "seed": seed}

        # Send to world client
        try:
            await self.world_client.send_bytes(msgpack.dumps(message))
        except Exception as e:
            logger.error(f"Error sending reset request to world client: {e}")
            if request_id in self._pending_resets:
                del self._pending_resets[request_id]
            return Reset.Response(
                success=False,
                message=f"Error sending reset request: {str(e)}",
                observation=None,
                info={"error": "communication_error"},
            )

        # Await response from world client
        try:
            response_data = await asyncio.wait_for(response_future, timeout=30.0)

            # Process response data into Reset.Response
            success = response_data.get("success", False)
            message = response_data.get("message", "Reset processed")

            observation = ObservationModel(**response_data["observation"])

            # Get any additional info
            info = response_data.get("info", {})
            if not isinstance(info, dict):
                info = {"data": info}

            return Reset.Response(
                success=success, message=message, observation=observation, info=info
            )

        except asyncio.TimeoutError:
            logger.error(f"Reset request {request_id} timed out after 30 seconds")
            if request_id in self._pending_resets:
                del self._pending_resets[request_id]
            return Reset.Response(
                success=False,
                message="Reset request timed out - no response from world client",
                observation=None,
                info={"error": "timeout"},
            )
        except Exception as e:
            logger.error(f"Error processing reset response: {e}")
            if request_id in self._pending_resets:
                del self._pending_resets[request_id]
            return Reset.Response(
                success=False,
                message=f"Error processing reset response: {str(e)}",
                observation=None,
                info={"error": "processing_error"},
            )

    async def _process_reset_response(self, message_data):
        """Process a reset response from the world client.

        This method is called when a reset response is received from the world client.
        It resolves the future for the corresponding request.

        Args:
            message_data: The response data from the world client
        """
        request_id = message_data.get("request_id")

        if not request_id:
            logger.warning("Received reset response without request_id")
            return

        if request_id not in self._pending_resets:
            logger.warning(
                f"Received reset response for unknown request_id: {request_id}"
            )
            return

        # Get the future for this request
        future = self._pending_resets[request_id]

        shared_loop = get_event_loop()

        # Use call_soon_threadsafe to ensure the future is completed in the right context
        shared_loop.call_soon_threadsafe(
            lambda f=future, d=message_data: f.set_result(d) if not f.done() else None
        )

        # Also clean up the pending resets in a thread-safe way
        shared_loop.call_soon_threadsafe(
            lambda p=self._pending_resets, r=request_id: p.pop(r, None)
        )

    async def handle_step(self, request: Step.Request) -> Step.Response:
        """Handle the step request by forwarding to the world client.

        This method is called when a step service request is received from a node.
        It forwards the request to the world client via WebSocket and returns
        the response.

        Args:
            request: The step request containing action data

        Returns:
            Step.Response: The response from the world client
        """
        # Check if world client is connected
        if self.world_client is None:
            logger.error("No world client connection available")
            return Step.Response(
                success=False,
                message="No world client connection available",
                observation=None,
                info={"error": "no_connection"},
            )

        # Generate a unique ID for this request
        request_id = f"{uuid.uuid4().hex}"

        # Create a future to hold the response
        shared_loop = get_event_loop()
        response_future = shared_loop.create_future()

        # Store the future with the request ID
        self._pending_steps[request_id] = response_future

        # Create message for world client
        # Extract pose and twist data if available
        pose = (
            request.action.pose.dict()
            if hasattr(request, "action") and request.action.pose
            else None
        )
        twist = (
            request.action.twist.dict()
            if hasattr(request, "action") and request.action.twist
            else None
        )

        if pose is None and twist is None:
            logger.error("No pose or twist data provided in step request")
            return Step.Response(
                success=False,
                message="No pose or twist data provided in step request",
                observation=None,
                info={"error": "no_data"},
            )

        message = {
            "type": "step",
            "request_id": request_id,
            "pose": pose,
            "twist": twist,
        }

        # Send to world client
        try:
            await self.world_client.send_bytes(msgpack.dumps(message))
        except Exception as e:
            logger.error(f"Error sending step request to world client: {e}")
            if request_id in self._pending_steps:
                del self._pending_steps[request_id]
            return Step.Response(
                success=False,
                message=f"Error sending step request: {str(e)}",
                observation=None,
                info={"error": "communication_error"},
            )

        # Wait for response
        try:
            response_data = await asyncio.wait_for(response_future, timeout=30.0)

            # Process response data into Step.Response
            success = response_data.get("success", False)
            message = response_data.get("message", "Step processed")

            observation = ObservationModel(**response_data["observation"])

            # Get any additional info
            info = response_data.get("info", {})
            if not isinstance(info, dict):
                info = {"data": info}

            return Step.Response(
                success=success, message=message, observation=observation, info=info
            )

        except asyncio.TimeoutError:
            logger.error(f"Step request {request_id} timed out after 30 seconds")
            if request_id in self._pending_steps:
                del self._pending_steps[request_id]
            return Step.Response(
                success=False,
                message="Step request timed out - no response from world client",
                observation=None,
                info={"error": "timeout"},
            )
        except Exception as e:
            logger.error(f"Error processing step response: {e}")
            if request_id in self._pending_steps:
                del self._pending_steps[request_id]
            return Step.Response(
                success=False,
                message=f"Error processing step response: {str(e)}",
                observation=None,
                info={"error": "processing_error"},
            )

    async def _process_step_response(self, message_data):
        request_id = message_data.get("request_id")

        if not request_id:
            logger.warning("Received step response without request_id")
            return

        if request_id not in self._pending_steps:
            logger.warning(
                f"Received step response for unknown request_id: {request_id}"
            )
            return

        # Get the future for this request
        future = self._pending_steps[request_id]

        shared_loop = get_event_loop()

        # Use call_soon_threadsafe to ensure the future is completed in the right context
        shared_loop.call_soon_threadsafe(
            lambda f=future, d=message_data: f.set_result(d) if not f.done() else None
        )

        # Also clean up the pending steps in a thread-safe way
        shared_loop.call_soon_threadsafe(
            lambda p=self._pending_steps, r=request_id: p.pop(r, None)
        )

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

    def _stop_websocket_server(self) -> None:
        """Stop the WebSocket server if it's running"""
        if self._server is not None:
            logger.info("Stopping WebSocket server...")
            # Signal the server to stop
            self._server.should_exit = True

            # Wait for the server thread to exit (with timeout)
            if self._server_thread and self._server_thread.is_alive():
                self._server_thread.join(timeout=2.0)
                if self._server_thread.is_alive():
                    logger.warning(
                        "WebSocket server thread did not terminate gracefully"
                    )
                else:
                    logger.info("WebSocket server stopped")

            # Reset server references
            self._server = None
            self._server_thread = None

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

        # Stop the WebSocket server
        self._stop_websocket_server()

        # Shutdown the event loop
        shutdown_event_loop()

        self._shutdown_event.set()
        logger.info("LuckyRobots shutdown complete")


@app.websocket("/nodes")
async def nodes_endpoint(websocket: WebSocket) -> None:
    """WebSocket endpoint for node communication"""
    await websocket.accept()

    node_name = None

    try:
        # Wait for the first message, which should be NODE_ANNOUNCE
        message = await websocket.receive_bytes()
        message_data = msgpack.unpackb(message)
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
            try:
                message = await websocket.receive_bytes()
                message_data = msgpack.unpackb(message)
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
            except msgpack.UnpackValueError:
                logger.error(f"Received invalid msgpack from {node_name}")
            except Exception as e:
                logger.error(f"Error processing message from {node_name}: {e}")
    except WebSocketDisconnect:
        logger.info(f"Node {node_name} disconnected")


@app.websocket("/world")
async def world_endpoint(websocket: WebSocket) -> None:
    """WebSocket endpoint for world client communication"""
    await websocket.accept()

    # Store the world client connection
    if hasattr(app, "lucky_robots"):
        app.lucky_robots.world_client = websocket
        logger.info("World client connected")

    try:
        # Process messages until disconnection
        while True:
            try:
                message = await websocket.receive_bytes()
                message_data = msgpack.unpackb(message)

                # Process the message based on its type
                if "type" in message_data:
                    if message_data["type"] == "reset_response":
                        await app.lucky_robots._process_reset_response(message_data)
                    elif message_data["type"] == "step_response":
                        await app.lucky_robots._process_step_response(message_data)
                    else:
                        logger.warning(f"Unknown message type: {message_data['type']}")
                else:
                    logger.warning("Received message without type field")
            except msgpack.UnpackValueError:
                logger.error(f"Received invalid msgpack from world client")
            except Exception as e:
                logger.error(f"Error processing message from world client: {e}")
    except WebSocketDisconnect:
        logger.info("World client disconnected")
        if hasattr(app, "lucky_robots"):
            app.lucky_robots.world_client = None
