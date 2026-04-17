"""
LuckyEngine gRPC client.

Uses checked-in Python stubs generated from the `.proto` files under
`src/luckyrobots/grpc/proto/`.
"""

from __future__ import annotations

import logging
import math
import statistics
import time
from types import SimpleNamespace
from typing import Any, Optional

import grpc  # type: ignore

logger = logging.getLogger("luckyrobots.client")

try:
    from .grpc.generated import agent_pb2  # type: ignore
    from .grpc.generated import agent_pb2_grpc  # type: ignore
    from .grpc.generated import camera_pb2  # type: ignore
    from .grpc.generated import camera_pb2_grpc  # type: ignore
    from .grpc.generated import common_pb2  # type: ignore
    from .grpc.generated import debug_pb2  # type: ignore
    from .grpc.generated import debug_pb2_grpc  # type: ignore
    from .grpc.generated import mujoco_pb2  # type: ignore
    from .grpc.generated import mujoco_pb2_grpc  # type: ignore
    from .grpc.generated import mujoco_scene_pb2  # type: ignore
    from .grpc.generated import mujoco_scene_pb2_grpc  # type: ignore
    from .grpc.generated import scene_pb2  # type: ignore
    from .grpc.generated import scene_pb2_grpc  # type: ignore
except Exception as e:  # pragma: no cover
    raise ImportError(
        "Missing generated gRPC stubs. Regenerate them from the protos in "
        "src/luckyrobots/grpc/proto into src/luckyrobots/grpc/generated."
    ) from e

from .models import ObservationResponse
from .models.observation import CameraFrame
from .models.benchmark import BenchmarkResult
from . import sim_contract


class GrpcConnectionError(Exception):
    """Raised when gRPC connection fails."""

    def __init__(self, message: str):
        super().__init__(message)
        logger.warning("gRPC connection error: %s", message)


