import json
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
from typing import Dict, Optional

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

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("luckyrobots")

app = FastAPI()
manager = Manager()


class LuckyRobots(Node):
    host = "localhost"
    port = 3000

    robot_client = None
    world_client = None

    _pending_resets = {}
    _pending_steps = {}

    _nodes: Dict[str, "Node"] = {}
    _running = False
    _shutdown_event = threading.Event()

    def __init__(self, host: str = None, port: int = None):
        initialize_event_loop()

        self.host = host or self.host
        self.port = port or self.port

        if not self._is_websocket_server_running():
            self._start_websocket_server()

        super().__init__("lucky_robots_manager", "", host, port)

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
        """Set the host address for the LuckyRobots node"""
        LuckyRobots.host = ip_address
        set_param("core/host", ip_address)

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
        scene: str = None,
        task: str = None,
        robot_type: str = None,
        render_mode: str = None,
        binary_path: Optional[str] = None,
    ) -> None:
        """Start the LuckyRobots node"""
        if self._running:
            logger.warning("LuckyRobots is already running")
            return

        if (
            not is_luckyworld_running()
            and "--lr-no-executable" not in sys.argv
            and render_mode is not None
        ):
            logger.error("LuckyWorld is not running, starting it now...")
            # run_luckyworld_executable(scene, task, robot_type, binary_path)

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

    def wait_for_world_client(self, timeout: float = 60.0) -> bool:
        """Wait for the world client to connect to the websocket server"""
        start_time = time.time()

        while not self.world_client and time.time() - start_time < timeout:
            time.sleep(0.5)  # Check every half second

        if self.world_client:
            logger.info("World client connected successfully")
            return True
        else:
            self.shutdown()
            raise Exception(f"No world client connected after {timeout} seconds")

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
            self.shutdown()
            raise Exception("No world client connection available")

        id = f"{uuid.uuid4().hex}"

        shared_loop = get_event_loop()
        response_future = shared_loop.create_future()

        self._pending_resets[id] = response_future

        seed = request.seed if hasattr(request, "seed") else None

        request_data = {"type": "reset", "id": id, "seed": seed}

        # Send to world client
        try:
            await self.world_client.send_text(json.dumps(request_data))
        except Exception as e:
            if id in self._pending_resets:
                del self._pending_resets[id]
            self.shutdown()
            raise Exception(f"Error sending reset request to world client: {e}")

        # Await response from world client
        try:
            response_data = await asyncio.wait_for(response_future, timeout=30.0)

            # Process response data into Reset.Response
            success = True
            message = "Reset request processed"
            type = response_data["type"]
            id = response_data["id"]
            time_stamp = response_data["timeStamp"]

            observation = ObservationModel(**response_data["observation"])

            # Get any additional info
            info = response_data.get("info", {})
            if not isinstance(info, dict):
                info = {"data": info}

            return Reset.Response(
                success=success,
                message=message,
                type=type,
                id=id,
                time_stamp=time_stamp,
                observation=observation,
                info=info,
            )

        except asyncio.TimeoutError:
            self.shutdown()
            raise Exception(f"Reset request {id} timed out after 30 seconds")

        except Exception as e:
            self.shutdown()
            raise Exception(f"Error processing reset response: {e}")

    async def _process_reset_response(self, message_data: dict) -> None:
        """Process a reset response from the world client"""
        id = message_data.get("id")

        if not id:
            self.shutdown()
            raise Exception("Received reset response without id")

        if id not in self._pending_resets:
            self.shutdown()
            raise Exception(f"Received reset response for unknown id: {id}")

        # Get the future for this request
        future = self._pending_resets[id]

        shared_loop = get_event_loop()

        shared_loop.call_soon_threadsafe(
            lambda f=future, d=message_data: f.set_result(d) if not f.done() else None
        )

        shared_loop.call_soon_threadsafe(
            lambda p=self._pending_resets, r=id: p.pop(r, None)
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
            self.shutdown()
            raise Exception("No world client connection available")

        # Generate a unique ID for this request
        id = f"{uuid.uuid4().hex}"

        shared_loop = get_event_loop()
        response_future = shared_loop.create_future()

        self._pending_steps[id] = response_future

        joint_positions = (
            request.action.joint_positions
            if hasattr(request.action, "joint_positions")
            else None
        )

        joint_velocities = (
            request.action.joint_velocities
            if hasattr(request.action, "joint_velocities")
            else None
        )

        if joint_positions is None and joint_velocities is None:
            logger.error(
                "No joint positions or velocities data provided in step request"
            )
            return Step.Response(
                success=False,
                message="No joint positions or velocities data provided in step request",
                observation=None,
                info={"error": "no_data"},
            )

        request_data = {
            "type": "step",
            "id": id,
            "joint_positions": joint_positions,
            "joint_velocities": joint_velocities,
        }

        # Send to world client
        try:
            await self.world_client.send_text(json.dumps(request_data))
        except Exception as e:
            self.shutdown()
            raise Exception(f"Error sending step request to world client: {e}")

        # Wait for response
        try:
            response_data = await asyncio.wait_for(response_future, timeout=30.0)

            success = True
            message = "Step request processed"
            type = response_data["type"]
            id = response_data["id"]
            time_stamp = response_data["timeStamp"]

            observation = ObservationModel(**response_data["observation"])

            info = response_data.get("info", {})
            if not isinstance(info, dict):
                info = {"data": info}

            return Step.Response(
                success=success,
                message=message,
                type=type,
                id=id,
                time_stamp=time_stamp,
                observation=observation,
                info=info,
            )

        except asyncio.TimeoutError:
            self.shutdown()
            raise Exception(f"Step request {id} timed out after 30 seconds")

        except Exception as e:
            self.shutdown()
            raise Exception(f"Error processing step response: {e}")

    async def _process_step_response(self, message_data: dict) -> None:
        """Process a step response from the world client"""
        id = message_data.get("id")

        if not id:
            self.shutdown()
            raise Exception("Received step response without id")

        if id not in self._pending_steps:
            self.shutdown()
            raise Exception(f"Received step response for unknown id: {id}")

        future = self._pending_steps[id]

        shared_loop = get_event_loop()

        # Use call_soon_threadsafe to ensure the future is completed in the right context
        shared_loop.call_soon_threadsafe(
            lambda f=future, d=message_data: f.set_result(d) if not f.done() else None
        )

        # Also clean up the pending steps in a thread-safe way
        shared_loop.call_soon_threadsafe(
            lambda p=self._pending_steps, r=id: p.pop(r, None)
        )

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

        self._stop_websocket_server()

        shutdown_event_loop()

        self._shutdown_event.set()
        logger.info("LuckyRobots shutdown complete")


@app.websocket("/nodes")
async def nodes_endpoint(websocket: WebSocket) -> None:
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
    await websocket.accept()

    if hasattr(app, "lucky_robots"):
        app.lucky_robots.world_client = websocket
        logger.info("World client connected")

    try:
        # Process messages until disconnection
        while True:
            try:
                message_json = await websocket.receive_json()

                if "type" in message_json:
                    if message_json["type"] == "reset_response":
                        await app.lucky_robots._process_reset_response(message_json)
                    elif message_json["type"] == "step_response":
                        await app.lucky_robots._process_step_response(message_json)
                    else:
                        logger.warning(f"Unknown message type: {message_json['type']}")
                else:
                    logger.warning("Received message without type field")
            except json.JSONDecodeError:
                logger.error(f"Received invalid JSON from world client")
            except Exception as e:
                logger.error(f"Error processing message from world client: {e}")
    except WebSocketDisconnect:
        logger.info("World client disconnected")
        if hasattr(app, "lucky_robots"):
            app.lucky_robots.world_client = None
