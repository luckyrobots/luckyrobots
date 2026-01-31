"""
LuckyEngine gRPC client.

Uses checked-in Python stubs generated from the `.proto` files under
`src/luckyrobots/grpc/proto/`.
"""

from __future__ import annotations

import logging
import time
import statistics
from dataclasses import dataclass
from types import SimpleNamespace
from typing import Any, Optional

logger = logging.getLogger("luckyrobots.client")

try:
    from .grpc.generated import agent_pb2  # type: ignore
    from .grpc.generated import agent_pb2_grpc  # type: ignore
    from .grpc.generated import camera_pb2  # type: ignore
    from .grpc.generated import camera_pb2_grpc  # type: ignore
    from .grpc.generated import common_pb2  # type: ignore
    from .grpc.generated import media_pb2  # type: ignore
    from .grpc.generated import mujoco_pb2  # type: ignore
    from .grpc.generated import mujoco_pb2_grpc  # type: ignore
    from .grpc.generated import scene_pb2  # type: ignore
    from .grpc.generated import scene_pb2_grpc  # type: ignore
    from .grpc.generated import telemetry_pb2  # type: ignore
    from .grpc.generated import telemetry_pb2_grpc  # type: ignore
    from .grpc.generated import viewport_pb2  # type: ignore
    from .grpc.generated import viewport_pb2_grpc  # type: ignore
except Exception as e:  # pragma: no cover
    raise ImportError(
        "Missing generated gRPC stubs. Regenerate them from the protos in "
        "src/luckyrobots/grpc/proto into src/luckyrobots/grpc/generated."
    ) from e

# Import Pydantic models for type-checked responses
from .models import ObservationResponse, StateSnapshot, DomainRandomizationConfig


class GrpcConnectionError(Exception):
    """Raised when gRPC connection fails."""

    def __init__(self, message: str):
        super().__init__(message)
        logger.warning("gRPC connection error: %s", message)


