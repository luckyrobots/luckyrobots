"""Simple example for controlling a single robot.

This minimal example demonstrates how to:
1. Connect to a robot
2. Create service clients for resetting and stepping the robot
3. Create a publisher for sending actions
4. Subscribe to robot observations
5. Implement a basic control loop
"""

import time
import asyncio
import logging
import threading

from luckyrobots import *

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("controller")


class Controller(Node):
    """Example node that controls a robot"""

    def __init__(
        self,
        name: str = "controller",
        namespace: str = "",
        host: str = None,
        port: int = None,
    ) -> None:
        """Initialize the robot controller node.

        Args:
            name: The name of the node
            namespace: The namespace for the node
            host: The host to connect to
            port: The port to connect to
        """
        super().__init__(name, namespace, host, port)

        logger.info(f"Robot controller node {self.full_name} created")
        self._control_thread = None
        self._shutdown_event = threading.Event()

    def _setup(self) -> None:
        """Setup the node."""
        self.latest_observation = None
        self.loop_running = False

        self.action_pub = self.create_publisher(ActionModel, "/action")
        self.observation_sub = self.create_subscription(
            ObservationModel, "/observation", self.observation_callback
        )

        self.reset_client = self.create_client(Reset, "/reset")
        self.step_client = self.create_client(Step, "/step")

    def observation_callback(self, observation: ObservationModel) -> None:
        """Process a new observation.

        Args:
            observation: The observation to process
        """
        self.latest_observation = observation
        logger.info(f"Received observation with timestamp: {observation.time_stamp}")

    async def request_reset(self, seed: int = None) -> Reset.Response:
        """Request a reset of the scene to an initial state.

        Returns:
            The response from the reset service
        """
        logger.info(
            f"Resetting scene with seed: {seed if seed is not None else 'random'}"
        )
        request = Reset.Request(seed=seed)

        try:
            response = await self.reset_client.call(request, timeout=500)
            logger.info(f"Reset response: {response.success}, {response.message}")
            return response
        except Exception as e:
            logger.error(f"Error resetting scene: {e}")
            return None

    async def request_step(self, twist: TwistModel) -> Step.Response:
        """Request a step with the robot given a twist.

        Args:
            twist: The twist to execute

        Returns:
            The response from the step service
        """
        logger.info(f"Stepping robot with twist: {twist}")
        request = Step.Request(twist=twist)

        try:
            response = await self.step_client.call(request)
            logger.info(f"Step response: {response.success}")
            return response
        except Exception as e:
            logger.error(f"Error stepping robot: {e}")
            return None

    async def run_loop(self, rate_hz: float = 1.0) -> None:
        """Start the control loop.

        Args:
            rate_hz: The frequency to run the control loop at in Hz
        """

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
            logger.error("Failed to reset robot, control loop will not start")
            self.loop_running = False
            return

        try:
            while self.loop_running and not self._shutdown_event.is_set():
                start_time = time.time()

                action = ActionModel(
                    twist=TwistModel(
                        linear={"x": 0.5, "y": 0.0, "z": 0.0},
                        angular={"x": 0.0, "y": 0.0, "z": 0.0},
                    ),
                )

                self.action_pub.publish(action)

                response = await self.request_step(action.twist)
                if response is None:
                    logger.warning("Step request failed, continuing loop")

                logger.info(f"Step response: {response.success}")

                # Calculate sleep time to maintain the desired rate
                elapsed = time.time() - start_time
                sleep_time = max(0, period - elapsed)
                await asyncio.sleep(sleep_time)
        except Exception as e:
            logger.error(f"Error in control loop: {e}")
        finally:
            self.loop_running = False
            logger.info("Control loop ended")

    def start_loop(self, rate_hz: float = 1.0) -> None:
        """Start the control loop in a background thread."""
        if self._control_thread is not None and self._control_thread.is_alive():
            logger.warning("Control thread is already running")
            return

        self._shutdown_event.clear()

        def run_async_loop():
            # Create a new event loop for this thread
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

            try:
                loop.run_until_complete(self.run_loop(rate_hz))
            except Exception as e:
                logger.error(f"Error in control thread: {e}")
            finally:
                loop.close()

        self._control_thread = threading.Thread(target=run_async_loop, daemon=True)
        self._control_thread.start()
        logger.info("Started control loop in background thread")

    def stop_loop(self) -> None:
        """Stop the control loop"""
        self.loop_running = False
        self._shutdown_event.set()
        logger.info("Control loop stop requested")

        if self._control_thread and self._control_thread.is_alive():
            self._control_thread.join(timeout=2.0)
            if self._control_thread.is_alive():
                logger.warning("Control thread did not terminate gracefully")
            else:
                logger.info("Control thread terminated")


def main():
    try:
        luckyrobots = LuckyRobots()

        host = get_param("host", "localhost")
        port = get_param("port", 3000)

        controller = Controller(host=host, port=port)

        luckyrobots.register_node(controller)

        luckyrobots.start()

        # Wait for world client to connect
        logger.info("Waiting for Unreal world client to connect...")
        if luckyrobots.wait_for_world_client(timeout=60.0):
            # Start the controller loop once world client is connected
            controller.start_loop(rate_hz=10)
            logger.info("Controller running. Press Ctrl+C to exit.")
        else:
            logger.error("No world client connected. Controller loop will not start.")

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