class LuckyEngineClient:
    """
    Client for connecting to the LuckyEngine gRPC server.

    Provides access to gRPC services for RL training:
    - AgentService: stepping, resets
    - SceneService: simulation mode control
    - MujocoService: health checks, joint state

    Usage:
        client = LuckyEngineClient(host="127.0.0.1", port=50051)
        client.connect()
        client.wait_for_server()

        schema = client.get_agent_schema()
        obs = client.step(actions=[0.0] * 12)

        client.close()
    """

    def __init__(
        self,
        host: str = "127.0.0.1",
        port: int = 50051,
        timeout: float = 5.0,
        *,
        robot_name: Optional[str] = None,
    ) -> None:
        """
        Initialize the LuckyEngine gRPC client.

        Args:
            host: gRPC server host address.
            port: gRPC server port.
            timeout: Default timeout for RPC calls in seconds.
            robot_name: Default robot name for calls that require it.
        """
        self.host = host
        self.port = port
        self.timeout = timeout
        self._robot_name = robot_name

        self._channel = None

        # Service stubs (created lazily on first property access)
        self._scene = None
        self._mujoco = None
        self._mujoco_scene = None
        self._agent = None
        self._camera = None
        self._debug = None

        # Additional user-registered stubs (see register_stub).
        self._extra_stubs: dict[str, Any] = {}

        # Cached agent schemas: agent_name -> (observation_names, action_names)
        self._schema_cache: dict[str, tuple[list[str], list[str]]] = {}

        # Camera requests included on every Step RPC (configured via configure_cameras).
        self._camera_requests: list = []

        # Protobuf modules (for discoverability + explicit imports).
        self._pb = SimpleNamespace(
            common=common_pb2,
            scene=scene_pb2,
            mujoco=mujoco_pb2,
            mujoco_scene=mujoco_scene_pb2,
            agent=agent_pb2,
            debug=debug_pb2,
        )

    def connect(self) -> None:
        """
        Connect to the LuckyEngine gRPC server.

        Opens the gRPC channel. Service stubs are created lazily on first
        access so importers can skip unused services without cost.

        Raises:
            GrpcConnectionError: If connection fails.
        """
        target = f"{self.host}:{self.port}"
        logger.info(f"Connecting to LuckyEngine gRPC server at {target}")

        self._channel = grpc.insecure_channel(target)

        # Drop any cached stubs so a reconnect re-binds them to the new channel.
        self._scene = None
        self._mujoco = None
        self._mujoco_scene = None
        self._agent = None
        self._camera = None
        self._debug = None
        self._extra_stubs: dict[str, Any] = {}

        logger.info(f"Channel opened to {target} (server not verified yet)")

    def close(self) -> None:
        """Close the gRPC channel."""
        if self._channel is not None:
            try:
                self._channel.close()
            except Exception as e:
                logger.debug(f"Error closing gRPC channel: {e}")
            self._channel = None
            self._scene = None
            self._mujoco = None
            self._mujoco_scene = None
            self._agent = None
            self._camera = None
            self._debug = None
            self._extra_stubs = {}
            logger.info("gRPC channel closed")

    def is_connected(self) -> bool:
        """Check if the client is connected."""
        return self._channel is not None

    def health_check(self, timeout: Optional[float] = None) -> bool:
        """
        Perform a health check by calling GetMujocoInfo.

        Args:
            timeout: Timeout in seconds (uses default if None).

        Returns:
            True if server responds, False otherwise.
        """
        if not self.is_connected():
            return False

        timeout = timeout or self.timeout
        try:
            self._mujoco.GetMujocoInfo(
                self.pb.mujoco.GetMujocoInfoRequest(robot_name=self._robot_name or ""),
                timeout=timeout,
            )
            return True
        except Exception as e:
            logger.debug(f"Health check failed: {e}")
            return False

    def wait_for_server(
        self, timeout: float = 30.0, poll_interval: float = 0.5
    ) -> bool:
        """
        Wait for the gRPC server to become available.

        Args:
            timeout: Maximum time to wait in seconds.
            poll_interval: Time between connection attempts.

        Returns:
            True if server became available, False if timeout.
        """
        start = time.perf_counter()

        while time.perf_counter() - start < timeout:
            if not self.is_connected():
                try:
                    self.connect()
                except Exception:
                    pass

            if self.health_check(timeout=min(poll_interval, timeout - (time.perf_counter() - start))):
                logger.info(f"Connected to LuckyEngine gRPC server at {self.host}:{self.port}")
                return True

            time.sleep(poll_interval)

        return False

    @property
    def pb(self) -> Any:
        """Access protobuf modules grouped by domain (e.g., `client.pb.scene`)."""
        return self._pb

    @property
    def robot_name(self) -> Optional[str]:
        """Default robot name used by calls that accept an optional robot_name."""
        return self._robot_name

    def set_robot_name(self, robot_name: str) -> None:
        """Set the default robot name used by calls that accept an optional robot_name."""
        self._robot_name = robot_name

    @property
    def channel(self) -> grpc.Channel:
        """The underlying gRPC channel.

        Exposed so users can attach their own service stubs using the same
        connection (shared keep-alive, auth, etc.):

            client.connect()
            my_stub = my_pb2_grpc.MyServiceStub(client.channel)
        """
        if self._channel is None:
            raise GrpcConnectionError("Not connected. Call connect() first.")
        return self._channel

    @property
    def scene(self) -> Any:
        """SceneService stub (lazy)."""
        if self._scene is None:
            self._scene = scene_pb2_grpc.SceneServiceStub(self.channel)
        return self._scene

    @property
    def mujoco(self) -> Any:
        """MujocoService stub (lazy) — agent-scoped joint state.

        For the full, engine-wide MuJoCo model (every joint, every actuator),
        use :attr:`mujoco_scene` instead.
        """
        if self._mujoco is None:
            self._mujoco = mujoco_pb2_grpc.MujocoServiceStub(self.channel)
        return self._mujoco

    @property
    def mujoco_scene(self) -> Any:
        """MujocoSceneService stub (lazy) — engine-wide MuJoCo access.

        Exposes every joint, actuator, and the full qpos/qvel/ctrl vectors
        in the loaded model. Use the higher-level helpers
        :meth:`get_model_info`, :meth:`get_full_state`, and :meth:`set_ctrl`
        for common operations.
        """
        if self._mujoco_scene is None:
            self._mujoco_scene = mujoco_scene_pb2_grpc.MujocoSceneServiceStub(self.channel)
        return self._mujoco_scene

    @property
    def agent(self) -> Any:
        """AgentService stub (lazy)."""
        if self._agent is None:
            self._agent = agent_pb2_grpc.AgentServiceStub(self.channel)
        return self._agent

    @property
    def debug(self) -> Any:
        """DebugService stub (lazy)."""
        if self._debug is None:
            self._debug = debug_pb2_grpc.DebugServiceStub(self.channel)
        return self._debug

    @property
    def camera(self) -> Any:
        """CameraService stub (lazy)."""
        if self._camera is None:
            self._camera = camera_pb2_grpc.CameraServiceStub(self.channel)
        return self._camera

    # ── Extension seam for user-provided services ──

    def register_stub(self, name: str, stub_class: Any) -> Any:
        """Attach a third-party stub class to this client's channel.

        Useful when an engine build exposes a service that the shipped SDK
        doesn't know about:

            client.register_stub("my_svc", my_pb2_grpc.MyServiceStub)
            client.my_svc.DoThing(...)

        Args:
            name: Attribute name under which the stub is exposed.
            stub_class: Generated ``*Stub`` class from a ``_pb2_grpc`` module.

        Returns:
            The instantiated stub (also available as ``client.<name>``).
        """
        if not name or name.startswith("_"):
            raise ValueError("Stub name must be non-empty and not start with '_'.")
        if hasattr(type(self), name):
            raise ValueError(
                f"Cannot register stub '{name}': attribute reserved on LuckyEngineClient."
            )
        stub = stub_class(self.channel)
        self._extra_stubs[name] = stub
        return stub

    def __getattr__(self, name: str) -> Any:
        # Only reached for attributes not found on self or the class.
        # Resolves user-registered stubs as ``client.<name>``.
        extras = self.__dict__.get("_extra_stubs")
        if extras and name in extras:
            return extras[name]
        raise AttributeError(name)

    def discover_services(self) -> list[str]:
        """Ask the server which gRPC services it advertises.

        Uses ``grpc.reflection.v1alpha.ServerReflection``. Requires the engine
        to be built with reflection enabled (default in the v0.2.0+ LuckyEngine
        server). The standard reflection service itself is filtered out of the
        result.
        """
        from . import reflection as _reflection

        return _reflection.list_services(self.channel)

    # ── Camera configuration ──

    def configure_cameras(self, cameras: list[dict]) -> None:
        """Configure cameras to capture on every Step RPC.

        Args:
            cameras: List of camera configs. Each dict has keys:
                name: Camera entity name in the scene.
                width: Desired image width (0 = native resolution).
                height: Desired image height (0 = native resolution).
        """
        self._camera_requests = [
            self.pb.agent.GetCameraFrameRequest(
                name=c["name"],
                width=c.get("width", 0),
                height=c.get("height", 0),
            )
            for c in cameras
        ]

    def list_cameras(self, timeout: float | None = None) -> list[dict]:
        """List available cameras in the scene.

        Returns:
            List of dicts with 'name' and 'id' keys for each camera.
        """
        timeout = timeout or self.timeout
        resp = self.camera.ListCameras(
            camera_pb2.ListCamerasRequest(),
            timeout=timeout,
        )
        return [
            {"name": c.name, "id": c.id.id}
            for c in resp.cameras
        ]

    # ── Multi-policy action groups ──

    def set_action_group(
        self,
        group_name: str,
        actions: list[float],
        action_indices: list[int],
        agent_name: str = "",
        timeout: float | None = None,
    ) -> bool:
        """Preload actions for a named group without triggering a physics step.

        Call this for each policy/controller, then call step() to fire them
        all atomically in one physics tick.

        Args:
            group_name: Name for this action group (e.g., "lower_body", "right_arm").
            actions: Action values for this group.
            action_indices: Which indices in the action vector these map to.
            agent_name: Agent name (empty = default agent).
            timeout: RPC timeout in seconds.

        Returns:
            True if the group was preloaded successfully.
        """
        timeout = timeout or self.timeout
        resp = self.agent.SetActionGroup(
            self.pb.agent.SetActionGroupRequest(
                agent_name=agent_name,
                group=self.pb.agent.ActionGroupEntry(
                    group_name=group_name,
                    actions=actions,
                    action_indices=action_indices,
                ),
            ),
            timeout=timeout,
        )
        if not resp.success:
            logger.warning("SetActionGroup failed: %s", resp.message)
        return resp.success

    # ── MujocoService RPCs ──

    def get_joint_state(self, robot_name: str = "", timeout: Optional[float] = None):
        """Get current joint state (positions and velocities).

        Args:
            robot_name: Robot entity name (uses default if empty).
            timeout: RPC timeout in seconds.

        Returns:
            GetJointStateResponse with state.positions (qpos) and
            state.velocities (qvel).
        """
        timeout = timeout or self.timeout
        robot_name = robot_name or self._robot_name
        if not robot_name:
            raise ValueError("robot_name is required")
        return self.mujoco.GetJointState(
            self.pb.mujoco.GetJointStateRequest(robot_name=robot_name),
            timeout=timeout,
        )

    def get_mujoco_info(self, robot_name: str = "", timeout: Optional[float] = None):
        """Get MuJoCo model information (joint names, limits, etc.)."""
        timeout = timeout or self.timeout
        robot_name = robot_name or self._robot_name
        if not robot_name:
            raise ValueError("robot_name is required")
        return self.mujoco.GetMujocoInfo(
            self.pb.mujoco.GetMujocoInfoRequest(robot_name=robot_name),
            timeout=timeout,
        )

    # ── MujocoSceneService RPCs (engine-wide, not agent-scoped) ──

    def get_model_info(self, timeout: Optional[float] = None):
        """Introspect the full loaded MuJoCo model.

        Returns a ``GetModelInfoResponse`` whose ``joints`` and ``actuators``
        lists cover every entry in ``mjModel`` — not just those declared by
        the registered RL agent. Use this to discover fingers, non-agent
        joints, and actuator names the agent API doesn't expose.
        """
        timeout = timeout or self.timeout
        return self.mujoco_scene.GetModelInfo(
            self.pb.mujoco_scene.GetModelInfoRequest(),
            timeout=timeout,
        )

    def get_full_state(
        self,
        *,
        include_qpos: bool = True,
        include_qvel: bool = True,
        include_ctrl: bool = True,
        timeout: Optional[float] = None,
    ):
        """Snapshot the complete mjData state (qpos, qvel, ctrl, time)."""
        timeout = timeout or self.timeout
        return self.mujoco_scene.GetFullState(
            self.pb.mujoco_scene.GetFullStateRequest(
                include_qpos=include_qpos,
                include_qvel=include_qvel,
                include_ctrl=include_ctrl,
            ),
            timeout=timeout,
        )

    def stream_full_state(
        self,
        *,
        target_fps: int = 30,
        include_qpos: bool = True,
        include_qvel: bool = True,
        include_ctrl: bool = True,
    ):
        """Iterate ``GetFullStateResponse`` messages at approximately ``target_fps``.

        Example:
            for resp in client.stream_full_state(target_fps=60):
                qpos = list(resp.state.qpos)
        """
        return self.mujoco_scene.StreamFullState(
            self.pb.mujoco_scene.StreamFullStateRequest(
                target_fps=target_fps,
                include_qpos=include_qpos,
                include_qvel=include_qvel,
                include_ctrl=include_ctrl,
            )
        )

    def set_ctrl(
        self,
        values: Any,
        *,
        skip_range_clamp: bool = False,
        wait_for_next_step: bool = False,
        timeout: Optional[float] = None,
    ):
        """Write actuator control values.

        Accepts three input shapes:
            - A flat sequence of floats: bulk write starting at index 0.
            - A dict[str, float]: write by actuator name.
            - A dict[int, float]: write by actuator index.

        Actuators currently owned by an active RL agent are refused and
        returned in ``SetControlResponse.rejected_actuators``.
        """
        timeout = timeout or self.timeout

        req_kwargs: dict[str, Any] = {
            "skip_range_clamp": skip_range_clamp,
            "wait_for_next_step": wait_for_next_step,
        }

        if isinstance(values, dict):
            named: list = []
            indexed: list = []
            for k, v in values.items():
                if isinstance(k, str):
                    named.append(
                        self.pb.mujoco_scene.NamedControlEntry(actuator_name=k, value=float(v))
                    )
                elif isinstance(k, int):
                    indexed.append(
                        self.pb.mujoco_scene.IndexedControlEntry(actuator_index=int(k), value=float(v))
                    )
                else:
                    raise TypeError(
                        f"set_ctrl dict keys must be str or int; got {type(k).__name__}"
                    )
            if named:
                req_kwargs["named"] = named
            if indexed:
                req_kwargs["indexed"] = indexed
        else:
            req_kwargs["bulk"] = [float(v) for v in values]

        return self.mujoco_scene.SetControl(
            self.pb.mujoco_scene.SetControlRequest(**req_kwargs),
            timeout=timeout,
        )

    def list_all_joints(self, timeout: Optional[float] = None) -> list[dict]:
        """Return lightweight dicts for every joint in the loaded MuJoCo model.

        Convenience wrapper around :meth:`get_model_info`. Each entry:
            {"index": int, "name": str, "type": int, "qpos_adr": int,
             "qvel_adr": int, "limited": bool, "range": (lo, hi)}
        """
        info = self.get_model_info(timeout=timeout)
        return [
            {
                "index": j.index,
                "name": j.name,
                "type": int(j.type),
                "qpos_adr": j.qpos_adr,
                "qvel_adr": j.qvel_adr,
                "limited": j.limited,
                "range": (j.range_lo, j.range_hi),
            }
            for j in info.joints
        ]

    def list_all_actuators(self, timeout: Optional[float] = None) -> list[dict]:
        """Return lightweight dicts for every actuator in the loaded MuJoCo model."""
        info = self.get_model_info(timeout=timeout)
        return [
            {
                "index": a.index,
                "name": a.name,
                "ctrl_limited": a.ctrl_limited,
                "ctrl_range": (a.ctrl_range_lo, a.ctrl_range_hi),
                "target_joint_index": a.target_joint_index,
            }
            for a in info.actuators
        ]

    # ── AgentService RPCs ──

    def get_agent_schema(self, agent_name: str = "", timeout: Optional[float] = None):
        """Get agent schema (observation/action sizes and names).

        The schema is cached for subsequent step() calls to enable
        named access to observation values.

        Args:
            agent_name: Agent name (empty = default agent).
            timeout: RPC timeout.

        Returns:
            GetAgentSchemaResponse with schema containing observation_names,
            action_names, observation_size, and action_size.
        """
        timeout = timeout or self.timeout
        resp = self.agent.GetAgentSchema(
            self.pb.agent.GetAgentSchemaRequest(agent_name=agent_name),
            timeout=timeout,
        )

        # Cache the schema for named observation access
        schema = getattr(resp, "schema", None)
        if schema is not None:
            cache_key = agent_name or "agent_0"
            obs_names = list(schema.observation_names) if schema.observation_names else []
            action_names = list(schema.action_names) if schema.action_names else []
            self._schema_cache[cache_key] = (obs_names, action_names)
            logger.debug(
                "Cached schema for %s: %d obs names, %d action names",
                cache_key,
                len(obs_names),
                len(action_names),
            )

        return resp

    def reset_agent(
        self,
        agent_name: str = "",
        randomization_cfg: Optional[Any] = None,
        timeout: Optional[float] = None,
    ):
        """
        Reset a specific agent.

        Args:
            agent_name: Agent logical name. Empty string means default agent.
            randomization_cfg: Optional simulation contract config for this reset.
            timeout: Timeout in seconds (uses default if None).

        Returns:
            ResetAgentResponse with success and message fields.
        """
        timeout = timeout or self.timeout

        request_kwargs = {"agent_name": agent_name}

        if randomization_cfg is not None:
            contract = sim_contract.to_proto(self.pb.agent, randomization_cfg)
            request_kwargs["simulation_contract"] = contract

        return self.agent.ResetAgent(
            self.pb.agent.ResetAgentRequest(**request_kwargs),
            timeout=timeout,
        )

    def step(
        self,
        actions: list[float] | None = None,
        agent_name: str = "",
        step_timeout_s: float = 0.0,
        timeout: Optional[float] = None,
        action_groups: list[dict] | None = None,
    ) -> ObservationResponse:
        """
        Synchronous RL step: apply action, wait for physics, return observation.

        Args:
            actions: Action vector to apply for this step (optional when using action_groups).
            agent_name: Agent name (empty = default agent).
            step_timeout_s: Server-side timeout for waiting for the physics step (seconds).
                0 means use server default.
            timeout: RPC timeout in seconds.
            action_groups: Optional list of action group dicts, each with keys:
                group_name: str, actions: list[float], action_indices: list[int].
                Groups are applied on top of actions (if provided) or default positions.

        Returns:
            ObservationResponse with observation after physics step.
        """
        timeout = timeout or self.timeout

        # Build inline action groups if provided
        proto_groups = []
        if action_groups:
            for g in action_groups:
                gname = g.get("group_name", "")
                gactions = g.get("actions", [])
                gindices = g.get("action_indices", [])
                if not gname or not gactions or not gindices:
                    logger.warning(
                        "Skipping invalid action group (missing group_name, actions, or action_indices): %s",
                        g,
                    )
                    continue
                proto_groups.append(
                    self.pb.agent.ActionGroupEntry(
                        group_name=gname,
                        actions=gactions,
                        action_indices=gindices,
                    )
                )

        try:
            resp = self.agent.Step(
                self.pb.agent.StepRequest(
                    agent_name=agent_name,
                    actions=actions or [],
                    timeout_s=step_timeout_s,
                    camera_requests=self._camera_requests,
                    action_groups=proto_groups,
                ),
                timeout=timeout,
            )
        except grpc.RpcError as e:
            if e.code() == grpc.StatusCode.DEADLINE_EXCEEDED:
                raise RuntimeError(
                    f"Client-side gRPC timeout ({timeout}s): the server did not respond in time. "
                    "This usually means the engine is frozen or the network is unreachable."
                ) from e
            raise

        if not resp.success:
            raise RuntimeError(
                f"Server-side physics timeout: {resp.message} "
                f"(server waited up to its configured timeout for the physics step to complete)"
            )

        agent_frame = resp.observation
        observations = list(agent_frame.observations) if agent_frame.observations else []
        actions_out = list(agent_frame.actions) if agent_frame.actions else []
        timestamp_ms = getattr(agent_frame, "timestamp_ms", 0)
        frame_number = getattr(agent_frame, "frame_number", 0)

        cache_key = agent_name or "agent_0"
        obs_names, action_names = self._schema_cache.get(cache_key, (None, None))

        camera_frames = [
            CameraFrame(
                name=nf.name,
                data=bytes(nf.frame.data),
                width=nf.frame.width,
                height=nf.frame.height,
                channels=nf.frame.channels,
                frame_number=nf.frame.frame_number,
            )
            for nf in resp.camera_frames
        ]

        # Extract enriched step data if present
        reward_signals = dict(resp.reward_signals) if resp.reward_signals else None
        terminated = resp.terminated
        truncated = resp.truncated
        info = dict(resp.info) if resp.info else None
        termination_flags = dict(resp.termination_flags) if resp.termination_flags else None

        return ObservationResponse(
            observation=observations,
            actions=actions_out,
            timestamp_ms=timestamp_ms,
            frame_number=frame_number,
            agent_name=cache_key,
            observation_names=obs_names,
            action_names=action_names,
            camera_frames=camera_frames,
            reward_signals=reward_signals,
            terminated=terminated,
            truncated=truncated,
            info=info,
            termination_flags=termination_flags,
        )

    # ── Progress reporting ──

    def report_progress(
        self,
        *,
        run_id: str = "",
        task_name: str = "",
        policy_name: str = "",
        phase: str = "",
        current_episode: int = 0,
        total_episodes: int = 0,
        current_step: int = 0,
        max_steps: int = 0,
        elapsed_s: float = 0.0,
        status_text: str = "",
        finished: bool = False,
    ) -> None:
        """Report evaluation/training progress to the engine for UI display.

        Fire-and-forget: errors are logged but never raised.
        """
        try:
            self.agent.ReportProgress(
                self.pb.agent.ProgressReport(
                    run_id=run_id,
                    task_name=task_name,
                    policy_name=policy_name,
                    phase=phase,
                    current_episode=current_episode,
                    total_episodes=total_episodes,
                    current_step=current_step,
                    max_steps=max_steps,
                    elapsed_s=elapsed_s,
                    status_text=status_text,
                    finished=finished,
                ),
                timeout=1.0,
            )
        except Exception as e:
            logger.debug("report_progress failed (non-fatal): %s", e)

    # ── Task Contract RPCs ──

    def get_capability_manifest(
        self,
        robot_name: str = "",
        scene: str = "",
        timeout: Optional[float] = None,
    ) -> dict:
        """Discover what MDP components the engine supports.

        Args:
            robot_name: Filter by robot (empty = all).
            scene: Filter by scene (empty = all).
            timeout: RPC timeout in seconds.

        Returns:
            Dict with observations, rewards, terminations, randomizations lists.
        """
        timeout = timeout or self.timeout
        resp = self.agent.GetCapabilityManifest(
            self.pb.agent.GetCapabilityManifestRequest(
                robot_name=robot_name,
                scene=scene,
            ),
            timeout=timeout,
        )
        manifest = resp.manifest
        return {
            "engine_version": manifest.engine_version,
            "manifest_version": manifest.manifest_version,
            "observations": [
                {"name": d.name, "description": d.description, "category": d.category}
                for d in manifest.observations
            ],
            "rewards": [
                {"name": d.name, "description": d.description, "category": d.category}
                for d in manifest.rewards
            ],
            "terminations": [
                {"name": d.name, "description": d.description, "category": d.category}
                for d in manifest.terminations
            ],
            "randomizations": [
                {
                    "name": d.base.name,
                    "description": d.base.description,
                    "default_range": (d.default_range_min, d.default_range_max),
                    "engine_target": d.engine_target,
                }
                for d in manifest.randomizations
            ],
        }

    def negotiate_task(
        self,
        contract: dict,
        timeout: Optional[float] = None,
    ) -> dict:
        """Validate and configure engine for a task contract.

        Args:
            contract: Task contract dict with observations, rewards, terminations, etc.
            timeout: RPC timeout in seconds.

        Returns:
            Dict with session_id, reward_terms, termination_terms on success.

        Raises:
            RuntimeError: If contract validation fails.
        """
        timeout = timeout or self.timeout

        # Build protobuf contract from dict
        proto_contract = self._build_task_contract(contract)

        resp = self.agent.NegotiateTask(
            self.pb.agent.NegotiateTaskRequest(contract=proto_contract),
            timeout=timeout,
        )

        if not resp.success:
            raise RuntimeError(f"Task contract negotiation failed: {resp.message}")

        result = {
            "session_id": resp.session.session_id if resp.session else "",
            "reward_terms": list(resp.session.reward_terms) if resp.session else [],
            "termination_terms": list(resp.session.termination_terms) if resp.session else [],
        }

        # Include warnings if any
        if resp.validation and resp.validation.warnings:
            result["warnings"] = [
                {
                    "component": w.component,
                    "term_name": w.term_name,
                    "message": w.message,
                    "suggestion": w.suggestion,
                }
                for w in resp.validation.warnings
            ]

        return result

    def _build_task_contract(self, contract: dict):
        """Convert a Python dict to a TaskContract protobuf message."""
        pb = self.pb.agent

        # Build observation contract
        obs_contract = None
        if "observations" in contract:
            obs = contract["observations"]
            required = [
                pb.ObservationTermRequest(
                    name=t["name"],
                    params=t.get("params", {}),
                    group=t.get("group", "policy"),
                )
                for t in obs.get("required", [])
            ]
            optional = [
                pb.ObservationTermRequest(
                    name=t["name"],
                    params=t.get("params", {}),
                    group=t.get("group", "policy"),
                )
                for t in obs.get("optional", [])
            ]
            obs_contract = pb.ObservationContract(required=required, optional=optional)

        # Build reward contract
        reward_contract = None
        if "rewards" in contract:
            rew = contract["rewards"]
            engine_terms = [
                pb.RewardTermRequest(
                    name=t["name"],
                    weight=t.get("weight", 1.0),
                    params=t.get("params", {}),
                )
                for t in rew.get("engine_terms", [])
            ]
            reward_contract = pb.RewardContract(
                engine_terms=engine_terms,
                python_terms=rew.get("python_terms", []),
            )

        # Build termination contract
        term_contract = None
        if "terminations" in contract:
            terms = [
                pb.TerminationTermRequest(
                    name=t["name"],
                    is_timeout=t.get("is_timeout", False),
                    params=t.get("params", {}),
                )
                for t in contract["terminations"].get("terms", [])
            ]
            term_contract = pb.TerminationContract(terms=terms)

        # Build action contract
        action_contract = None
        if "actions" in contract:
            act = contract["actions"]
            action_terms = [
                pb.ActionTermRequest(
                    type=t["type"],
                    joint_pattern=t.get("joint_pattern", "*"),
                    params=t.get("params", {}),
                    group=t.get("group", ""),
                )
                for t in act.get("terms", [])
            ]
            action_contract = pb.ActionContract(terms=action_terms)

        # Build randomization contract
        rand_contract = None
        if "randomization" in contract:
            rand = contract["randomization"]
            custom_rands = [
                pb.CustomRandomization(
                    name=r["name"],
                    range_min=r.get("range_min", 0.0),
                    range_max=r.get("range_max", 1.0),
                    target=r.get("target", ""),
                )
                for r in rand.get("custom_randomizations", [])
            ]
            rand_contract = pb.RandomizationContract(
                custom_randomizations=custom_rands,
            )

        # Build auxiliary data requests
        aux_data = []
        if "auxiliary_data" in contract:
            aux_data = [
                pb.AuxiliaryDataRequest(
                    name=a["name"],
                    params=a.get("params", {}),
                )
                for a in contract["auxiliary_data"]
            ]

        return pb.TaskContract(
            task_id=contract.get("task_id", ""),
            robot=contract.get("robot", ""),
            scene=contract.get("scene", ""),
            observations=obs_contract,
            actions=action_contract,
            rewards=reward_contract,
            terminations=term_contract,
            randomization=rand_contract,
            auxiliary_data=aux_data,
        )

    # ── SceneService RPCs ──

    def set_simulation_mode(
        self,
        mode: str = "fast",
        timeout: Optional[float] = None,
    ):
        """
        Set simulation timing mode.

        Args:
            mode: "realtime", "deterministic", or "fast"
                - realtime: Physics runs at 1x wall-clock speed
                - deterministic: Physics runs at fixed rate
                - fast: Physics runs as fast as possible (for RL training)
            timeout: RPC timeout in seconds.

        Returns:
            SetSimulationModeResponse with success and current mode.
        """
        timeout = timeout or self.timeout

        mode_map = {
            "realtime": 0,
            "deterministic": 1,
            "fast": 2,
        }
        mode_value = mode_map.get(mode.lower(), 2)

        return self.scene.SetSimulationMode(
            self.pb.scene.SetSimulationModeRequest(mode=mode_value),
            timeout=timeout,
        )

    # ── Benchmarking ──

    def benchmark(
        self,
        duration_seconds: float = 5.0,
        method: str = "step",
        print_results: bool = False,
    ) -> BenchmarkResult:
        """Benchmark a client method by calling it in a tight loop.

        Args:
            duration_seconds: How long to run the benchmark.
            method: Method to benchmark. Currently supports "step".
            print_results: Print results to stdout.

        Returns:
            BenchmarkResult with timing statistics.

        Raises:
            ValueError: If method is not recognized.
        """
        if method == "step":
            # Use zero actions for benchmarking
            call_fn = lambda: self.step(actions=[0.0] * 12)
        else:
            raise ValueError(
                f"Unknown method '{method}'. Supported: 'step'"
            )

        latencies: list[float] = []
        start = time.perf_counter()
        deadline = start + duration_seconds

        while time.perf_counter() < deadline:
            t0 = time.perf_counter()
            call_fn()
            t1 = time.perf_counter()
            latencies.append((t1 - t0) * 1000.0)  # ms

        elapsed = time.perf_counter() - start
        count = len(latencies)

        if count == 0:
            result = BenchmarkResult(
                method=method,
                duration_seconds=elapsed,
                frame_count=0,
                actual_fps=0.0,
                avg_latency_ms=0.0,
                min_latency_ms=0.0,
                max_latency_ms=0.0,
                std_latency_ms=0.0,
                p50_latency_ms=0.0,
                p99_latency_ms=0.0,
            )
        else:
            sorted_lat = sorted(latencies)
            p50_idx = int(math.floor(0.50 * (count - 1)))
            p99_idx = int(math.floor(0.99 * (count - 1)))

            result = BenchmarkResult(
                method=method,
                duration_seconds=elapsed,
                frame_count=count,
                actual_fps=count / elapsed if elapsed > 0 else 0.0,
                avg_latency_ms=statistics.mean(latencies),
                min_latency_ms=sorted_lat[0],
                max_latency_ms=sorted_lat[-1],
                std_latency_ms=statistics.stdev(latencies) if count > 1 else 0.0,
                p50_latency_ms=sorted_lat[p50_idx],
                p99_latency_ms=sorted_lat[p99_idx],
            )

        if print_results:
            print(f"\n--- Benchmark: {method} ({elapsed:.1f}s) ---")
            print(f"  Frames: {result.frame_count}")
            print(f"  FPS:    {result.actual_fps:.1f}")
            print(f"  Avg:    {result.avg_latency_ms:.2f} ms")
            print(f"  Min:    {result.min_latency_ms:.2f} ms")
            print(f"  Max:    {result.max_latency_ms:.2f} ms")
            print(f"  Std:    {result.std_latency_ms:.2f} ms")
            print(f"  P50:    {result.p50_latency_ms:.2f} ms")
            print(f"  P99:    {result.p99_latency_ms:.2f} ms")

        return result