class LuckyEngineClient:
    """
    Client for connecting to the LuckyEngine gRPC server.

    Provides access to all gRPC services defined by the protos under
    `src/luckyrobots/rpc/proto`:
    - SceneService
    - MujocoService
    - TelemetryService
    - AgentService
    - ViewportService
    - CameraService

    Usage:
        client = LuckyEngineClient(host="127.0.0.1", port=50051)
        client.connect()

        # Access services
        scene_info = client.scene.GetSceneInfo(client.pb.scene.GetSceneInfoRequest())
        joint_state = client.mujoco.GetJointState(
            client.pb.mujoco.GetJointStateRequest()
        )

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

        # Service stubs (populated after connect)
        self._scene = None
        self._mujoco = None
        self._telemetry = None
        self._agent = None
        self._viewport = None
        self._camera = None

        # Cached agent schemas: agent_name -> (observation_names, action_names)
        # Populated lazily by get_agent_schema() or fetch_schema()
        self._schema_cache: dict[str, tuple[list[str], list[str]]] = {}

        # Protobuf modules (for discoverability + explicit imports).
        self._pb = SimpleNamespace(
            common=common_pb2,
            media=media_pb2,
            scene=scene_pb2,
            mujoco=mujoco_pb2,
            telemetry=telemetry_pb2,
            agent=agent_pb2,
            viewport=viewport_pb2,
            camera=camera_pb2,
        )

    def connect(self) -> None:
        """
        Connect to the LuckyEngine gRPC server.

        Raises:
            GrpcConnectionError: If connection fails.
        """
        try:
            import grpc  # type: ignore
        except ImportError as e:
            raise RuntimeError(
                "Missing grpcio. Install with: pip install grpcio protobuf"
            ) from e

        target = f"{self.host}:{self.port}"
        logger.info(f"Connecting to LuckyEngine gRPC server at {target}")

        self._channel = grpc.insecure_channel(target)

        # Create service stubs
        self._scene = scene_pb2_grpc.SceneServiceStub(self._channel)
        self._mujoco = mujoco_pb2_grpc.MujocoServiceStub(self._channel)
        self._telemetry = telemetry_pb2_grpc.TelemetryServiceStub(self._channel)
        self._agent = agent_pb2_grpc.AgentServiceStub(self._channel)
        self._viewport = viewport_pb2_grpc.ViewportServiceStub(self._channel)
        self._camera = camera_pb2_grpc.CameraServiceStub(self._channel)

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
            self._telemetry = None
            self._agent = None
            self._viewport = None
            self._camera = None
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
        import time

        start = time.perf_counter()

        while time.perf_counter() - start < timeout:
            if not self.is_connected():
                try:
                    self.connect()
                except Exception:
                    pass

            if self.health_check(timeout=10.0):
                logger.info(f"Connected to LuckyEngine gRPC server at {self.host}:{self.port}")
                return True

            time.sleep(poll_interval)

        return False

    # --- Protobuf modules (discoverable + explicit) ---

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

    # --- Service stubs ---
    #
    # Confirmed working:
    #   - mujoco: GetMujocoInfo, GetJointState, SendControl
    #   - agent: GetObservation, ResetAgent, GetAgentSchema, StreamAgent
    #
    # Placeholders (not yet confirmed working - use at your own risk):
    #   - scene: GetSceneInfo
    #   - telemetry: StreamTelemetry
    #   - viewport: (no methods implemented)
    #   - camera: ListCameras, StreamCamera

    @property
    def scene(self) -> Any:
        """SceneService stub. [PLACEHOLDER - not confirmed working]"""
        if self._scene is None:
            raise GrpcConnectionError("Not connected. Call connect() first.")
        return self._scene

    @property
    def mujoco(self) -> Any:
        """MujocoService stub."""
        if self._mujoco is None:
            raise GrpcConnectionError("Not connected. Call connect() first.")
        return self._mujoco

    @property
    def telemetry(self) -> Any:
        """TelemetryService stub. [PLACEHOLDER - not confirmed working]"""
        if self._telemetry is None:
            raise GrpcConnectionError("Not connected. Call connect() first.")
        return self._telemetry

    @property
    def agent(self) -> Any:
        """AgentService stub."""
        if self._agent is None:
            raise GrpcConnectionError("Not connected. Call connect() first.")
        return self._agent

    @property
    def viewport(self) -> Any:
        """ViewportService stub. [PLACEHOLDER - not confirmed working]"""
        if self._viewport is None:
            raise GrpcConnectionError("Not connected. Call connect() first.")
        return self._viewport

    @property
    def camera(self) -> Any:
        """CameraService stub. [PLACEHOLDER - not confirmed working]"""
        if self._camera is None:
            raise GrpcConnectionError("Not connected. Call connect() first.")
        return self._camera

    # --- Convenience methods ---

    def get_scene_info(self, timeout: Optional[float] = None):
        """Get scene information. [PLACEHOLDER - not confirmed working]"""
        raise NotImplementedError(
            "get_scene_info() is not yet confirmed working. "
            "Remove this check if you want to test it."
        )
        timeout = timeout or self.timeout
        return self.scene.GetSceneInfo(
            self.pb.scene.GetSceneInfoRequest(),
            timeout=timeout,
        )

    def get_mujoco_info(self, robot_name: str = "", timeout: Optional[float] = None):
        """Get MuJoCo model information."""
        timeout = timeout or self.timeout
        robot_name = robot_name or self._robot_name
        if not robot_name:
            raise ValueError(
                "robot_name is required (pass `robot_name=` or set it once via "
                "LuckyEngineClient(robot_name=...) / client.set_robot_name(...))."
            )
        return self.mujoco.GetMujocoInfo(
            self.pb.mujoco.GetMujocoInfoRequest(robot_name=robot_name),
            timeout=timeout,
        )

    def get_joint_state(self, robot_name: str = "", timeout: Optional[float] = None):
        """Get current joint state."""
        timeout = timeout or self.timeout
        robot_name = robot_name or self._robot_name
        if not robot_name:
            raise ValueError(
                "robot_name is required (pass `robot_name=` or set it once via "
                "LuckyEngineClient(robot_name=...) / client.set_robot_name(...))."
            )
        return self.mujoco.GetJointState(
            self.pb.mujoco.GetJointStateRequest(robot_name=robot_name),
            timeout=timeout,
        )

    def send_control(
        self,
        controls: list[float],
        robot_name: str = "",
        timeout: Optional[float] = None,
    ):
        """Send control commands to the robot."""
        timeout = timeout or self.timeout
        robot_name = robot_name or self._robot_name
        if not robot_name:
            raise ValueError(
                "robot_name is required (pass `robot_name=` or set it once via "
                "LuckyEngineClient(robot_name=...) / client.set_robot_name(...))."
            )
        return self.mujoco.SendControl(
            self.pb.mujoco.SendControlRequest(robot_name=robot_name, controls=controls),
            timeout=timeout,
        )

    def get_agent_schema(self, agent_name: str = "", timeout: Optional[float] = None):
        """Get agent schema (observation/action sizes and names).

        The schema is cached for subsequent get_observation() calls to enable
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

    def fetch_schema(self, agent_name: str = "", timeout: Optional[float] = None) -> None:
        """Fetch and cache agent schema for named observation access.

        Call this once before get_observation() to enable accessing observations
        by name (e.g., obs["proj_grav_x"]).

        Args:
            agent_name: Agent name (empty = default agent).
            timeout: RPC timeout.
        """
        self.get_agent_schema(agent_name=agent_name, timeout=timeout)

    def get_observation(
        self,
        agent_name: str = "",
        timeout: Optional[float] = None,
    ) -> ObservationResponse:
        """
        Get the RL observation vector for an agent.

        This returns only the flat observation vector defined by the agent's
        observation spec in LuckyEngine. For sensor data (joints, telemetry,
        cameras), use the dedicated methods.

        Args:
            agent_name: Agent name (empty = default agent).
            timeout: RPC timeout.

        Returns:
            ObservationResponse with observation vector, actions, timestamp.
        """
        timeout = timeout or self.timeout

        resolved_robot_name = self._robot_name
        if not resolved_robot_name:
            raise ValueError(
                "robot_name is required (set it once via "
                "LuckyEngineClient(robot_name=...) / client.set_robot_name(...))."
            )

        # Request only the agent's RL observation (agent_frame in gRPC terms).
        # Joint state and telemetry have their own dedicated methods.
        resp = self.agent.GetObservation(
            self.pb.agent.GetObservationRequest(
                robot_name=resolved_robot_name,
                agent_name=agent_name,
                include_joint_state=False,
                include_agent_frame=True,  # The RL observation vector
                include_telemetry=False,
            ),
            timeout=timeout,
        )

        # Extract observation from agent_frame.
        #
        # In gRPC, the "agent_frame" is the message containing the RL observation
        # data from LuckyEngine's agent system. It includes:
        #   - observations: flat float vector matching the agent's observation spec
        #   - actions: the last action vector sent to the agent (echoed back)
        #   - timestamp_ms: wall-clock time when the observation was captured
        #   - frame_number: monotonic counter for ordering observations
        #
        # This is distinct from joint_state (raw MuJoCo qpos/qvel) and telemetry
        # (debugging data like contact forces, energy, etc).
        agent_frame = getattr(resp, "agent_frame", None)
        observations = []
        actions = []
        timestamp_ms = getattr(resp, "timestamp_ms", 0)
        frame_number = getattr(resp, "frame_number", 0)

        if agent_frame is not None:
            observations = list(agent_frame.observations) if agent_frame.observations else []
            actions = list(agent_frame.actions) if agent_frame.actions else []
            timestamp_ms = getattr(agent_frame, "timestamp_ms", timestamp_ms)
            frame_number = getattr(agent_frame, "frame_number", frame_number)

        # Look up cached schema for named access
        cache_key = agent_name or "agent_0"
        obs_names, action_names = self._schema_cache.get(cache_key, (None, None))

        return ObservationResponse(
            observation=observations,
            actions=actions,
            timestamp_ms=timestamp_ms,
            frame_number=frame_number,
            agent_name=cache_key,
            observation_names=obs_names,
            action_names=action_names,
        )

    def get_state(
        self,
        agent_name: str = "",
        include_observation: bool = True,
        include_joint_state: bool = True,
        camera_names: Optional[list[str]] = None,
        width: int = 0,
        height: int = 0,
        format: str = "raw",
        timeout: Optional[float] = None,
    ) -> StateSnapshot:
        """
        Get a bundled snapshot of multiple data sources.

        Use this for efficiency when you need multiple data types in one call.
        For single data types, prefer the dedicated methods:
        - get_observation() for RL observation vector
        - get_joint_state() for joint positions/velocities
        - stream_telemetry() for telemetry (streaming only)
        - stream_camera() for camera frames (streaming)

        Args:
            agent_name: Agent name (empty = default agent).
            include_observation: Include RL observation vector.
            include_joint_state: Include joint positions/velocities.
            camera_names: List of camera names to include frames from.
            width: Desired width for camera frames (0 = native).
            height: Desired height for camera frames (0 = native).
            format: Image format ("raw" or "jpeg").
            timeout: RPC timeout.

        Returns:
            StateSnapshot with requested data.
        """
        timeout = timeout or self.timeout

        resolved_robot_name = self._robot_name
        if not resolved_robot_name:
            raise ValueError(
                "robot_name is required (set it once via "
                "LuckyEngineClient(robot_name=...) / client.set_robot_name(...))."
            )

        cameras = []
        if camera_names:
            for name in camera_names:
                cameras.append(
                    self.pb.agent.GetCameraFrameRequest(
                        name=name,
                        width=width,
                        height=height,
                        format=format,
                    )
                )

        resp = self.agent.GetObservation(
            self.pb.agent.GetObservationRequest(
                robot_name=resolved_robot_name,
                agent_name=agent_name,
                include_joint_state=include_joint_state,
                include_agent_frame=include_observation,
                include_telemetry=False,  # Telemetry is streaming-only
                cameras=cameras,
            ),
            timeout=timeout,
        )

        # Build ObservationResponse if requested
        obs_response = None
        if include_observation:
            agent_frame = getattr(resp, "agent_frame", None)
            observations = []
            actions = []
            if agent_frame is not None:
                observations = list(agent_frame.observations) if agent_frame.observations else []
                actions = list(agent_frame.actions) if agent_frame.actions else []

            # Look up cached schema for named access
            cache_key = agent_name or "agent_0"
            obs_names, action_names = self._schema_cache.get(cache_key, (None, None))

            obs_response = ObservationResponse(
                observation=observations,
                actions=actions,
                timestamp_ms=getattr(resp, "timestamp_ms", 0),
                frame_number=getattr(resp, "frame_number", 0),
                agent_name=cache_key,
                observation_names=obs_names,
                action_names=action_names,
            )

        return StateSnapshot(
            observation=obs_response,
            joint_state=getattr(resp, "joint_state", None) if include_joint_state else None,
            camera_frames=list(getattr(resp, "camera_frames", [])) if camera_names else None,
            timestamp_ms=getattr(resp, "timestamp_ms", 0),
            frame_number=getattr(resp, "frame_number", 0),
        )

    def stream_agent(self, agent_name: str = "", target_fps: int = 30):
        """
        Start streaming agent observations.

        Returns an iterator of AgentFrame messages.
        """
        return self.agent.StreamAgent(
            self.pb.agent.StreamAgentRequest(
                agent_name=agent_name, target_fps=target_fps
            ),
        )

    def reset_agent(
        self,
        agent_name: str = "",
        randomization_cfg: Optional[Any] = None,
        timeout: Optional[float] = None,
    ):
        """
        Reset a specific agent (full reset: clear buffers, reset state, resample commands, apply MuJoCo state).

        Useful for multi-env RL where individual agents need to be reset without resetting the entire scene.

        Args:
            agent_name: Agent logical name. Convention is `agent_0`, `agent_1`, ...
                Empty string means "default agent" (agent_0).
            randomization_cfg: Optional domain randomization config for this reset.
            timeout: Timeout in seconds (uses default if None).

        Returns:
            ResetAgentResponse with success and message fields.
        """
        timeout = timeout or self.timeout

        # Build request with optional randomization config
        request_kwargs = {"agent_name": agent_name}

        if randomization_cfg is not None:
            randomization_proto = self._randomization_to_proto(randomization_cfg)
            request_kwargs["dr_config"] = randomization_proto

        return self.agent.ResetAgent(
            self.pb.agent.ResetAgentRequest(**request_kwargs),
            timeout=timeout,
        )

    def _randomization_to_proto(self, randomization_cfg: Any):
        """Convert domain randomization config to proto message.

        Accepts any object with randomization config fields (DomainRandomizationConfig,
        PhysicsDRCfg from luckylab, or similar).
        """
        proto_kwargs = {}

        # Helper to get attribute value, checking for None
        def get_val(name: str, default=None):
            val = getattr(randomization_cfg, name, default)
            # Handle both None and empty tuples/lists
            if val is None or (isinstance(val, (tuple, list)) and len(val) == 0):
                return None
            return val

        # Initial state randomization
        pose_pos = get_val("pose_position_noise")
        if pose_pos is not None:
            proto_kwargs["pose_position_noise"] = list(pose_pos)

        pose_ori = get_val("pose_orientation_noise")
        if pose_ori is not None and pose_ori != 0.0:
            proto_kwargs["pose_orientation_noise"] = pose_ori

        joint_pos = get_val("joint_position_noise")
        if joint_pos is not None and joint_pos != 0.0:
            proto_kwargs["joint_position_noise"] = joint_pos

        joint_vel = get_val("joint_velocity_noise")
        if joint_vel is not None and joint_vel != 0.0:
            proto_kwargs["joint_velocity_noise"] = joint_vel

        # Physics parameters (ranges)
        friction = get_val("friction_range")
        if friction is not None:
            proto_kwargs["friction_range"] = list(friction)

        restitution = get_val("restitution_range")
        if restitution is not None:
            proto_kwargs["restitution_range"] = list(restitution)

        mass_scale = get_val("mass_scale_range")
        if mass_scale is not None:
            proto_kwargs["mass_scale_range"] = list(mass_scale)

        com_offset = get_val("com_offset_range")
        if com_offset is not None:
            proto_kwargs["com_offset_range"] = list(com_offset)

        # Motor/actuator
        motor_strength = get_val("motor_strength_range")
        if motor_strength is not None:
            proto_kwargs["motor_strength_range"] = list(motor_strength)

        motor_offset = get_val("motor_offset_range")
        if motor_offset is not None:
            proto_kwargs["motor_offset_range"] = list(motor_offset)

        # External disturbances
        push_interval = get_val("push_interval_range")
        if push_interval is not None:
            proto_kwargs["push_interval_range"] = list(push_interval)

        push_velocity = get_val("push_velocity_range")
        if push_velocity is not None:
            proto_kwargs["push_velocity_range"] = list(push_velocity)

        # Terrain
        terrain_type = get_val("terrain_type")
        if terrain_type is not None and terrain_type != "":
            proto_kwargs["terrain_type"] = terrain_type

        terrain_diff = get_val("terrain_difficulty")
        if terrain_diff is not None and terrain_diff != 0.0:
            proto_kwargs["terrain_difficulty"] = terrain_diff

        return self.pb.agent.DomainRandomizationConfig(**proto_kwargs)

    def stream_telemetry(self, target_fps: int = 30):
        """
        Start streaming telemetry data. [PLACEHOLDER - not confirmed working]

        Returns an iterator of TelemetryFrame messages.
        """
        raise NotImplementedError(
            "stream_telemetry() is not yet confirmed working. "
            "Remove this check if you want to test it."
        )
        return self.telemetry.StreamTelemetry(
            self.pb.telemetry.StreamTelemetryRequest(target_fps=target_fps),
        )

    def list_cameras(self, timeout: Optional[float] = None):
        """List available cameras. [PLACEHOLDER - not confirmed working]"""
        raise NotImplementedError(
            "list_cameras() is not yet confirmed working. "
            "Remove this check if you want to test it."
        )
        timeout = timeout or self.timeout
        return self.camera.ListCameras(
            self.pb.camera.ListCamerasRequest(),
            timeout=timeout,
        )

    def stream_camera(
        self,
        camera_id: Optional[int] = None,
        camera_name: Optional[str] = None,
        target_fps: int = 30,
        width: int = 640,
        height: int = 480,
        format: str = "raw",
    ):
        """
        Start streaming camera frames. [PLACEHOLDER - not confirmed working]

        Args:
            camera_id: Camera entity ID (use either id or name).
            camera_name: Camera name (use either id or name).
            target_fps: Desired frames per second.
            width: Desired width (0 = native).
            height: Desired height (0 = native).
            format: Image format ("raw" or "jpeg").

        Returns an iterator of ImageFrame messages.
        """
        raise NotImplementedError(
            "stream_camera() is not yet confirmed working. "
            "Remove this check if you want to test it."
        )
        if camera_id is not None:
            request = self.pb.camera.StreamCameraRequest(
                id=self.pb.common.EntityId(id=camera_id),
                target_fps=target_fps,
                width=width,
                height=height,
                format=format,
            )
        elif camera_name is not None:
            request = self.pb.camera.StreamCameraRequest(
                name=camera_name,
                target_fps=target_fps,
                width=width,
                height=height,
                format=format,
            )
        else:
            raise ValueError("Either camera_id or camera_name must be provided")

        return self.camera.StreamCamera(request)

    def benchmark(
        self,
        duration_seconds: float = 5.0,
        method: str = "get_observation",
        print_results: bool = True,
    ) -> "BenchmarkResult":
        """
        Benchmark gRPC performance.

        Measures actual FPS and latency for observation calls.

        Args:
            duration_seconds: How long to run the benchmark.
            method: Which method to benchmark ("get_observation" or "stream_agent").
            print_results: Whether to print results to console.

        Returns:
            BenchmarkResult with FPS and latency statistics.
        """
        if method not in ("get_observation", "stream_agent"):
            raise ValueError(f"Unknown method: {method}. Use 'get_observation' or 'stream_agent'.")

        latencies: list[float] = []
        frame_times: list[float] = []
        frame_count = 0
        start_time = time.perf_counter()
        last_frame_time = start_time

        if method == "get_observation":
            while time.perf_counter() - start_time < duration_seconds:
                call_start = time.perf_counter()
                self.get_observation()
                call_end = time.perf_counter()

                latencies.append((call_end - call_start) * 1000)  # ms
                frame_times.append(call_end - last_frame_time)
                last_frame_time = call_end
                frame_count += 1

        elif method == "stream_agent":
            stream = self.stream_agent(target_fps=1000)  # Request max FPS
            for frame in stream:
                now = time.perf_counter()
                if now - start_time >= duration_seconds:
                    break

                frame_times.append(now - last_frame_time)
                last_frame_time = now
                frame_count += 1

        total_time = time.perf_counter() - start_time

        # Calculate statistics
        actual_fps = frame_count / total_time if total_time > 0 else 0

        if len(frame_times) > 1:
            # Remove first frame (warmup)
            frame_times = frame_times[1:]
            fps_from_frames = 1.0 / statistics.mean(frame_times) if frame_times else 0
        else:
            fps_from_frames = actual_fps

        result = BenchmarkResult(
            method=method,
            duration_seconds=total_time,
            frame_count=frame_count,
            actual_fps=actual_fps,
            avg_latency_ms=statistics.mean(latencies) if latencies else 0,
            min_latency_ms=min(latencies) if latencies else 0,
            max_latency_ms=max(latencies) if latencies else 0,
            std_latency_ms=statistics.stdev(latencies) if len(latencies) > 1 else 0,
            p50_latency_ms=statistics.median(latencies) if latencies else 0,
            p99_latency_ms=sorted(latencies)[int(len(latencies) * 0.99)] if latencies else 0,
        )

        if print_results:
            print(f"\n{'=' * 50}")
            print(f"Benchmark Results ({method})")
            print(f"{'=' * 50}")
            print(f"Duration:     {result.duration_seconds:.2f}s")
            print(f"Frames:       {result.frame_count}")
            print(f"Actual FPS:   {result.actual_fps:.1f}")
            if latencies:
                print(f"{'─' * 50}")
                print(f"Latency (ms):")
                print(f"  avg:        {result.avg_latency_ms:.2f}")
                print(f"  min:        {result.min_latency_ms:.2f}")
                print(f"  max:        {result.max_latency_ms:.2f}")
                print(f"  std:        {result.std_latency_ms:.2f}")
                print(f"  p50:        {result.p50_latency_ms:.2f}")
                print(f"  p99:        {result.p99_latency_ms:.2f}")
            print(f"{'=' * 50}\n")

        return result


@dataclass
class BenchmarkResult:
    """Results from a benchmark run."""

    method: str
    duration_seconds: float
    frame_count: int
    actual_fps: float
    avg_latency_ms: float
    min_latency_ms: float
    max_latency_ms: float
    std_latency_ms: float
    p50_latency_ms: float
    p99_latency_ms: float
