"""
LuckyEngine gRPC client.

Uses checked-in Python stubs generated from the `.proto` files under
`src/luckyrobots/grpc/proto/`.
"""

from __future__ import annotations

import logging
import time
from types import SimpleNamespace
from typing import Any, Optional

import grpc  # type: ignore

logger = logging.getLogger("luckyrobots.client")

try:
    from .grpc.generated import agent_pb2  # type: ignore
    from .grpc.generated import agent_pb2_grpc  # type: ignore
    from .grpc.generated import common_pb2  # type: ignore
    from .grpc.generated import debug_pb2  # type: ignore
    from .grpc.generated import debug_pb2_grpc  # type: ignore
    from .grpc.generated import mujoco_pb2  # type: ignore
    from .grpc.generated import mujoco_pb2_grpc  # type: ignore
    from .grpc.generated import scene_pb2  # type: ignore
    from .grpc.generated import scene_pb2_grpc  # type: ignore
except Exception as e:  # pragma: no cover
    raise ImportError(
        "Missing generated gRPC stubs. Regenerate them from the protos in "
        "src/luckyrobots/grpc/proto into src/luckyrobots/grpc/generated."
    ) from e

from .models import ObservationResponse


class GrpcConnectionError(Exception):
    """Raised when gRPC connection fails."""

    def __init__(self, message: str):
        super().__init__(message)
        logger.warning("gRPC connection error: %s", message)


