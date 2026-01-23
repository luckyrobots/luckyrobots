"""
LuckyEngine gRPC client.

Uses checked-in Python stubs generated from the `.proto` files under
`src/luckyrobots/rpc/proto/`.
"""

from __future__ import annotations

from dataclasses import dataclass
import logging
from types import SimpleNamespace
from typing import Any, Optional

logger = logging.getLogger("luckyrobots.rpc")

try:
    from .generated import agent_pb2  # type: ignore
    from .generated import agent_pb2_grpc  # type: ignore
    from .generated import camera_pb2  # type: ignore
    from .generated import camera_pb2_grpc  # type: ignore
    from .generated import common_pb2  # type: ignore
    from .generated import media_pb2  # type: ignore
    from .generated import mujoco_pb2  # type: ignore
    from .generated import mujoco_pb2_grpc  # type: ignore
    from .generated import scene_pb2  # type: ignore
    from .generated import scene_pb2_grpc  # type: ignore
    from .generated import telemetry_pb2  # type: ignore
    from .generated import telemetry_pb2_grpc  # type: ignore
    from .generated import viewport_pb2  # type: ignore
    from .generated import viewport_pb2_grpc  # type: ignore
except Exception as e:  # pragma: no cover
    raise ImportError(
        "Missing generated gRPC stubs. Regenerate them from the protos in "
        "src/luckyrobots/rpc/proto into src/luckyrobots/rpc/generated."
    ) from e


class GrpcConnectionError(Exception):
    """Raised when gRPC connection fails."""

    pass


@dataclass(frozen=True, slots=True)
class ObservationDefaults:
    """Default options for `LuckyEngineClient.get_observation()` calls."""

    include_joint_state: bool = True
    include_agent_frame: bool = True
    include_telemetry: bool = False
    camera_names: Optional[list[str]] = None
    viewport_names: Optional[list[str]] = None
    width: int = 0
    height: int = 0
    format: str = "raw"


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
        observation_defaults: Optional[ObservationDefaults] = None,
    ) -> None:
        """
        Initialize the LuckyEngine gRPC client.

        Args:
            host: gRPC server host address.
            port: gRPC server port.
            timeout: Default timeout for RPC calls in seconds.
        """
        self.host = host
        self.port = port
        self.timeout = timeout
        self._robot_name = robot_name
        self._observation_defaults = observation_defaults or ObservationDefaults()

        self._channel = None

        # Service stubs (populated after connect)
        self._scene = None
        self._mujoco = None
        self._telemetry = None
        self._agent = None
        self._viewport = None
        self._camera = None

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

        logger.info(f"Connected to LuckyEngine gRPC server at {target}")

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
        Perform a health check by calling GetMujocoInfo (GetSceneInfo can hang).

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

    def wait_for_server(self, timeout: float = 30.0, poll_interval: float = 0.5) -> bool:
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

            if self.health_check(timeout=1.0):
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

    @property
    def observation_defaults(self) -> ObservationDefaults:
        """Default options applied by `get_observation()` when arguments are omitted."""
        return self._observation_defaults

    def set_observation_defaults(self, defaults: ObservationDefaults) -> None:
        """Set default options applied by `get_observation()` when arguments are omitted."""
        self._observation_defaults = defaults

    # --- Service stubs ---

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
    def telemetry(self) -> Any:
        """TelemetryService stub."""
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
        """ViewportService stub."""
        if self._viewport is None:
            raise GrpcConnectionError("Not connected. Call connect() first.")
        return self._viewport

    @property
    def camera(self) -> Any:
        """CameraService stub."""
        if self._camera is None:
            raise GrpcConnectionError("Not connected. Call connect() first.")
        return self._camera

    # --- Convenience methods ---

    def get_scene_info(self, timeout: Optional[float] = None):
        """Get scene information."""
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
        """Get agent schema (observation/action sizes and names)."""
        timeout = timeout or self.timeout
        return self.agent.GetAgentSchema(
            self.pb.agent.GetAgentSchemaRequest(agent_name=agent_name),
            timeout=timeout,
        )

    def get_observation(
        self,
        robot_name: Optional[str] = None,
        agent_name: str = "",
        include_joint_state: Optional[bool] = None,
        include_agent_frame: Optional[bool] = None,
        include_telemetry: Optional[bool] = None,
        camera_names: Optional[list[str]] = None,
        viewport_names: Optional[list[str]] = None,
        width: Optional[int] = None,
        height: Optional[int] = None,
        format: Optional[str] = None,
        timeout: Optional[float] = None,
    ):
        """
        Get a single-shot unified observation snapshot.

        This RPC is defined in `hazel_rpc.proto` as `AgentService.GetObservation`.
        LuckyEngine must implement it for this call to succeed.
        """
        timeout = timeout or self.timeout

        resolved_robot_name = robot_name if robot_name is not None else self._robot_name
        if not resolved_robot_name:
            raise ValueError(
                "robot_name is required (pass `robot_name=` or set it once via "
                "LuckyEngineClient(robot_name=...) / client.set_robot_name(...))."
            )

        defaults = self._observation_defaults
        include_joint_state = (
            defaults.include_joint_state
            if include_joint_state is None
            else include_joint_state
        )
        include_agent_frame = (
            defaults.include_agent_frame
            if include_agent_frame is None
            else include_agent_frame
        )
        include_telemetry = (
            defaults.include_telemetry if include_telemetry is None else include_telemetry
        )
        camera_names = defaults.camera_names if camera_names is None else camera_names
        viewport_names = (
            defaults.viewport_names if viewport_names is None else viewport_names
        )
        width = defaults.width if width is None else width
        height = defaults.height if height is None else height
        format = defaults.format if format is None else format

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

        viewports = []
        if viewport_names:
            for viewport_name in viewport_names:
                viewports.append(
                    self.pb.agent.GetViewportFrameRequest(
                        viewport_name=viewport_name,
                        width=width,
                        height=height,
                        format=format,
                    )
                )

        return self.agent.GetObservation(
            self.pb.agent.GetObservationRequest(
                robot_name=resolved_robot_name,
                agent_name=agent_name,
                include_joint_state=include_joint_state,
                include_agent_frame=include_agent_frame,
                include_telemetry=include_telemetry,
                cameras=cameras,
                viewports=viewports,
            ),
            timeout=timeout,
        )

    def stream_agent(self, agent_name: str = "", target_fps: int = 30):
        """
        Start streaming agent observations.

        Returns an iterator of AgentFrame messages.
        """
        return self.agent.StreamAgent(
            self.pb.agent.StreamAgentRequest(agent_name=agent_name, target_fps=target_fps),
        )

    def stream_telemetry(self, target_fps: int = 30):
        """
        Start streaming telemetry data.

        Returns an iterator of TelemetryFrame messages.
        """
        return self.telemetry.StreamTelemetry(
            self.pb.telemetry.StreamTelemetryRequest(target_fps=target_fps),
        )

    def list_cameras(self, timeout: Optional[float] = None):
        """List available cameras."""
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
        Start streaming camera frames.

        Args:
            camera_id: Camera entity ID (use either id or name).
            camera_name: Camera name (use either id or name).
            target_fps: Desired frames per second.
            width: Desired width (0 = native).
            height: Desired height (0 = native).
            format: Image format ("raw" or "jpeg").

        Returns an iterator of ImageFrame messages.
        """
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
