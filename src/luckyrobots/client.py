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
