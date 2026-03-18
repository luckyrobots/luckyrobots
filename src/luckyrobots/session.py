import logging
import os
from collections.abc import Sequence
from typing import Any, Optional

import numpy as np

from .engine import launch_luckyengine, stop_luckyengine
from .ipc import IpcClient
from .models import ObservationResponse
from .client import LuckyEngineClient, GrpcConnectionError
from .utils import validate_params, get_robot_config

logger = logging.getLogger("luckyrobots")


class Session:
    """
    Managed session with LuckyEngine.

    High-level wrapper around `LuckyEngineClient` that manages the full
    lifecycle: launch engine -> connect via gRPC -> interact -> close.
    """

    def __init__(
        self,
        host: str = "127.0.0.1",
        port: int = 50051,
    ) -> None:
        self.host = host
        self.port = port

        self._engine_client: Optional[LuckyEngineClient] = None
        self._ipc_client: Optional[IpcClient] = None
        self._robot_name: Optional[str] = None

        # Cached metadata (filled after connect)
        self._joint_names: Optional[list[str]] = None
        self._obs_names: Optional[list[str]] = None
        self._act_names: Optional[list[str]] = None

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

        # Try to connect via IPC (shared memory) for fast step/reset
        self._connect_ipc()

    def _require_client(self) -> LuckyEngineClient:
        if self._engine_client is None or not self._engine_client.is_connected():
            raise GrpcConnectionError("Not connected. Call start() or connect() first.")
        return self._engine_client

    def get_joint_state(self):
        """
        Get joint positions/velocities.

        Returns the raw MuJoCo joint state for the robot.
        """
        client = self._require_client()
        if not self._robot_name:
            raise ValueError("Robot name is not set.")
        return client.get_joint_state(robot_name=self._robot_name)

    def step(
        self,
        actions: Sequence[float],
        agent_name: str = "",
    ) -> ObservationResponse:
        """
        Synchronous RL step: apply action, wait for physics, return observation.

        Uses IPC shared memory when available (sub-millisecond latency),
        falls back to gRPC otherwise.

        Args:
            actions: Action vector to apply for this step.
            agent_name: Agent name (empty = default agent).

        Returns:
            ObservationResponse with observation after physics step.
        """
        # Fast path: IPC shared memory
        if self._ipc_client is not None:
            return self._step_ipc(actions)

        # Fallback: gRPC
        client = self._require_client()
        return client.step(actions=list(actions), agent_name=agent_name)

    def set_simulation_mode(self, mode: str = "fast"):
        """
        Set simulation timing mode.

        Args:
            mode: "realtime", "deterministic", or "fast"
                - realtime: Physics runs at 1x wall-clock speed (for visualization)
                - deterministic: Physics runs at fixed rate (for reproducibility)
                - fast: Physics runs as fast as possible (for RL training)
        """
        if self._ipc_client is not None:
            self._ipc_client.set_simulation_mode_cmd(mode)
            return

        client = self._require_client()
        return client.set_simulation_mode(mode=mode)

    def reset(
        self,
        agent_name: str = "",
        randomization_cfg: Optional[Any] = None,
    ) -> ObservationResponse:
        """
        Reset the agent and return a fresh observation.

        Uses IPC reset flags for simple resets. Falls back to gRPC for
        resets with domain randomization configs (until Phase 4 command ring).

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
        # IPC path: all resets go through IPC when available
        if self._ipc_client is not None:
            return self._reset_ipc(randomization_cfg=randomization_cfg)

        # gRPC fallback
        client = self._require_client()
        resp = client.reset_agent(agent_name=agent_name, randomization_cfg=randomization_cfg)
        if hasattr(resp, "success") and not resp.success:
            raise RuntimeError(f"Reset failed: {getattr(resp, 'message', '')}")
        # Step with zero actions to get the initial observation after reset.
        return client.step(actions=[0.0] * 12, agent_name=agent_name)

    def close(self, stop_engine: bool = True) -> None:
        """Close IPC and gRPC clients and optionally stop the engine executable."""
        if self._ipc_client is not None:
            try:
                self._ipc_client.close()
            finally:
                self._ipc_client = None

        if self._engine_client is not None:
            try:
                self._engine_client.close()
            finally:
                self._engine_client = None

        if stop_engine:
            stop_luckyengine()

    def __enter__(self) -> "Session":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close(stop_engine=True)

    @property
    def ipc_client(self) -> Optional[IpcClient]:
        """Access the underlying IPC client, or None if not connected via IPC."""
        return self._ipc_client

    @property
    def engine_client(self) -> Optional[LuckyEngineClient]:
        """Access the underlying LuckyEngine gRPC client for advanced operations."""
        return self._engine_client

    def _connect_ipc(self) -> None:
        """Try to connect via IPC shared memory. Non-fatal if it fails."""
        shm_name = os.environ.get("LUCKY_SHM_NAME")
        if not shm_name:
            logger.debug("LUCKY_SHM_NAME not set, IPC not available")
            return

        try:
            ipc = IpcClient(shm_name)
            if ipc.wait_for_engine(timeout=10.0):
                self._ipc_client = ipc

                # Cache schema from shm
                schema = ipc.get_schema()
                self._obs_names = schema.get("obs_names")
                self._act_names = schema.get("act_names")

                logger.info("IPC transport active: step/reset will use shared memory")
            else:
                logger.warning("IPC shared memory exists but engine not ready, using gRPC")
                ipc.close()
        except Exception as e:
            logger.debug("IPC connection failed (will use gRPC): %s", e)

    def _step_ipc(self, actions: Sequence[float]) -> ObservationResponse:
        """Execute a step via IPC shared memory."""
        ipc = self._ipc_client
        actions_arr = np.asarray(actions, dtype=np.float32)
        obs, rewards, dones = ipc.step(actions_arr)

        # Convert to ObservationResponse for API compatibility
        return ObservationResponse(
            observation=obs.ravel().tolist(),
            actions=actions_arr.ravel().tolist(),
            timestamp_ms=0,
            frame_number=int(ipc.header.frame_seq),
            agent_name="agent_0",
            observation_names=self._obs_names,
            action_names=self._act_names,
        )

    def _reset_ipc(self, randomization_cfg: Optional[Any] = None) -> ObservationResponse:
        """Execute a reset via IPC.

        Simple resets use shm reset flags. Resets with domain randomization
        use the ring buffer command channel.
        """
        ipc = self._ipc_client

        if randomization_cfg is not None:
            # Build simulation_contract dict from config object
            contract = self._build_contract_dict(randomization_cfg)
            ipc.reset_agent_cmd(simulation_contract=contract)
            # After the ring buffer reset, step to get fresh observation
            obs, rewards, dones = ipc.step(np.zeros(ipc.act_size, dtype=np.float32))
        else:
            obs, rewards, dones = ipc.reset()

        return ObservationResponse(
            observation=obs.ravel().tolist(),
            actions=[0.0] * ipc.act_size,
            timestamp_ms=0,
            frame_number=int(ipc.header.frame_seq),
            agent_name="agent_0",
            observation_names=self._obs_names,
            action_names=self._act_names,
        )

    @staticmethod
    def _build_contract_dict(config: Any) -> dict:
        """Convert a config object to a simulation_contract dict for IPC."""
        contract: dict[str, Any] = {}

        def get_val(name: str):
            val = getattr(config, name, None)
            if val is None or (isinstance(val, (tuple, list)) and len(val) == 0):
                return None
            return val

        for field in [
            "pose_position_noise", "pose_orientation_noise",
            "joint_position_noise", "joint_velocity_noise",
            "friction_range", "restitution_range",
            "mass_scale_range", "com_offset_range",
            "motor_strength_range", "motor_offset_range",
            "push_interval_range", "push_velocity_range",
            "vel_command_x_range", "vel_command_y_range",
            "vel_command_yaw_range", "vel_command_resampling_time_range",
            "vel_command_standing_probability",
            "terrain_type", "terrain_difficulty",
        ]:
            val = get_val(field)
            if val is not None:
                if isinstance(val, (list, tuple)):
                    contract[field] = list(val)
                else:
                    contract[field] = val

        return contract