class LuckyEngineClient:
    """
    Client for connecting to the LuckyEngine gRPC server.

    Provides access to gRPC services for RL training:
    - AgentService: observations, stepping, resets
    - SceneService: simulation mode control
    - MujocoService: health checks

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

        # Service stubs (populated after connect)
        self._scene = None
        self._mujoco = None
        self._agent = None
        self._debug = None

        # Cached agent schemas: agent_name -> (observation_names, action_names)
        self._schema_cache: dict[str, tuple[list[str], list[str]]] = {}

        # Protobuf modules (for discoverability + explicit imports).
        self._pb = SimpleNamespace(
            common=common_pb2,
            scene=scene_pb2,
            mujoco=mujoco_pb2,
            agent=agent_pb2,
            debug=debug_pb2,
        )

    def connect(self) -> None:
        """
        Connect to the LuckyEngine gRPC server.

        Raises:
            GrpcConnectionError: If connection fails.
        """
        target = f"{self.host}:{self.port}"
        logger.info(f"Connecting to LuckyEngine gRPC server at {target}")

        self._channel = grpc.insecure_channel(target)

        # Create service stubs
        self._scene = scene_pb2_grpc.SceneServiceStub(self._channel)
        self._mujoco = mujoco_pb2_grpc.MujocoServiceStub(self._channel)
        self._agent = agent_pb2_grpc.AgentServiceStub(self._channel)
        self._debug = debug_pb2_grpc.DebugServiceStub(self._channel)

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
            self._agent = None
            self._debug = None
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

            if self.health_check(timeout=10.0):
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
    def scene(self) -> Any:
        """SceneService stub."""
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
    def agent(self) -> Any:
        """AgentService stub."""
        if self._agent is None:
            raise GrpcConnectionError("Not connected. Call connect() first.")
        return self._agent

    @property
    def debug(self) -> Any:
        """DebugService stub."""
        if self._debug is None:
            raise GrpcConnectionError("Not connected. Call connect() first.")
        return self._debug

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

    def get_observation(
        self,
        agent_name: str = "",
        timeout: Optional[float] = None,
    ) -> ObservationResponse:
        """
        Get the RL observation vector for an agent.

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

        resp = self.agent.GetObservation(
            self.pb.agent.GetObservationRequest(
                robot_name=resolved_robot_name,
                agent_name=agent_name,
                include_joint_state=False,
                include_agent_frame=True,
                include_telemetry=False,
            ),
            timeout=timeout,
        )

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
            randomization_cfg: Optional domain randomization config for this reset.
            timeout: Timeout in seconds (uses default if None).

        Returns:
            ResetAgentResponse with success and message fields.
        """
        timeout = timeout or self.timeout

        request_kwargs = {"agent_name": agent_name}

        if randomization_cfg is not None:
            randomization_proto = self._randomization_to_proto(randomization_cfg)
            request_kwargs["dr_config"] = randomization_proto

        return self.agent.ResetAgent(
            self.pb.agent.ResetAgentRequest(**request_kwargs),
            timeout=timeout,
        )

    def step(
        self,
        actions: list[float],
        agent_name: str = "",
        step_timeout_s: float = 0.0,
        timeout: Optional[float] = None,
    ) -> ObservationResponse:
        """
        Synchronous RL step: apply action, wait for physics, return observation.

        Args:
            actions: Action vector to apply for this step.
            agent_name: Agent name (empty = default agent).
            step_timeout_s: Server-side timeout for waiting for the physics step (seconds).
                0 means use server default.
            timeout: RPC timeout in seconds.

        Returns:
            ObservationResponse with observation after physics step.
        """
        timeout = timeout or self.timeout

        try:
            resp = self.agent.Step(
                self.pb.agent.StepRequest(
                    agent_name=agent_name,
                    actions=actions,
                    timeout_s=step_timeout_s,
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

        return ObservationResponse(
            observation=observations,
            actions=actions_out,
            timestamp_ms=timestamp_ms,
            frame_number=frame_number,
            agent_name=cache_key,
            observation_names=obs_names,
            action_names=action_names,
        )

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

    def _randomization_to_proto(self, randomization_cfg: Any):
        """Convert domain randomization config to proto message."""
        proto_kwargs = {}

        def get_val(name: str, default=None):
            val = getattr(randomization_cfg, name, default)
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

        # Physics parameters
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

    def draw_velocity_command(
        self,
        origin: tuple[float, float, float],
        lin_vel_x: float,
        lin_vel_y: float,
        ang_vel_z: float,
        scale: float = 1.0,
        clear_previous: bool = True,
        timeout: Optional[float] = None,
    ) -> bool:
        """
        Draw velocity command visualization in LuckyEngine.

        Args:
            origin: (x, y, z) position of the robot.
            lin_vel_x: Forward velocity command.
            lin_vel_y: Lateral velocity command.
            ang_vel_z: Angular velocity command (yaw rate).
            scale: Scale factor for visualization.
            clear_previous: Clear previous debug draws before drawing.
            timeout: RPC timeout in seconds.

        Returns:
            True if draw succeeded, False otherwise.
        """
        timeout = timeout or self.timeout

        velocity_cmd = self.pb.debug.DebugVelocityCommand(
            origin=self.pb.debug.DebugVector3(x=origin[0], y=origin[1], z=origin[2]),
            lin_vel_x=lin_vel_x,
            lin_vel_y=lin_vel_y,
            ang_vel_z=ang_vel_z,
            scale=scale,
        )

        request = self.pb.debug.DebugDrawRequest(
            velocity_command=velocity_cmd,
            clear_previous=clear_previous,
        )

        try:
            resp = self.debug.Draw(request, timeout=timeout)
            return resp.success
        except Exception as e:
            logger.debug(f"Debug draw failed: {e}")
            return False

    def draw_arrow(
        self,
        origin: tuple[float, float, float],
        direction: tuple[float, float, float],
        color: tuple[float, float, float, float] = (1.0, 0.0, 0.0, 1.0),
        scale: float = 1.0,
        clear_previous: bool = False,
        timeout: Optional[float] = None,
    ) -> bool:
        """
        Draw a debug arrow in LuckyEngine.

        Args:
            origin: (x, y, z) start position.
            direction: (x, y, z) direction and magnitude.
            color: (r, g, b, a) color values (0-1 range).
            scale: Scale factor for visualization.
            clear_previous: Clear previous debug draws before drawing.
            timeout: RPC timeout in seconds.

        Returns:
            True if draw succeeded, False otherwise.
        """
        timeout = timeout or self.timeout

        arrow = self.pb.debug.DebugArrow(
            origin=self.pb.debug.DebugVector3(x=origin[0], y=origin[1], z=origin[2]),
            direction=self.pb.debug.DebugVector3(
                x=direction[0], y=direction[1], z=direction[2]
            ),
            color=self.pb.debug.DebugColor(
                r=color[0], g=color[1], b=color[2], a=color[3]
            ),
            scale=scale,
        )

        request = self.pb.debug.DebugDrawRequest(
            arrows=[arrow],
            clear_previous=clear_previous,
        )

        try:
            resp = self.debug.Draw(request, timeout=timeout)
            return resp.success
        except Exception as e:
            logger.debug(f"Debug draw failed: {e}")
            return False

    def draw_line(
        self,
        start: tuple[float, float, float],
        end: tuple[float, float, float],
        color: tuple[float, float, float, float] = (1.0, 1.0, 1.0, 1.0),
        clear_previous: bool = False,
        timeout: Optional[float] = None,
    ) -> bool:
        """
        Draw a debug line in LuckyEngine.

        Args:
            start: (x, y, z) start position.
            end: (x, y, z) end position.
            color: (r, g, b, a) color values (0-1 range).
            clear_previous: Clear previous debug draws before drawing.
            timeout: RPC timeout in seconds.

        Returns:
            True if draw succeeded, False otherwise.
        """
        timeout = timeout or self.timeout

        line = self.pb.debug.DebugLine(
            start=self.pb.debug.DebugVector3(x=start[0], y=start[1], z=start[2]),
            end=self.pb.debug.DebugVector3(x=end[0], y=end[1], z=end[2]),
            color=self.pb.debug.DebugColor(
                r=color[0], g=color[1], b=color[2], a=color[3]
            ),
        )

        request = self.pb.debug.DebugDrawRequest(
            lines=[line],
            clear_previous=clear_previous,
        )

        try:
            resp = self.debug.Draw(request, timeout=timeout)
            return resp.success
        except Exception as e:
            logger.debug(f"Debug draw failed: {e}")
            return False
