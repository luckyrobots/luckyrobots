import cv2
import json
import msgpack
import asyncio
import logging
import os
import uuid
import platform
import signal
import threading
import time

from typing import Dict

import uvicorn
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from websocket import create_connection

from .manager import Manager
from ..message.transporter import MessageType, TransportMessage
from ..message.srv.types import Reset, Step
from ..runtime.run_executable import is_luckyworld_running, run_luckyworld_executable
from ..utils.library_dev import library_dev
from ..core.models import ObservationModel
from .node import Node
from .parameters import load_from_file, set_param
from ..utils.event_loop import (
    get_event_loop,
    initialize_event_loop,
    shutdown_event_loop,
)
from ..utils.helpers import validate_params, get_robot_config, process_images

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("luckyrobots")

# FastAPI app and manager instances
app = FastAPI()
manager = Manager()


class LuckyRobots(Node):
    """Main LuckyRobots node for managing robot communication and control"""

    host = "localhost"
    port = 3000

    robot_client = None
    world_client = None

    _pending_resets = {}
    _pending_steps = {}

    _running = False
    _nodes: Dict[str, "Node"] = {}
    _shutdown_event = threading.Event()

    def __init__(self, host: str = None, port: int = None):
        initialize_event_loop()

        self.host = host or self.host
        self.port = port or self.port

        # Initialize clients and state
        self.robot_client = None
        self.world_client = None
        self._pending_resets = {}
        self._pending_steps = {}
        self._running = False
        self._nodes: Dict[str, Node] = {}
        self._shutdown_event = threading.Event()

        if not self._is_websocket_server_running():
            self._start_websocket_server()

        super().__init__("lucky_robots_manager", "", self.host, self.port)
        app.lucky_robots = self

        self._load_default_params()

    def _is_websocket_server_running(self) -> bool:
        """Check if the websocket server is already running"""
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
        """Start the websocket server in a separate thread using uvicorn"""

        def run_server():
            logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
            uvicorn.run(app, host=self.host, port=self.port, log_level="warning")

        server_thread = threading.Thread(target=run_server, daemon=True)
        server_thread.start()

        logger.info(f"Starting WebSocket server on {self.host}:{self.port}")

        # Give the server time to start
        time.sleep(0.5)

    def _load_default_params(self) -> None:
        """Load the default parameters for the LuckyRobots node"""
        set_param("core/host", self.host)
        set_param("core/port", self.port)

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
        """Set the host address for the LuckyRobots node"""
        LuckyRobots.host = ip_address
        set_param("core/host", ip_address)

    def get_robot_config(self, robot: str = None) -> dict:
        """Get the configuration for the LuckyRobots node"""
        return get_robot_config(robot)
    
    @staticmethod
    def process_images(observation_cameras: list) -> dict:
        """Process the images from the observation cameras"""
        return process_images(observation_cameras)

    def register_node(self, node: Node) -> None:
        """Register a node with the LuckyRobots node"""
        self._nodes[node.full_name] = node
        logger.info(f"Registered node: {node.full_name}")

    async def _setup_async(self):
        """Setup the LuckyRobots node asynchronously"""
        self.reset_service = await self.create_service(
            Reset, "/reset", self.handle_reset
        )
        self.step_service = await self.create_service(Step, "/step", self.handle_step)

    def start(
        self,
        scene: str = "kitchen",
        task: str = "pickandplace",
        robot: str = "so100",
        render_mode: str = None,
        binary_path: str = None,
    ) -> None:
        """Start the LuckyRobots node"""
        if self._running:
            logger.warning("LuckyRobots is already running")
            return

        validate_params(scene, task, robot)

        # if (
        #     not is_luckyworld_running()
        #     and "--lr-no-executable" not in sys.argv
        #     and render_mode is not None
        # ):
        #     logger.error("LuckyWorld is not running, starting it now...")
        #     run_luckyworld_executable(scene, task, robot, binary_path)

        library_dev()

        self._setup_signal_handlers()

        # Start all registered nodes
        for node in self._nodes.values():
            try:
                node.start()
            except Exception as e:
                logger.error(f"Error starting node {node.full_name}: {e}")

        # Start the luckyrobots node
        super().start()

        self._running = True

    def _setup_signal_handlers(self) -> None:
        """Setup signal handlers for the LuckyRobots node to handle Ctrl+C"""

        def sigint_handler(signum, frame):
            print("\nCtrl+C pressed. Shutting down...")
            self.shutdown()

        signal.signal(signal.SIGINT, sigint_handler)

    def _display_welcome_message(self) -> None:
        """Display the welcome message for the LuckyRobots node in the terminal"""
        welcome_art = [
            "*" * 60,
            "                                                                                ",
            "                                                                                ",
            "▄▄▌  ▄• ▄▌ ▄▄· ▄ •▄  ▄· ▄▌▄▄▄        ▄▄▄▄·       ▄▄▄▄▄.▄▄ · ",
            "██•  █▪██▌▐█ ▌▪█▌▄▌▪▐█▪██▌▀▄ █·▪     ▐█ ▀█▪▪     •██  ▐█ ▀. ",
            "██▪  █▌▐█▌██ ▄▄▐▀▀▄·▐█▌▐█▪▐▀▀▄  ▄█▀▄ ▐█▀▀█▄ ▄█▀▄  ▐█.▪▄▀▀▀█▄",
            "▐█▌▐▌▐█▄█▌▐███▌▐█.█▌ ▐█▀·.▐█•█▌▐█▌.▐▌██▄▪▐█▐█▌.▐▌ ▐█▌·▐█▄▪▐█",
            ".▀▀▀  ▀▀▀ ·▀▀▀ ·▀  ▀  ▀ • .▀  ▀ ▀█▄▀▪·▀▀▀▀  ▀█▄▀▪ ▀▀▀  ▀▀▀▀ ",
            "                                                                                ",
            "                                                                                ",
        ]

        for line in welcome_art:
            print(line)

        if platform.system() == "Darwin":
            mac_instructions = [
                "*" * 60,
                "For macOS users:",
                "Please be patient. The application may take up to a minute to open on its first launch.",
                "If the application doesn't appear, please follow these steps:",
                "1. Open System Settings",
                "2. Navigate to Privacy & Security",
                "3. Scroll down and click 'Allow' next to the 'luckyrobots' app",
                "*" * 60,
            ]
            for line in mac_instructions:
                print(line)

        final_messages = [
            "Lucky Robots application started successfully.",
            "To move the robot: Choose a level and tick the HTTP checkbox.",
            "To receive camera feed: Choose a level and tick the Capture checkbox.",
            "*" * 60,
        ]
        for line in final_messages:
            print(line)

    def wait_for_world_client(self, timeout: float = 60.0) -> bool:
        """Wait for the world client to connect to the websocket server"""
        start_time = time.time()

        logger.info(f"Waiting for world client to connect for {timeout} seconds")
        while not self.world_client and time.time() - start_time < timeout:
            time.sleep(0.5)

        if self.world_client:
            logger.info("World client connected successfully")
            return True
        else:
            logger.error("No world client connected after 60 seconds")
            self.shutdown()
            raise

    async def handle_reset(self, request: Reset.Request) -> Reset.Response:
        """Handle the reset request by forwarding to the world client"""
        if self.world_client is None:
            logger.error("No world client connection available")
            self.shutdown()
            raise

        request_id = uuid.uuid4().hex
        shared_loop = get_event_loop()
        response_future = shared_loop.create_future()
        self._pending_resets[request_id] = response_future

        seed = getattr(request, "seed", None)
        options = getattr(request, "options", None)
        request_data = {
            "request_type": "reset",
            "request_id": request_id,
            "seed": seed,
            "options": options,
        }

        try:
            await self.world_client.send_text(json.dumps(request_data))
            response_data = await asyncio.wait_for(response_future, timeout=30.0)

            return Reset.Response(
                success=True,
                message="Reset request processed",
                request_type=response_data["RequestType"],
                request_id=response_data["RequestID"],
                time_stamp=response_data["TimeStamp"],
                observation=ObservationModel(**response_data["Observation"]),
                info=response_data["Info"],
            )
        except Exception as e:
            self._pending_resets.pop(request_id, None)
            logger.error(f"Error processing reset request: {e}")
            self.shutdown()
            raise

    async def _process_reset_response(self, message_json: dict) -> None:
        """Process a reset response from the world client"""
        request_id = message_json.get("RequestID")

        if not request_id:
            logger.error(f"Invalid reset response for id: {request_id}")
            self.shutdown()
            raise

        future = self._pending_resets[request_id]
        shared_loop = get_event_loop()

        shared_loop.call_soon_threadsafe(
            lambda: future.set_result(message_json) if not future.done() else None
        )
        shared_loop.call_soon_threadsafe(lambda: self._pending_resets.pop(request_id, None))

    async def handle_step(self, request: Step.Request) -> Step.Response:
        """Handle the step request by forwarding to the world client"""
        if self.world_client is None:   
            logger.error("No world client connection available")
            self.shutdown()
            raise

        request_id = uuid.uuid4().hex
        shared_loop = get_event_loop()
        response_future = shared_loop.create_future()
        self._pending_steps[request_id] = response_future

        self._pending_steps[request_id] = response_future

        request_data = {
            "request_type": "step",
            "request_id": request_id,
            "actuator_values": request.actuator_values,
        }

        try:
            await self.world_client.send_text(json.dumps(request_data))
            response_data = await asyncio.wait_for(response_future, timeout=30.0)

            return Step.Response(
                success=True,
                message="Step request processed",
                request_type=response_data["RequestType"],
                request_id=response_data["RequestID"],
                time_stamp=response_data["TimeStamp"],
                observation=ObservationModel(**response_data["Observation"]),
                info=response_data["Info"],
            )
        except Exception as e:
            self._pending_steps.pop(request_id, None)
            logger.error(f"Error processing step request: {e}")
            self.shutdown()
            raise

    async def _process_step_response(self, message_json: dict) -> None:
        """Process a step response from the world client"""
        request_id = message_json.get("RequestID")

        if not request_id:
            logger.error(f"Invalid step response for id: {request_id}")
            self.shutdown()
            raise

        future = self._pending_steps[request_id]
        shared_loop = get_event_loop()

        shared_loop.call_soon_threadsafe(
            lambda: future.set_result(message_json) if not future.done() else None
        )
        shared_loop.call_soon_threadsafe(lambda: self._pending_steps.pop(request_id, None))

    def spin(self) -> None:
        """Spin the LuckyRobots node to keep it running"""
        if not self._running:
            logger.warning("LuckyRobots is not running")
            return

        self._display_welcome_message()
        logger.info("LuckyRobots spinning")

        try:
            self._shutdown_event.wait()
        except KeyboardInterrupt:
            logger.info("Keyboard interrupt received. Shutting down...")
            self.shutdown()

        logger.info("LuckyRobots stopped spinning")

    def _stop_websocket_server(self) -> None:
        """Stop the WebSocket server if it's running"""
        if hasattr(self, "_server") and self._server is not None:
            logger.info("Stopping WebSocket server...")
            self._server.should_exit = True

            if (
                hasattr(self, "_server_thread")
                and self._server_thread
                and self._server_thread.is_alive()
            ):
                self._server_thread.join(timeout=2.0)
                if self._server_thread.is_alive():
                    logger.warning(
                        "WebSocket server thread did not terminate gracefully"
                    )
                else:
                    logger.info("WebSocket server stopped")

            self._server = None
            self._server_thread = None

    def _cleanup_camera_windows(self) -> None:
        """Clean up all OpenCV windows and reset tracking"""
        cv2.destroyAllWindows()
        cv2.waitKey(1)

    def shutdown(self) -> None:
        """Shutdown the LuckyRobots node and clean up resources"""
        if not self._running:
            return

        self._running = False

        # Shutdown all nodes
        for node in self._nodes.values():
            try:
                node.shutdown()
            except Exception as e:
                logger.error(f"Error shutting down node {node.full_name}: {e}")

        super().shutdown()
        self._cleanup_camera_windows()
        self._stop_websocket_server()
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

        # Message processing loop
        while True:
            try:
                message = await websocket.receive_bytes()
                message_data = msgpack.unpackb(message)
                message = TransportMessage(**message_data)

                # Process message based on type
                handlers = {
                    MessageType.SUBSCRIBE: lambda: manager.subscribe(
                        node_name, message.topic_or_service
                    ),
                    MessageType.UNSUBSCRIBE: lambda: manager.unsubscribe(
                        node_name, message.topic_or_service
                    ),
                    MessageType.SERVICE_REGISTER: lambda: manager.register_service(
                        node_name, message.topic_or_service
                    ),
                    MessageType.SERVICE_UNREGISTER: lambda: manager.unregister_service(
                        node_name, message.topic_or_service
                    ),
                    MessageType.NODE_SHUTDOWN: lambda: None,  # Will break the loop
                }

                if message.msg_type in handlers:
                    if message.msg_type == MessageType.NODE_SHUTDOWN:
                        logger.info(f"Node {node_name} shutting down")
                        break
                    await handlers[message.msg_type]()
                else:
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

    if hasattr(app, "lucky_robots"):
        app.lucky_robots.world_client = websocket
        logger.info("World client connected")

    try:
        while True:
            try:
                message_json = await websocket.receive_json()

                # Handle service responses
                request_type = message_json.get("RequestType")
                if request_type == "reset_response":
                    await app.lucky_robots._process_reset_response(message_json)
                elif request_type == "step_response":
                    await app.lucky_robots._process_step_response(message_json)
                elif request_type:
                    logger.warning(f"Unknown message type: {request_type}")
                else:
                    logger.debug("Received message without type field")

            except json.JSONDecodeError:
                logger.error("Received invalid JSON from world client")
            except Exception as e:
                logger.error(f"Error processing message from world client: {e}")
                app.lucky_robots.shutdown()
    except WebSocketDisconnect:
        logger.info("World client disconnected")
        if hasattr(app, "lucky_robots"):
            app.lucky_robots.world_client = None
