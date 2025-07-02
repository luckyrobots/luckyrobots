import cv2
import json
import msgpack
import asyncio
import logging
import secrets
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
from ..utils.sim_manager import launch_luckyworld, stop_luckyworld
from ..core.models import ObservationModel
from .node import Node
from ..utils.event_loop import (
    get_event_loop,
    initialize_event_loop,
)
from ..utils.helpers import (
    validate_params,
    get_robot_config,
)

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("luckyrobots")

app = FastAPI()
manager = Manager()


class LuckyRobots(Node):
    """Main LuckyRobots node for managing robot communication and control"""

    def __init__(self, host: str = "localhost", port: int = 3000) -> None:
        self.host = host
        self.port = port
        self.robot_client = None
        self.world_client = None
        self._pending_resets = {}
        self._pending_steps = {}
        self._running = False
        self._nodes: Dict[str, Node] = {}
        self._shutdown_event = threading.Event()

        initialize_event_loop()

        self._start_websocket_server()

        super().__init__("lucky_robots_manager", "", self.host, self.port)
        app.lucky_robots = self

    def _is_websocket_server_running(self) -> bool:
        """Check if the websocket server is already running"""
        try:
            ws_url = f"ws://{self.host}:{self.port}/nodes"
            ws = create_connection(ws_url, timeout=1)
            ws.close()
            return True
        except Exception as e:
            return False

    def _start_websocket_server(self) -> None:
        """Start the websocket server in a separate thread using uvicorn"""

        if self._is_websocket_server_running():
            logger.warning(
                f"WebSocket server already running on {self.host}:{self.port}"
            )
            return

        def run_server():
            logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
            config = uvicorn.Config(
                app, host=self.host, port=self.port, log_level="warning"
            )
            self._server = uvicorn.Server(config)
            self._server.run()

        self._server_thread = threading.Thread(target=run_server, daemon=True)
        self._server_thread.start()

        logger.info(f"Starting WebSocket server on {self.host}:{self.port}")

        # Wait for the server to start
        timeout = 10.0
        start_time = time.perf_counter()

        while time.perf_counter() - start_time < timeout:
            if self._is_websocket_server_running():
                logger.info(f"WebSocket server ready on {self.host}:{self.port}")
                return
            time.sleep(0.1)

        logger.error(f"WebSocket server failed to start within {timeout} seconds")
        raise RuntimeError(
            f"WebSocket server failed to start on {self.host}:{self.port}"
        )

    @staticmethod
    def get_robot_config(robot: str = None) -> dict:
        """Get the configuration for the LuckyRobots node"""
        return get_robot_config(robot)

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

    def _register_cleanup_handlers(self) -> None:
        """Register cleanup handlers for the LuckyRobots node to handle Ctrl+C"""

        def sigint_handler(signum, frame):
            logger.info("Ctrl+C pressed. Shutting down...")
            self.shutdown()

        signal.signal(signal.SIGINT, sigint_handler)

    def start(
        self,
        scene: str,
        robot: str,
        debug: bool = False,
        task: str = None,
        executable_path: str = None,
        observation_type: str = "pixels_agent_pos",
        headless: bool = False,
    ) -> None:
        """Start the LuckyRobots node"""
        if self._running:
            logger.warning("LuckyRobots is already running")
            return

        validate_params(scene, robot, task, observation_type)
        self.process_cameras = "pixels" in observation_type

        success = launch_luckyworld(
            scene=scene,
            robot=robot,
            debug=debug,
            task=task,
            executable_path=executable_path,
            headless=headless,
        )
        if not success:
            logger.error("Failed to launch LuckyWorld")
            self.shutdown()
            raise RuntimeError(
                "Failed to launch LuckyWorld. Look through the log for more information."
            )

        self._register_cleanup_handlers()

        # Start all registered nodes
        failed_nodes = []
        for node in self._nodes.values():
            try:
                node.start()
                logger.info(f"Started node: {node.full_name}")
            except Exception as e:
                logger.error(f"Error starting node {node.full_name}: {e}")
                failed_nodes.append(node.full_name)

        if failed_nodes:
            logger.error(f"Failed to start nodes: {', '.join(failed_nodes)}")
            # Continue anyway - some nodes might be optional

        super().start()

        self._running = True

    def _display_welcome_message(self) -> None:
        """Display the welcome message for the LuckyRobots node in the terminal"""

        # Create the complete message in one go
        stars = "*" * 60

        welcome_lines = [
            stars,
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

        # Add macOS instructions if needed
        if platform.system() == "Darwin":
            welcome_lines.extend(
                [
                    stars,
                    "For macOS users:",
                    "Please be patient. The application may take up to a minute to open on its first launch.",
                    "If the application doesn't appear, please follow these steps:",
                    "1. Open System Settings",
                    "2. Navigate to Privacy & Security",
                    "3. Scroll down and click 'Allow' next to the 'luckyrobots' app",
                    stars,
                ]
            )

        # Add final messages
        welcome_lines.extend(
            [
                "Lucky Robots application started successfully.",
                "To move the robot: Choose a level and tick the HTTP checkbox.",
                "To receive camera feed: Choose a level and tick the Capture checkbox.",
                stars,
                "",  # Empty line at the end
            ]
        )

        # Single print statement - cannot be interrupted!
        print("\n".join(welcome_lines), flush=True)

    def wait_for_world_client(self, timeout: float = 120.0) -> bool:
        """Wait for the world client to connect to the websocket server"""
        start_time = time.perf_counter()

        logger.info(f"Waiting for world client to connect (timeout: {timeout}s)")
        while not self.world_client and time.perf_counter() - start_time < timeout:
            time.sleep(0.5)

        if self.world_client:
            logger.info("World client connected successfully")
            return True
        else:
            logger.error(f"No world client connected after {timeout} seconds")
            self.shutdown()
            raise RuntimeError(
                f"World client connection timeout after {timeout} seconds"
            )

    async def handle_reset(self, request: Reset.Request) -> Reset.Response:
        """Handle the reset request by forwarding to the world client"""
        if self.world_client is None:
            logger.error("No world client connection available")
            self.shutdown()
            raise

        request_id = secrets.token_hex(4)
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

            # Wait for reset animation to finish in Lucky World
            time.sleep(1)

            observation = ObservationModel(**response_data["Observation"])
            if self.process_cameras:
                observation.process_all_cameras()

            return Reset.Response(
                success=True,
                message="Reset request processed",
                request_type=response_data["RequestType"],
                request_id=response_data["RequestID"],
                time_stamp=response_data["TimeStamp"],
                observation=observation,
                info=response_data["Info"],
            )
        except Exception as e:
            self._pending_resets.pop(request_id, None)
            logger.error(f"Error processing reset request: {e}")
            self.shutdown()
            raise

    async def handle_step(self, request: Step.Request) -> Step.Response:
        """Handle the step request by forwarding to the world client"""
        if self.world_client is None:
            logger.error("No world client connection available")
            self.shutdown()
            raise

        request_id = secrets.token_hex(4)
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

            observation = ObservationModel(**response_data["Observation"])
            if self.process_cameras:
                observation.process_all_cameras()

            return Step.Response(
                success=True,
                message="Step request processed",
                request_type=response_data["RequestType"],
                request_id=response_data["RequestID"],
                time_stamp=response_data["TimeStamp"],
                observation=observation,
                info=response_data["Info"],
            )
        except Exception as e:
            self._pending_steps.pop(request_id, None)
            logger.error(f"Error processing step request: {e}")
            self.shutdown()
            raise

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
            try:
                # Stop the uvicorn server
                self._server.should_exit = True

                # Wait for the server thread to terminate
                if (
                    hasattr(self, "_server_thread")
                    and self._server_thread
                    and self._server_thread.is_alive()
                ):
                    self._server_thread.join(timeout=5.0)

                    if self._server_thread.is_alive():
                        logger.warning(
                            "WebSocket server thread did not terminate within timeout"
                        )
                    else:
                        logger.info("WebSocket server thread terminated successfully")

                self._server = None
                self._server_thread = None

            except Exception as e:
                logger.error(f"Error stopping WebSocket server: {e}")
        else:
            logger.info("No WebSocket server instance found")

    def _cleanup_camera_windows(self) -> None:
        """Clean up all OpenCV windows and reset tracking"""
        try:
            # Only cleanup if we're in the main thread to avoid Qt warnings
            if threading.current_thread() == threading.main_thread():
                cv2.destroyAllWindows()
                cv2.waitKey(1)
            else:
                # If not in main thread, just skip OpenCV cleanup
                # The windows will close when the main thread exits anyway
                pass
        except Exception:
            # Ignore any errors during cleanup
            pass

    def shutdown(self) -> None:
        """Shutdown the LuckyRobots node and clean up resources"""
        if not self._running:
            logger.info("LuckyRobots already shut down")
            return

        logger.info("Starting LuckyRobots shutdown sequence")
        self._running = False

        self._cancel_pending_operations()
        self._shutdown_nodes()
        self._stop_luckyworld()
        self._shutdown_transport()
        self._stop_websocket_server()
        self._cleanup_resources()
        self._shutdown_event.set()

        logger.info("LuckyRobots shutdown complete")

        exit(0)

    def _cancel_pending_operations(self) -> None:
        """Cancel all pending reset and step operations"""
        logger.info("Cancelling pending operations")

        # Cancel pending resets
        for _, future in self._pending_resets.items():
            if not future.done():
                future.cancel()
        self._pending_resets.clear()

        # Cancel pending steps
        for _, future in self._pending_steps.items():
            if not future.done():
                future.cancel()
        self._pending_steps.clear()

    def _shutdown_nodes(self) -> None:
        """Shutdown all registered nodes with timeout"""
        if not self._nodes:
            return

        logger.info(f"Shutting down {len(self._nodes)} registered nodes")

        failed_nodes = []
        for node_name, node in self._nodes.items():
            try:
                logger.debug(f"Shutting down node: {node_name}")
                node.shutdown()
                logger.debug(f"Node {node_name} shut down successfully")
            except Exception as e:
                logger.error(f"Error shutting down node {node_name}: {e}")
                failed_nodes.append(node_name)

        if failed_nodes:
            logger.warning(f"Failed to shutdown nodes: {', '.join(failed_nodes)}")
        else:
            logger.info("All nodes shut down successfully")

        self._nodes.clear()

    def _stop_luckyworld(self) -> None:
        """Stop the LuckyWorld executable with error handling"""
        try:
            stop_luckyworld()
        except Exception as e:
            logger.error(f"Error stopping LuckyWorld executable: {e}")
            # Don't raise - continue with shutdown even if LuckyWorld fails to stop

    def _shutdown_transport(self) -> None:
        """Shutdown the transport layer with timeout"""
        try:
            logger.info("Shutting down transport layer...")
            super().shutdown()
            logger.info("Transport layer shut down")
        except Exception as e:
            logger.error(f"Error shutting down transport layer: {e}")

    def _cleanup_resources(self) -> None:
        """Clean up all remaining resources"""

        # Cleanup camera windows
        self._cleanup_camera_windows()

        # Close WebSocket connections
        if hasattr(self, "world_client") and self.world_client:
            try:
                self.world_client.close()
                self.world_client = None
            except Exception as e:
                logger.debug(f"Error closing world client: {e}")

        # Clear any remaining state
        self.robot_client = None
        self.world_client = None

        logger.info("Resource cleanup complete")


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

    lucky_robots = app.lucky_robots
    pending_resets = lucky_robots._pending_resets
    pending_steps = lucky_robots._pending_steps

    try:
        while True:
            try:
                message_bytes = await websocket.receive_bytes()
                message_data = msgpack.unpackb(message_bytes)
                request_type = message_data.get("RequestType")
                request_id = message_data.get("RequestID")
                shared_loop = get_event_loop()

                if request_type == "reset_response":
                    future = pending_resets.get(request_id)
                    shared_loop.call_soon_threadsafe(
                        lambda: future.set_result(message_data)
                        if future is not None and not future.done()
                        else None
                    )
                    shared_loop.call_soon_threadsafe(
                        lambda: pending_resets.pop(request_id, None)
                    )
                elif request_type == "step_response":
                    future = pending_steps.get(request_id)
                    shared_loop.call_soon_threadsafe(
                        lambda: future.set_result(message_data)
                        if future is not None and not future.done()
                        else None
                    )
                    shared_loop.call_soon_threadsafe(
                        lambda: pending_resets.pop(request_id, None)
                        if request_type == "reset_response"
                        else pending_steps.pop(request_id, None)
                    )
                else:
                    logger.warning(f"Unhandled message type: {request_type}")

            except WebSocketDisconnect as e:
                logger.info(f"WebSocket disconnected. Code: {e.code}")
                break
            except Exception as e:
                logger.error(f"Message processing error: {type(e).__name__}: {e}")
                break

    except WebSocketDisconnect:
        pass
    except Exception as e:
        logger.error(f"Critical error in world_endpoint: {type(e).__name__}: {e}")
    finally:
        if hasattr(app, "lucky_robots") and app.lucky_robots.world_client == websocket:
            app.lucky_robots.world_client = None
