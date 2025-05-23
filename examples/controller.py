import time
import asyncio
import logging
import threading
import argparse
from collections import deque
from luckyrobots import (
    Node,
    LuckyRobots,
    Step,
    Reset,
    ActionModel,
    run_coroutine,
)

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("controller")


class Controller(Node):
    def __init__(
        self,
        name: str = "controller",
        namespace: str = "",
        host: str = None,
        port: int = None,
    ) -> None:
        super().__init__(name, namespace, host, port)

        logger.info(f"Controller node {self.full_name} created")
        self._shutdown_event = threading.Event()
        self.loop_running = False
        
        # FPS tracking
        self.frame_times = deque(maxlen=10)  # Keep last 10 frame times
        self.last_frame_time = None
        self.frame_count = 0

    async def _setup_async(self) -> None:
        self.reset_client = self.create_client(Reset, "/reset")
        self.step_client = self.create_client(Step, "/step")

    def calculate_and_print_fps(self):
        """Calculate and print current FPS based on frame timestamps"""
        current_time = time.time()
        
        if self.last_frame_time is not None:
            frame_delta = current_time - self.last_frame_time
            self.frame_times.append(frame_delta)
        
        self.last_frame_time = current_time
        self.frame_count += 1
        
        # Print FPS every 30 frames or every 5 seconds
        if self.frame_count % 30 == 0 or (self.frame_times and len(self.frame_times) >= 10):
            if len(self.frame_times) > 1:
                avg_frame_time = sum(self.frame_times) / len(self.frame_times)
                fps = 1.0 / avg_frame_time if avg_frame_time > 0 else 0
                logger.info(f"📷 Current camera FPS: {fps:.2f} (avg over {len(self.frame_times)} frames)")
            # else:
                # logger.info("📷 Calculating FPS...")

    def log_camera_info(self, response):
        """Log information about received camera data"""
        if response.observation and response.observation.observation_cameras:
            cameras = response.observation.observation_cameras
            # Only log camera info every 100 frames to avoid spam
            # if self.frame_count % 100 == 0:
            #     camera_info = []
                # for cam in cameras:
                #     camera_info.append(f"{cam.camera_name}({cam.shape.image_width}x{cam.shape.image_height})")
                # logger.info(f"📹 Received data from {len(cameras)} camera(s): {', '.join(camera_info)}")

    async def request_reset(
        self, seed: int | None = None, options: dict | None = None
    ) -> Reset.Response:
        request = Reset.Request(seed=seed, options=options)

        try:
            response = await self.reset_client.call(request, timeout=30.0)
            return response
        except Exception as e:
            logger.error(f"Error resetting scene: {e}")
            return None

    async def request_step(self, action: ActionModel) -> Step.Response:
        request = Step.Request(action=action)

        try:
            response = await self.step_client.call(request)
            return response
        except Exception as e:
            logger.error(f"Error stepping robot: {e}")
            return None

    async def run_loop(self, rate_hz: float = 120.0) -> None:
        logger.info("Starting control loop")
        if self.loop_running:
            logger.warning("Control loop already running")
            return

        self.loop_running = True
        period = 1.0 / rate_hz

        logger.info(f"Starting control loop at {rate_hz} Hz")

        # Wait for a moment to ensure LuckyRobots core is fully initialized
        await asyncio.sleep(1.0)

        # Attempt to reset the robot
        response = await self.request_reset()
        if response is None:
            self.loop_running = False
            self.shutdown()
            raise Exception("Failed to reset robot, control loop will not start")

        logger.info(f"Reset info: {response.info}")

        try:
            while self.loop_running and not self._shutdown_event.is_set():
                start_time = time.time()

                action = ActionModel(
                    joint_positions={
                        "0": 0.0,  # Rotation
                        "1": 0.0,  # Pitch
                        "2": 0.0,  # Elbow
                        "3": 0.0,  # Wrist Pitch
                        "4": 0.0,  # Wrist Roll
                        "5": 0.0,  # Jaw
                    }
                )
                response = await self.request_step(action)
                if response is None:
                    self.loop_running = False
                    self.shutdown()
                    raise Exception("Step request failed, control loop will not step")

                # Track FPS for camera data
                if response.observation and response.observation.observation_cameras:
                    self.calculate_and_print_fps()
                    self.log_camera_info(response)

                logger.info(f"Step info: {response.info}")

                # Calculate sleep time to maintain the desired rate
                elapsed = time.time() - start_time
                sleep_time = max(0, period - elapsed)
                await asyncio.sleep(sleep_time)
        except Exception as e:
            logger.error(f"Error in control loop: {e}")
        finally:
            self.loop_running = False
            logger.info("Control loop ended")

    def start_loop(self, rate_hz: float = 30.0) -> None:
        if self.loop_running:
            logger.warning("Control loop is already running")
            return

        self._shutdown_event.clear()

        # Use the shared event loop to run our coroutine
        run_coroutine(self.run_loop(rate_hz))
        logger.info("Started control loop in shared event loop")

    def stop_loop(self) -> None:
        self.loop_running = False
        self._shutdown_event.set()
        logger.info("Control loop stop requested")


def main():
    parser = argparse.ArgumentParser(description="Keyboard Teleop for LuckyRobots")
    parser.add_argument("--host", type=str, default=None, help="Host to connect to")
    parser.add_argument("--port", type=int, default=None, help="Port to connect to")
    parser.add_argument(
        "--rate", type=float, default=30.0, help="Control loop rate in Hz"
    )
    parser.add_argument(
        "--show-camera", action="store_true", help="Enable camera feed display windows"
    )
    args = parser.parse_args()

    try:
        luckyrobots = LuckyRobots(host=args.host, port=args.port)
        
        # Set camera display based on command line argument
        luckyrobots.set_camera_display(args.show_camera)
        if args.show_camera:
            logger.info("Camera feed display enabled")
        else:
            logger.info("Camera feed display disabled")

        controller = Controller(host=args.host, port=args.port)

        luckyrobots.register_node(controller)

        luckyrobots.start()

        logger.info("Waiting for Lucky World client to connect...")
        if luckyrobots.wait_for_world_client(timeout=60.0):
            controller.start_loop(rate_hz=args.rate)
            logger.info("Controller running. Press Ctrl+C to exit.")
            luckyrobots.spin()
        else:
            luckyrobots.shutdown()
            raise Exception(
                "No world client connected. Controller loop will not start."
            )

    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt, shutting down...")
    except Exception as e:
        logger.error(f"Error in main: {e}")
    finally:
        if "controller" in locals():
            controller.stop_loop()
        logger.info("Application terminated")


if __name__ == "__main__":
    main()
