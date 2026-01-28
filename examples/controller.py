"""
Minimal example: control a robot in LuckyEngine via gRPC.

This example demonstrates how to:
1. Launch LuckyEngine
2. Connect to LuckyEngine via gRPC
3. Send control commands (MujocoService.SendControl)
4. Read back robot state and observations
5. Reset the agent periodically during the control loop
"""

import argparse
import logging
import time

import numpy as np

from luckyrobots import (
    GrpcConnectionError,
    LuckyEngineClient,
    LuckyRobots,
    ObservationDefaults,
)
from luckyrobots.engine import launch_luckyengine, stop_luckyengine

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("controller")


class Controller:
    """Minimal gRPC controller that sends random actions."""

    def __init__(self, host: str, port: int, robot: str) -> None:
        self.robot = robot
        self.client = LuckyEngineClient(
            host=host,
            port=port,
            robot_name=robot,
            observation_defaults=ObservationDefaults(
                include_joint_state=True,
                include_agent_frame=True,
                include_telemetry=False,
            ),
        )

        robot_cfg = LuckyRobots.get_robot_config(robot)
        limits = robot_cfg["action_space"]["actuator_limits"]
        self._lower = np.array([a["lower"] for a in limits], dtype=np.float32)
        self._upper = np.array([a["upper"] for a in limits], dtype=np.float32)

        logger.info("Controller created for robot=%s", robot)

    def connect(self, timeout_s: float = 120.0) -> None:
        """Connect to LuckyEngine gRPC server."""
        if not self.client.wait_for_server(timeout=timeout_s):
            raise GrpcConnectionError(
                f"Could not connect to LuckyEngine gRPC server within {timeout_s}s"
            )

        logger.info("Fetching MuJoCo info...")
        try:
            mujoco_info = self.client.get_mujoco_info()
            logger.info(
                "Connected. MuJoCo: nq=%s nv=%s nu=%s joints=%s",
                getattr(mujoco_info, "nq", None),
                getattr(mujoco_info, "nv", None),
                getattr(mujoco_info, "nu", None),
                len(getattr(mujoco_info, "joint_names", []) or []),
            )
        except Exception as e:
            logger.error("Failed to get MuJoCo info: %s", e, exc_info=True)
            raise

    def sample_action(self) -> np.ndarray:
        """Sample a single action within the robot's actuator limits."""
        return np.random.uniform(low=self._lower, high=self._upper).astype(np.float32)

    def step(self, controls: np.ndarray) -> np.ndarray:
        """Send a control vector and read back a unified observation snapshot."""
        resp = self.client.send_control(controls=[float(x) for x in controls])
        if hasattr(resp, "success") and not resp.success:
            raise RuntimeError(f"SendControl failed: {getattr(resp, 'message', '')}")

        obs = self.client.get_observation(agent_name="")
        if hasattr(obs, "success") and not obs.success:
            raise RuntimeError(f"GetObservation failed: {getattr(obs, 'message', '')}")

        # Prefer agent-frame observation vector
        if getattr(obs, "agent_frame", None) is not None:
            return np.array(list(obs.agent_frame.observations), dtype=np.float32)

        # Fallback (shouldn't happen if include_agent_frame=True)
        return np.zeros((0,), dtype=np.float32)

    def run_loop(self, rate_hz: float, duration_s: float) -> None:
        """Run a simple control loop at the requested rate for a fixed duration.

        The agent will be reset every 10 seconds during the loop.
        """
        period = 1.0 / rate_hz
        end_time = time.perf_counter() + duration_s
        last_reset_time = time.perf_counter()
        reset_interval_s = 10.0

        logger.info(
            "Starting control loop at %.1f Hz for %.1f seconds", rate_hz, duration_s
        )

        while time.perf_counter() < end_time:
            start = time.perf_counter()

            # Reset the agent every 10 seconds
            current_time = time.perf_counter()
            if current_time - last_reset_time >= reset_interval_s:
                logger.info("Resetting agent")
                try:
                    resp = self.client.reset_agent()
                    if hasattr(resp, "success") and resp.success:
                        logger.info(
                            "Agent reset successful: %s", getattr(resp, "message", "")
                        )
                    else:
                        logger.warning(
                            "Agent reset returned success=False: %s",
                            getattr(resp, "message", ""),
                        )
                except Exception as e:
                    logger.error("Failed to reset agent: %s", e, exc_info=True)
                last_reset_time = current_time

            action = self.sample_action()
            obs_vec = self.step(action)

            elapsed = time.perf_counter() - start
            time.sleep(max(0.0, period - elapsed))


def main() -> None:
    parser = argparse.ArgumentParser(description="LuckyEngine gRPC control example")
    parser.add_argument("--executable-path", type=str, default=None)
    parser.add_argument("--host", type=str, default="172.24.160.1")
    parser.add_argument("--port", type=int, default=50051)
    parser.add_argument("--scene", type=str, default="velocity")
    parser.add_argument("--task", type=str, default="locomotion")
    parser.add_argument("--robot", type=str, default="unitreego1")
    parser.add_argument("--rate", type=float, default=10.0)
    parser.add_argument("--duration", type=float, default=60.0)
    parser.add_argument(
        "--skip-launch",
        action="store_true",
        help="Skip launching LuckyEngine (assume it's already running)",
    )
    args = parser.parse_args()

    launched_here = False
    try:
        if not args.skip_launch:
            logger.info("Launching LuckyEngine...")
            ok = launch_luckyengine(
                scene=args.scene,
                robot=args.robot,
                task=args.task,
                executable_path=args.executable_path,
            )
            if not ok:
                raise RuntimeError("Failed to launch LuckyEngine")
            launched_here = True
        else:
            logger.info("Skipping launch (--skip-launch flag set)")

        controller = Controller(host=args.host, port=args.port, robot=args.robot)
        controller.connect(timeout_s=120.0)
        controller.run_loop(rate_hz=args.rate, duration_s=args.duration)
    finally:
        if launched_here:
            stop_luckyengine()


if __name__ == "__main__":
    main()
