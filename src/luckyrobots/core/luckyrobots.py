import logging
import time

from collections.abc import Sequence
from typing import Optional

from ..utils.sim_manager import launch_luckyengine, stop_luckyengine
from ..core.models import ObservationModel
from ..rpc import LuckyEngineClient, GrpcConnectionError
from ..utils.helpers import (
    validate_params,
    get_robot_config,
)

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

    def get_observation(
        self,
        agent_name: str = "",
        include_joint_state: bool = True,
        include_agent_frame: bool = True,
        include_telemetry: bool = False,
        camera_names: Optional[list[str]] = None,
        viewport_names: Optional[list[str]] = None,
        width: int = 0,
        height: int = 0,
        format: str = "raw",
    ) -> ObservationModel:
        """
        Fetch a unified observation snapshot via `AgentService.GetObservation`.

        This requires LuckyEngine to implement the new RPC. The observation content is
        controlled by the request fields (agent/joints/telemetry/images).
        """
        if self._engine_client is None:
            raise GrpcConnectionError("gRPC client not initialized")

        client = self._require_client()
        if not self._robot_name:
            raise ValueError("Robot name is not set.")

        resp = client.get_observation(
            robot_name=self._robot_name,
            agent_name=agent_name,
            include_joint_state=include_joint_state,
            include_agent_frame=include_agent_frame,
            include_telemetry=include_telemetry,
            camera_names=camera_names,
            viewport_names=viewport_names,
            width=width,
            height=height,
            format=format,
        )
        if hasattr(resp, "success") and not resp.success:
            raise RuntimeError(f"GetObservation failed: {getattr(resp, 'message', '')}")

        # Build ObservationModel from returned components.
        observation = ObservationModel()

        # Agent frame (preferred "observation vector" path)
        if getattr(resp, "agent_frame", None) is not None:
            observation = ObservationModel.from_grpc_agent_frame(
                resp.agent_frame,
                joint_names=self._joint_names,
            )

        # Joint state (optional; can also populate observation_state)
        if getattr(resp, "joint_state", None) is not None and include_joint_state:
            joint_obs = ObservationModel.from_grpc_joint_state(
                resp.joint_state,
                joint_names=self._joint_names,
            )
            # Merge: prefer agent-derived vector/timestamps, but keep joint state mapping.
            observation.observation_state = joint_obs.observation_state
            if observation.observation_vector is None:
                observation.observation_vector = joint_obs.observation_vector

        # Timestamp/frame metadata (best-effort)
        observation.timestamp_ms = getattr(resp, "timestamp_ms", None)
        observation.frame_number = getattr(resp, "frame_number", None)

        # Camera frames (optional)
        camera_frames = getattr(resp, "camera_frames", None) or []
        if camera_frames:
            from ..core.models import CameraData

            observation.observation_cameras = [
                CameraData.from_grpc_frame(item.frame, camera_name=item.name)
                for item in camera_frames
                if getattr(item, "frame", None) is not None
            ]

        return observation

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
    ) -> ObservationModel:
        """Send controls, wait briefly for physics, then return a fresh observation."""
        self.send_control(controls)
        if sleep_s > 0:
            time.sleep(sleep_s)
        return self.get_observation()

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
