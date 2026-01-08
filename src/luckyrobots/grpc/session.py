import threading
from dataclasses import dataclass
from typing import Optional

import grpc

import hazel_rpc_pb2 as pb  # type: ignore
import hazel_rpc_pb2_grpc as stubs  # type: ignore


@dataclass
class GrpcConfig:
    """Connection configuration for the Hazel gRPC server."""

    address: str = "127.0.0.1:50051"
    secure: bool = False
    root_certificates: Optional[bytes] = None


class GrpcSession:
    """
    Thin wrapper around a gRPC channel and Hazel stubs.

    This is intentionally minimal: LuckyRobots is a *client* of the Hazel
    gRPC server exposed by LuckyEditor / RobotSandbox. We do not start any
    servers here, only create channels and stubs.
    """

    def __init__(self, config: Optional[GrpcConfig] = None) -> None:
        self._config = config or GrpcConfig()
        self._channel: Optional[grpc.Channel] = None
        self._lock = threading.Lock()

        # Lazily created stubs
        self._scene_stub: Optional[stubs.SceneServiceStub] = None
        self._mujoco_stub: Optional[stubs.MujocoServiceStub] = None
        self._agent_stub: Optional[stubs.AgentServiceStub] = None
        self._telemetry_stub: Optional[stubs.TelemetryServiceStub] = None
        self._viewport_stub: Optional[stubs.ViewportServiceStub] = None
        self._camera_stub: Optional[stubs.CameraServiceStub] = None

    # --------------------------------------------------------------------- #
    # Channel management
    # --------------------------------------------------------------------- #
    @property
    def channel(self) -> grpc.Channel:
        """
        Return an open grpc.Channel, creating it if needed.

        Callers should not close the channel directly; use close().
        """
        if self._channel is not None:
            return self._channel

        with self._lock:
            if self._channel is not None:
                return self._channel

            if self._config.secure:
                credentials = grpc.ssl_channel_credentials(
                    root_certificates=self._config.root_certificates
                )
                self._channel = grpc.secure_channel(self._config.address, credentials)
            else:
                self._channel = grpc.insecure_channel(self._config.address)

            return self._channel

    def close(self) -> None:
        """Close the underlying channel and reset all stubs."""
        with self._lock:
            if self._channel is not None:
                self._channel.close()
            self._channel = None
            self._scene_stub = None
            self._mujoco_stub = None
            self._agent_stub = None
            self._telemetry_stub = None
            self._viewport_stub = None
            self._camera_stub = None

    # --------------------------------------------------------------------- #
    # Stubs – one per Hazel service
    # --------------------------------------------------------------------- #
    @property
    def scene(self) -> stubs.SceneServiceStub:
        if self._scene_stub is None:
            self._scene_stub = stubs.SceneServiceStub(self.channel)
        return self._scene_stub

    @property
    def mujoco(self) -> stubs.MujocoServiceStub:
        if self._mujoco_stub is None:
            self._mujoco_stub = stubs.MujocoServiceStub(self.channel)
        return self._mujoco_stub

    @property
    def agent(self) -> stubs.AgentServiceStub:
        if self._agent_stub is None:
            self._agent_stub = stubs.AgentServiceStub(self.channel)
        return self._agent_stub

    @property
    def telemetry(self) -> stubs.TelemetryServiceStub:
        if self._telemetry_stub is None:
            self._telemetry_stub = stubs.TelemetryServiceStub(self.channel)
        return self._telemetry_stub

    @property
    def viewport(self) -> stubs.ViewportServiceStub:
        if self._viewport_stub is None:
            self._viewport_stub = stubs.ViewportServiceStub(self.channel)
        return self._viewport_stub

    @property
    def camera(self) -> stubs.CameraServiceStub:
        if self._camera_stub is None:
            self._camera_stub = stubs.CameraServiceStub(self.channel)
        return self._camera_stub


__all__ = [
    "GrpcConfig",
    "GrpcSession",
    "pb",
    "stubs",
]


