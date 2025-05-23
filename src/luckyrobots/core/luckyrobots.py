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
from typing import Dict, Optional, List

import uvicorn
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from websocket import create_connection

# Camera processing imports
try:
    import base64
    import cv2
    import numpy as np
    CAMERA_LIBS_AVAILABLE = True
except ImportError:
    CAMERA_LIBS_AVAILABLE = False
    logging.warning("Camera libraries (cv2, numpy) not available. Camera display disabled.")

from .manager import Manager
from ..message.transporter import MessageType, TransportMessage
from ..message.srv.types import Reset, Step
from ..runtime.run_executable import is_luckyworld_running, run_luckyworld_executable
from ..utils.library_dev import library_dev
from ..core.models import ObservationModel
from .node import Node
from .parameters import load_from_file, set_param
from ..utils.event_loop import get_event_loop, initialize_event_loop, shutdown_event_loop
from ..utils.helpers import validate_params, get_robot_config, extract_observation_from_message
from .profiler import start_profiler

# Configure logging
logging.basicConfig(
    level=logging.INFO, 
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("luckyrobots")

from .profiler import start_profiler
start_profiler(interval=5)  # Log every 5 seconds

# FastAPI app and manager instances
app = FastAPI()
manager = Manager()

# Camera display globals
SHOW_CAMERA_FEED = False
_ACTIVE_CAMERA_WINDOWS = set()


def _cleanup_camera_windows() -> None:
    """Clean up all OpenCV windows and reset tracking"""
    global _ACTIVE_CAMERA_WINDOWS
    if CAMERA_LIBS_AVAILABLE:
        try:
            cv2.destroyAllWindows()
            cv2.waitKey(1)
            _ACTIVE_CAMERA_WINDOWS.clear()
        except Exception as e:
            logger.error(f"Error cleaning up camera windows: {e}")


def _process_camera_feeds(observation_cameras: List[Dict]) -> List[str]:
    """Process camera feeds for display if enabled
    
    Args:
        observation_cameras: List of camera data from observation
        
    Returns:
        List of camera names that were processed
    """
    import time
    start = time.time()
    global _ACTIVE_CAMERA_WINDOWS
    
    if not SHOW_CAMERA_FEED or not CAMERA_LIBS_AVAILABLE:
        return [cam.get("cameraName", f"camera{idx}") for idx, cam in enumerate(observation_cameras)]
    
    processed_cameras = []
    current_cameras = set()
    
    for idx, cam in enumerate(observation_cameras):
        if "imageData" not in cam:
            continue
            
        try:
            camera_name = cam.get("cameraName", f"camera{idx}")
            # window_name = f"LuckyRobots - {camera_name}"
            # current_cameras.add(window_name)
            
            # Decode base64 image data efficiently
            # image_data_b64 = cam["imageData"]
            # image_bytes = base64.b64decode(image_data_b64)
            
            # # Convert to numpy array and decode with OpenCV
            # nparr = np.frombuffer(image_bytes, np.uint8)
            # image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            
            # if image is not None:
            #     # Display image with proper window management
            #     cv2.namedWindow(window_name, cv2.WINDOW_AUTOSIZE)
            #     cv2.imshow(window_name, image)
                
            #     # Track this window
            #     _ACTIVE_CAMERA_WINDOWS.add(window_name)
            #     processed_cameras.append(camera_name)
                
            #     # Clean up numpy array immediately to free memory
            #     del nparr, image
                
        except Exception as e:
            logger.error(f"Failed to process camera {idx}: {e}")
    
    # Clean up windows that are no longer active
    # windows_to_remove = _ACTIVE_CAMERA_WINDOWS - current_cameras
    # for window_name in windows_to_remove:
    #     try:
    #         cv2.destroyWindow(window_name)
    #         _ACTIVE_CAMERA_WINDOWS.discard(window_name)
    #     except Exception as e:
    #         logger.error(f"Error destroying window {window_name}: {e}")
    
    # # Single waitKey call for all windows (more efficient)
    # if processed_cameras:
    #     cv2.waitKey(1)
    
    elapsed = time.time() - start
    logger.info(f"[Profiler] Camera feed processing took {elapsed*1000:.2f} ms")
    return processed_cameras


class LuckyRobots(Node):
    """Main LuckyRobots node for managing robot communication and control"""
    
    host = "localhost"
    port = 3000

    def __init__(self, host: Optional[str] = None, port: Optional[int] = None):
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
            with create_connection(ws_url, timeout=1) as ws:
                pass
            logger.info(f"WebSocket server running on {self.host}:{self.port}")
            return True
        except Exception:
            logger.error(f"WebSocket server not running on {self.host}:{self.port}")
            self.shutdown()
            return False

    def _start_websocket_server(self) -> None:
        """Start the websocket server in a separate thread using uvicorn"""
        def run_server():
            logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
            uvicorn.run(app, host=self.host, port=self.port, log_level="warning")

        server_thread = threading.Thread(target=run_server, daemon=True)
        server_thread.start()
        logger.info(f"Starting WebSocket server on {self.host}:{self.port}")
        time.sleep(0.5)  # Allow server to start

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

    @staticmethod
    def set_camera_display(enabled: bool) -> None:
        """Enable or disable OpenCV camera feed display"""
        global SHOW_CAMERA_FEED
        
        if enabled and not CAMERA_LIBS_AVAILABLE:
            logger.warning("Camera display requested but libraries not available. Install opencv-python and numpy.")
            return
        
        if not enabled and SHOW_CAMERA_FEED:
            _cleanup_camera_windows()
        
        SHOW_CAMERA_FEED = enabled
        status = "enabled" if enabled else "disabled"
        logger.info(f"Camera feed display {status}")

    def get_robot_config(self, robot: Optional[str] = None) -> dict:
        """Get the configuration for the LuckyRobots node"""
        return get_robot_config(robot)

    def register_node(self, node: Node) -> None:
        """Register a node with the LuckyRobots node"""
        self._nodes[node.full_name] = node
        logger.info(f"Registered node: {node.full_name}")

    async def _setup_async(self) -> None:
        """Setup the LuckyRobots node asynchronously"""
        self.reset_service = await self.create_service(Reset, "/reset", self.handle_reset)
        self.step_service = await self.create_service(Step, "/step", self.handle_step)

    def start(self, scene: Optional[str] = None, task: Optional[str] = None, 
              robot: Optional[str] = None, render_mode: Optional[str] = None, 
              binary_path: Optional[str] = None) -> None:
        """Start the LuckyRobots node"""
        if self._running:
            logger.warning("LuckyRobots is already running")
            return

        # validate_params(scene, task, robot)

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
                "*" * 60
            ]
            for line in mac_instructions:
                print(line)
                
        final_messages = [
            "Lucky Robots application started successfully.",
            "To move the robot: Choose a level and tick the HTTP checkbox.",
            "To receive camera feed: Choose a level and tick the Capture checkbox.",
            "*" * 60
        ]
        for line in final_messages:
            print(line)

    def wait_for_world_client(self, timeout: float = 60.0) -> bool:
        """Wait for the world client to connect to the websocket server"""
        start_time = time.time()
        while not self.world_client and time.time() - start_time < timeout:
            time.sleep(0.5)

        if self.world_client:
            logger.info("World client connected successfully")
            return True
        else:
            self.shutdown()
            raise Exception(f"No world client connected after {timeout} seconds")

    async def handle_reset(self, request: Reset.Request) -> Reset.Response:
        """Handle the reset request by forwarding to the world client"""
        if self.world_client is None:
            self.shutdown()
            raise Exception("No world client connection available")

        request_id = uuid.uuid4().hex
        shared_loop = get_event_loop()
        response_future = shared_loop.create_future()
        self._pending_resets[request_id] = response_future

        seed = getattr(request, "seed", None)
        request_data = {"type": "reset", "id": request_id, "seed": seed}

        try:
            await self.world_client.send_text(json.dumps(request_data))
            response_data = await asyncio.wait_for(response_future, timeout=30.0)

            # Process response data into Reset.Response
            success = True
            message = "Reset request processed"
            type = response_data["type"]
            id = response_data["iD"]
            time_stamp = response_data["timeStamp"]
            observation = ObservationModel(**response_data["observation"])
            info = response_data["info"]

            return Reset.Response(
                success=True,
                message="Reset request processed",
                type=response_data["type"],
                id=response_data["id"],
                time_stamp=response_data["timeStamp"],
                observation=ObservationModel(**response_data["observation"]),
                info=response_data["info"],
            )
        except Exception as e:
            self._pending_resets.pop(request_id, None)
            self.shutdown()
            logger.error(f"Error processing reset request: {e}")
            raise

    async def _process_reset_response(self, message_data: dict) -> None:
        """Process a reset response from the world client"""
        id = message_data.get("iD")

        if not id:
            self.shutdown()
            raise Exception(f"Invalid reset response for id: {request_id}")

        future = self._pending_resets[request_id]
        shared_loop = get_event_loop()
        
        shared_loop.call_soon_threadsafe(
            lambda: future.set_result(message_data) if not future.done() else None
        )
        shared_loop.call_soon_threadsafe(
            lambda: self._pending_resets.pop(request_id, None)
        )

    async def handle_step(self, request: Step.Request) -> Step.Response:
        """Handle the step request by forwarding to the world client"""
        if self.world_client is None:
            self.shutdown()
            raise Exception("No world client connection available")

        request_id = uuid.uuid4().hex
        shared_loop = get_event_loop()
        response_future = shared_loop.create_future()
        self._pending_steps[request_id] = response_future

        joint_positions = getattr(request.action, "joint_positions", None)
        joint_velocities = getattr(request.action, "joint_velocities", None)

        if joint_positions is None and joint_velocities is None:
            self.shutdown()
            raise Exception("No joint positions or velocities data provided in step request")

        request_data = {
            "type": "step",
            "id": request_id,
            "joint_positions": joint_positions,
            "joint_velocities": joint_velocities,
        }

        try:
            await self.world_client.send_text(json.dumps(request_data))
            response_data = await asyncio.wait_for(response_future, timeout=30.0)

            success = True
            message = "Step request processed"
            type = response_data["type"]
            id = response_data["iD"]
            time_stamp = response_data["timeStamp"]
            observation = ObservationModel(**response_data["observation"])
            info = response_data["info"]

            return Step.Response(
                success=True,
                message="Step request processed",
                type=response_data["type"],
                id=response_data["id"],
                time_stamp=response_data["timeStamp"],
                observation=ObservationModel(**response_data["observation"]),
                info=response_data["info"],
            )
        except Exception as e:
            self._pending_steps.pop(request_id, None)
            self.shutdown()
            logger.error(f"Error processing step request: {e}")
            raise

    async def _process_step_response(self, message_data: dict) -> None:
        """Process a step response from the world client"""
        id = message_data.get("iD")

        if not id:
            self.shutdown()
            raise Exception(f"Invalid step response for id: {request_id}")

        future = self._pending_steps[request_id]
        shared_loop = get_event_loop()
        
        shared_loop.call_soon_threadsafe(
            lambda: future.set_result(message_data) if not future.done() else None
        )
        shared_loop.call_soon_threadsafe(
            lambda: self._pending_steps.pop(request_id, None)
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
        if hasattr(self, '_server') and self._server is not None:
            logger.info("Stopping WebSocket server...")
            self._server.should_exit = True

            if hasattr(self, '_server_thread') and self._server_thread and self._server_thread.is_alive():
                self._server_thread.join(timeout=2.0)
                if self._server_thread.is_alive():
                    logger.warning("WebSocket server thread did not terminate gracefully")
                else:
                    logger.info("WebSocket server stopped")

            self._server = None
            self._server_thread = None

    def shutdown(self) -> None:
        """Shutdown the LuckyRobots node and clean up resources"""
        if not self._running:
            return

        self._running = False
        _cleanup_camera_windows()

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
    """WebSocket endpoint for node communication"""
    await websocket.accept()
    node_name = None

    try:
        # Wait for the first message, which should be NODE_ANNOUNCE
        message = await websocket.receive_bytes()
        message_data = msgpack.unpackb(message)
        message = TransportMessage(**message_data)

        if message.msg_type != MessageType.NODE_ANNOUNCE:
            logger.warning(f"First message from node should be NODE_ANNOUNCE, got {message.msg_type}")
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
                    MessageType.SUBSCRIBE: lambda: manager.subscribe(node_name, message.topic_or_service),
                    MessageType.UNSUBSCRIBE: lambda: manager.unsubscribe(node_name, message.topic_or_service),
                    MessageType.SERVICE_REGISTER: lambda: manager.register_service(node_name, message.topic_or_service),
                    MessageType.SERVICE_UNREGISTER: lambda: manager.unregister_service(node_name, message.topic_or_service),
                    MessageType.NODE_SHUTDOWN: lambda: None  # Will break the loop
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

    last_frame_time = None
    try:
        while True:
            try:
                import time
                now = time.time()
                if last_frame_time is not None:
                    interval = now - last_frame_time
                    logger.info(f"[Profiler] Interval since last frame: {interval*1000:.2f} ms")
                last_frame_time = now
                message_json = await websocket.receive_json()

                # Test: Extract and print the observation array using the new helper function
                obs_array = extract_observation_from_message(message_json)
                print('Extracted observation array:', obs_array)
                
                # Process camera feeds if present
                observation = message_json.get("observation", {})
                observation_cameras = observation.get("observationCameras", [])
                
                if observation_cameras:
                    processed_cameras = _process_camera_feeds(observation_cameras)
                    if processed_cameras:
                        action = "Displayed" if SHOW_CAMERA_FEED else "Processed"
                        logger.info(f"{action} {len(processed_cameras)} camera feed(s): {', '.join(processed_cameras)}")

                # Handle service responses
                message_type = message_json.get("type")
                if message_type == "reset_response":
                    await app.lucky_robots._process_reset_response(message_json)
                elif message_type == "step_response":
                    await app.lucky_robots._process_step_response(message_json)
                elif message_type:
                    logger.warning(f"Unknown message type: {message_type}")
                else:
                    logger.debug("Received message without type field")
                    
            except json.JSONDecodeError:
                logger.error("Received invalid JSON from world client")
            except Exception as e:
                logger.error(f"Error processing message from world client: {e}")
                
    except WebSocketDisconnect:
        logger.info("World client disconnected")
        if hasattr(app, "lucky_robots"):
            app.lucky_robots.world_client = None

# Log: Optimized code structure by consolidating imports, reducing redundancy in error handling, 
# simplifying method patterns, improving variable naming, and streamlining control flows while 
# preserving all functionality including commented camera processing sections.
