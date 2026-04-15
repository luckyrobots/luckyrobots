import logging
from collections.abc import Sequence
from typing import Any, Optional

from .engine import launch_luckyengine, stop_luckyengine
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
        task_contract: dict | None = None,
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
            task_contract: Optional task contract dict for engine-side MDP computation.
                When provided, the engine is configured to compute reward signals
                and termination flags alongside observations. Pass a dict with
                observations, rewards, terminations sections — see LuckyEnv or
                luckylab.contracts.TaskContract.to_dict() for the expected format.
        """
        self._robot_name = robot

        success = launch_luckyengine(
            scene=scene,
            robot=robot,
            task=task,
            executable_path=executable_path,
            headless=headless,
            auto_play=True,
            grpc_port=self.port,
        )
        if not success:
            logger.error("Failed to launch LuckyEngine")
            raise RuntimeError(
                "Failed to launch LuckyEngine. Look through the log for more information."
            )

        self.connect(timeout_s=timeout_s, robot=robot)
        self._wait_for_agents_ready(timeout_s=timeout_s)

        # Negotiate task contract if provided (engine-side reward/termination computation).
        self._negotiated_session = None
        if task_contract is not None:
            self._negotiated_session = self._engine_client.negotiate_task(task_contract)
            logger.info(
                "Task contract negotiated: session=%s, rewards=%s, terminations=%s",
                self._negotiated_session.get("session_id", "?"),
                self._negotiated_session.get("reward_terms", []),
                self._negotiated_session.get("termination_terms", []),
            )

    def _wait_for_agents_ready(self, timeout_s: float = 120.0) -> None:
        """Wait for the engine's agent pipeline to be ready (scene fully playing)."""
        import time
        logger.info("Waiting for agents to be ready...")
        deadline = time.monotonic() + timeout_s
        while time.monotonic() < deadline:
            try:
                schema = self._engine_client.get_agent_schema()
                if schema.schema.observation_size > 0:
                    logger.info("Agents ready (obs_size=%d, action_size=%d)",
                                schema.schema.observation_size, schema.schema.action_size)
                    return
            except Exception:
                pass
            time.sleep(1.0)
        raise RuntimeError(
            f"Agents not ready after {timeout_s}s. "
            "The scene may not have entered Play mode."
        )

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

    def get_joint_state(self):
        """
        Get joint positions/velocities.

        Returns the raw MuJoCo joint state for the robot.
        """
        client = self._require_client()
        if not self._robot_name:
            raise ValueError("Robot name is not set.")
        return client.get_joint_state(robot_name=self._robot_name)

    def configure_cameras(self, cameras: list[dict]) -> None:
        """Configure cameras to capture on every step.

        Once configured, every call to step() and reset() will include
        synchronized camera frames in the returned ObservationResponse.

        Args:
            cameras: List of camera configs. Each dict has keys:
                name: Camera entity name in the scene.
                width: Desired image width (0 = native resolution).
                height: Desired image height (0 = native resolution).
        """
        client = self._require_client()
        client.configure_cameras(cameras)

    def list_cameras(self) -> list[dict]:
        """List available cameras in the scene.

        Returns:
            List of dicts with 'name' and 'id' keys for each camera.
        """
        client = self._require_client()
        return client.list_cameras()

    def set_action_group(
        self,
        group_name: str,
        actions: Sequence[float],
        action_indices: Sequence[int],
        agent_name: str = "",
    ) -> bool:
        """Preload actions for a named group without triggering a physics step.

        Call this for each policy/controller, then call step() to fire them
        all atomically in one physics tick.

        Args:
            group_name: Name for this action group (e.g., "lower_body", "right_arm").
            actions: Action values for this group.
            action_indices: Which indices in the action vector these map to.
            agent_name: Agent name (empty = default agent).

        Returns:
            True if the group was preloaded successfully.
        """
        client = self._require_client()
        return client.set_action_group(
            group_name=group_name,
            actions=list(actions),
            action_indices=list(action_indices),
            agent_name=agent_name,
        )

    def step(
        self,
        actions: Sequence[float] | None = None,
        agent_name: str = "",
        action_groups: list[dict] | None = None,
    ) -> ObservationResponse:
        """
        Synchronous RL step: apply action, wait for physics, return observation.

        This is the recommended interface for RL training. It uses the gRPC Step RPC
        which atomically applies the action, advances physics, and returns the
        observation in a single call.

        Args:
            actions: Action vector to apply for this step (optional when using action_groups).
            agent_name: Agent name (empty = default agent).
            action_groups: Optional list of action group dicts for multi-policy control.
                Each dict has keys: group_name, actions, action_indices.

        Returns:
            ObservationResponse with observation after physics step.
        """
        client = self._require_client()
        return client.step(
            actions=list(actions) if actions is not None else None,
            agent_name=agent_name,
            action_groups=action_groups,
        )

    def set_simulation_mode(self, mode: str = "fast"):
        """
        Set simulation timing mode.

        Args:
            mode: "realtime", "deterministic", or "fast"
                - realtime: Physics runs at 1x wall-clock speed (for visualization)
                - deterministic: Physics runs at fixed rate (for reproducibility)
                - fast: Physics runs as fast as possible (for RL training)
        """
        client = self._require_client()
        return client.set_simulation_mode(mode=mode)

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

        # The Learn pipeline may still be initializing when we first connect.
        # Retry reset for up to 10 seconds if the batch isn't ready yet.
        import time as _time
        deadline = _time.perf_counter() + 10.0
        while True:
            resp = client.reset_agent(agent_name=agent_name, randomization_cfg=randomization_cfg)
            if hasattr(resp, "success") and not resp.success:
                msg = getattr(resp, "message", "")
                if "not ready yet" in msg and _time.perf_counter() < deadline:
                    _time.sleep(0.25)
                    continue
                raise RuntimeError(f"Reset failed: {msg}")
            break

        # Step with zero actions to get the initial observation after reset.
        # Query the agent schema for the correct action size (cached after first call).
        schema = client.get_agent_schema(agent_name=agent_name)
        action_size = schema.schema.action_size if schema.schema else 12
        return client.step(actions=[0.0] * action_size, agent_name=agent_name)

    def report_progress(self, **kwargs) -> None:
        """Report evaluation/training progress to the engine for UI display.

        Accepts all keyword arguments of LuckyEngineClient.report_progress().
        Fire-and-forget: errors are silently ignored.
        """
        client = self._require_client()
        client.report_progress(**kwargs)

    def close(self, stop_engine: bool = True) -> None:
        """Close gRPC client and optionally stop the engine executable."""
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
    def engine_client(self) -> Optional[LuckyEngineClient]:
        """Access the underlying LuckyEngine gRPC client for advanced operations."""
        return self._engine_client
