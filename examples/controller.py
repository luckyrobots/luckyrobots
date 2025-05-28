import time
import asyncio
import logging
import threading
import argparse
import numpy as np

from luckyrobots import (
    Node,
    LuckyRobots,
    Step,
    Reset,
    FPS,
    run_coroutine,
    process_images,
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
        show_camera: bool = False,
        robot: str = None,
    ) -> None:
        super().__init__(name, namespace, host, port)

        self.fps = FPS()

        self.show_camera = show_camera
        self.robot_config = LuckyRobots.get_robot_config(robot)

        self.loop_running = False
        self._shutdown_event = threading.Event()
        logger.info(f"Controller node {self.full_name} created")

    async def _setup_async(self) -> None:
        self.reset_client = self.create_client(Reset, "/reset")
        self.step_client = self.create_client(Step, "/step")

    async def request_reset(
        self, seed: int | None = None, options: dict | None = None
    ) -> Reset.Response:
        """Send a reset request to the luckyrobots core"""
        request = Reset.Request(seed=seed, options=options)

        try:
            response = await self.reset_client.call(request)
            if response is not None:
                if self.show_camera:
                    process_images(response.observation.observation_cameras)
                return response
            else:
                self.loop_running = False
                self.shutdown()
                raise Exception("Failed to reset robot, control loop will not start")
        except Exception as e:
            logger.error(f"Error resetting scene: {e}")
            return None

    async def request_step(self, actuator_values: np.ndarray) -> Step.Response:
        """Send a step request to the luckyrobots core"""
        request = Step.Request(actuator_values=actuator_values)

        try:
            response = await self.step_client.call(request)
            if response is not None:
                if self.show_camera:
                    process_images(response.observation.observation_cameras)
                return response
            else:
                self.loop_running = False
                self.shutdown()
                raise Exception("Step request failed, control loop will not step")
        except Exception as e:
            logger.error(f"Error stepping robot: {e}")
            return None

    def sample_action(self) -> np.ndarray:
        """Sample a single action within the robot's joint limits"""
        # Extract lower and upper limits from the joint configuration
        limits = self.robot_config["action_space"]["actuator_limits"]
        lower_limits = np.array([joint["lower"] for joint in limits])
        upper_limits = np.array([joint["upper"] for joint in limits])

        return np.random.uniform(low=lower_limits, high=upper_limits)

    def start_loop(self, rate_hz: float) -> None:
        if self.loop_running:
            logger.warning("Control loop is already running")
            return

        self._shutdown_event.clear()

        # Use the shared event loop to run our coroutine
        run_coroutine(self.run_loop(rate_hz))
        logger.info("Started control loop in shared event loop")
        logger.info("Controller running. Press Ctrl+C to exit.")

    async def run_loop(self, rate_hz: float) -> None:
        logger.info("Starting control loop")
        if self.loop_running:
            logger.warning("Control loop already running")
            return

        period = 1.0 / rate_hz
        self.loop_running = True

        logger.info(f"Starting control loop at {rate_hz} Hz")

        # Wait for a moment to ensure LuckyRobots core is fully initialized
        await asyncio.sleep(1.0)

        response = await self.request_reset()
        self.fps.measure()

        try:
            while self.loop_running and not self._shutdown_event.is_set():
                start_time = time.perf_counter()

                actuator_values = self.sample_action()
                response = await self.request_step(actuator_values)
                self.fps.measure()

                # Calculate sleep time to maintain the desired rate
                elapsed = time.perf_counter() - start_time
                sleep_time = max(0, period - elapsed)
                await asyncio.sleep(sleep_time)
        except Exception as e:
            logger.error(f"Error in control loop: {e}")
        finally:
            self.loop_running = False
            logger.info("Control loop ended")

    def stop_loop(self) -> None:
        self.loop_running = False
        self._shutdown_event.set()
        logger.info("Control loop stop requested")


def main():
    parser = argparse.ArgumentParser(description="Keyboard Teleop for LuckyRobots")
    parser.add_argument("--host", type=str, default="localhost", help="Host to connect to")
    parser.add_argument("--port", type=int, default=3000, help="Port to connect to")
    parser.add_argument(
        "--scene", type=str, default="kitchen", help="Scene to connect to"
    )
    parser.add_argument(
        "--task", type=str, default="pickandplace", help="Task to connect to"
    )
    parser.add_argument(
        "--robot", type=str, default="so100", help="Robot to connect to"
    )
    parser.add_argument(
        "--rate", type=float, default=10.0, help="Control loop rate in Hz"
    )
    parser.add_argument(
        "--show-camera",
        action="store_true",
        default=False,
        help="Enable camera feed display windows",
    )
    args = parser.parse_args()

    try:
        controller = Controller(
            host=args.host,
            port=args.port,
            show_camera=args.show_camera,
            robot=args.robot,
        )

        luckyrobots = LuckyRobots(args.host, args.port)
        luckyrobots.register_node(controller)
        luckyrobots.start(scene=args.scene, task=args.task, robot=args.robot)
        luckyrobots.wait_for_world_client(timeout=60.0)

        controller.start_loop(rate_hz=args.rate)

        luckyrobots.spin()
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
