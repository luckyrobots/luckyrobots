import logging
import time

from collections.abc import Sequence
from typing import Optional

from typing import Any

from .engine import launch_luckyengine, stop_luckyengine
from .models import ObservationResponse
from .client import LuckyEngineClient, GrpcConnectionError
from .utils import validate_params, get_robot_config

logger = logging.getLogger("luckyrobots")


class LuckyRobots:
    """
    gRPC-only control surface for LuckyEngine.

    This is a small convenience wrapper around `LuckyEngineClient` that can:
    - launch the LuckyEngine executable (optional)
    - connect to the LuckyEngine gRPC server
    - send controls and fetch unified observations
    """

    def __init__(
        self,
        host: str = "127.0.0.1",
        port: int = 50051,
    ) -> None:
        self.host = host
        self.port = port

        self._engine_client: Optional[LuckyEngineClient] = None
        self._robot_name: Optional[str] = None

        # Cached metadata (filled after connect)
        self._joint_names: Optional[list[str]] = None

    @staticmethod
    def get_robot_config(robot: str = None) -> dict:
        """Return robot config from `luckyrobots/config/robots.yaml`."""
        return get_robot_config(robot)

    def start(
        self,
        scene: str,
        robot: str,
        task: str,
        executable_path: str = None,
        observation_type: str = "pixels_agent_pos",
        headless: bool = False,
        timeout_s: float = 120.0,
    ) -> None:
        """
        Launch LuckyEngine (if needed) and connect to gRPC.

        Args:
            scene: LuckyEngine scene name.
            robot: Robot name (must exist in `robots.yaml`).
            task: Task name (must exist in `robots.yaml`).
            executable_path: Path to LuckyEngine executable (optional; auto-detected).
            observation_type: Used for validation and optional camera processing.
            headless: Launch without rendering.
            timeout_s: How long to wait for gRPC server to come up.
        """
        validate_params(scene, robot, task, observation_type)
        self._robot_name = robot

        success = launch_luckyengine(
            scene=scene,
            robot=robot,
            task=task,
            executable_path=executable_path,
            headless=headless,
        )
        if not success:
            logger.error("Failed to launch LuckyEngine")
            raise RuntimeError(
                "Failed to launch LuckyEngine. Look through the log for more information."
            )

        self.connect(timeout_s=timeout_s, robot=robot)

    def connect(self, timeout_s: float = 120.0, robot: Optional[str] = None) -> None:
        """Connect to LuckyEngine gRPC server and cache MuJoCo metadata."""
        if robot is not None:
            self._robot_name = robot
        if not self._robot_name:
            raise ValueError("Robot name is required (pass `robot=` or call start()).")

        self._engine_client = LuckyEngineClient(
            host=self.host,
            port=self.port,
            robot_name=self._robot_name,
        )
        logger.info(
            "Waiting for LuckyEngine gRPC server at %s:%s", self.host, self.port
        )
        if not self._engine_client.wait_for_server(timeout=timeout_s):
            raise GrpcConnectionError(
                f"LuckyEngine gRPC server connection timeout after {timeout_s} seconds"
            )

        mujoco_info = self._engine_client.get_mujoco_info(robot_name=self._robot_name)
        self._joint_names = (
            list(mujoco_info.joint_names) if mujoco_info.joint_names else []
        )
        logger.info(
            "Connected. MuJoCo: nq=%s nv=%s nu=%s joints=%s",
            getattr(mujoco_info, "nq", None),
            getattr(mujoco_info, "nv", None),
            getattr(mujoco_info, "nu", None),
            len(self._joint_names),
        )

    def _require_client(self) -> LuckyEngineClient:
        if self._engine_client is None or not self._engine_client.is_connected():
            raise GrpcConnectionError("Not connected. Call start() or connect() first.")
        return self._engine_client

    def get_observation(self, agent_name: str = "") -> ObservationResponse:
        """
        Get observation vector.

        This returns only the flat observation vector defined by the agent's
        observation spec. For sensor data, use the dedicated methods:
        - get_joint_state() for joint positions/velocities
        - engine_client.stream_telemetry() for telemetry
        - engine_client.stream_camera() for camera frames

        Args:
            agent_name: Agent name (empty = default agent).

        Returns:
            ObservationResponse with observation vector, actions, timestamp.
        """
        client = self._require_client()
        return client.get_observation(agent_name=agent_name)

    def get_joint_state(self):
        """
        Get joint positions/velocities.

        Returns the raw MuJoCo joint state for the robot.
        """
        client = self._require_client()
        if not self._robot_name:
            raise ValueError("Robot name is not set.")
        return client.get_joint_state(robot_name=self._robot_name)

    def send_control(self, controls: Sequence[float]) -> None:
        """Send control commands to the robot via gRPC."""
        client = self._require_client()
        if not self._robot_name:
            raise ValueError("Robot name is not set.")

        resp = client.send_control(
            controls=[float(x) for x in controls],
            robot_name=self._robot_name,
        )
        if hasattr(resp, "success") and not resp.success:
            raise RuntimeError(f"SendControl failed: {getattr(resp, 'message', '')}")

    def step(
        self, controls: Sequence[float], sleep_s: float = 0.01
    ) -> ObservationResponse:
        """Send controls, wait briefly for physics, then return a fresh observation."""
        self.send_control(controls)
        if sleep_s > 0:
            time.sleep(sleep_s)
        return self.get_observation()

    def reset(
        self,
        agent_name: str = "",
        randomization_cfg: Optional[Any] = None,
    ) -> ObservationResponse:
        """
        Reset the agent and return a fresh observation.

        Args:
            agent_name: Agent logical name. Empty string means default agent.
            randomization_cfg: Optional domain randomization config for this reset.
                Use this to randomize physics parameters (friction, mass, etc.)
                at the start of each episode for sim-to-real transfer.

        Returns:
            ObservationResponse after reset.

        Raises:
            RuntimeError: If reset fails.
        """
        client = self._require_client()
        resp = client.reset_agent(agent_name=agent_name, randomization_cfg=randomization_cfg)
        if hasattr(resp, "success") and not resp.success:
            raise RuntimeError(f"Reset failed: {getattr(resp, 'message', '')}")
        return self.get_observation(agent_name=agent_name)

    def close(self, stop_engine: bool = True) -> None:
        """Close gRPC client and optionally stop the engine executable."""
        if self._engine_client is not None:
            try:
                self._engine_client.close()
            finally:
                self._engine_client = None

        if stop_engine:
            stop_luckyengine()

    def __enter__(self) -> "LuckyRobots":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close(stop_engine=True)

    @property
    def engine_client(self) -> Optional[LuckyEngineClient]:
        """Access the underlying LuckyEngine gRPC client for advanced operations."""
        return self._engine_client
