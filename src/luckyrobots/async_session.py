"""Asyncio mirror of luckyrobots.Session, built on grpc.aio.

Use this when your application is asyncio-native and you want concurrent
calls without spawning threads. The API mirrors Session 1:1, just with
coroutines.

Lifecycle:
    sess = AsyncSession(host="127.0.0.1", port=50051)
    await sess.connect()
    ...
    await sess.close()

Or as an async context manager:
    async with AsyncSession() as sess:
        await sess.connect()
        ...

Notes:
- AsyncSession is a sibling of the sync ``Session`` (not a method on it).
  It uses a ``grpc.aio`` channel and the same generated ``*Stub`` classes
  (the generated stubs work with both sync and aio channels — only the
  channel type differs).
- This wrapper deliberately stays small: launch_luckyengine / domain
  helpers from the sync ``Session`` are not duplicated here. Pair with
  the sync ``Session`` if you need engine-launch lifecycle, or call
  launch_luckyengine() yourself.
"""

from __future__ import annotations

import asyncio
import logging
from typing import List, Optional

import grpc.aio as grpc_aio

from .grpc.generated import (
    agent_pb2,
    agent_pb2_grpc,
    debug_pb2_grpc,
    mujoco_pb2_grpc,
    mujoco_scene_pb2,
    mujoco_scene_pb2_grpc,
    scene_pb2,
    scene_pb2_grpc,
)
from .robots.robot_controller import (
    PolicyDescriptorInfo,
    RobotControllerState,
)

logger = logging.getLogger("luckyrobots.async_session")


class AsyncSession:
    """Asyncio session wrapping a ``grpc.aio`` channel + service stubs.

    Mirrors the surface of ``luckyrobots.Session`` for the bits that are
    reachable via gRPC stubs. Use as either a manual lifecycle object
    (``await connect()`` / ``await close()``) or as an async context
    manager (``async with AsyncSession() as sess: await sess.connect()``).
    """

    def __init__(self, host: str = "127.0.0.1", port: int = 50051) -> None:
        self.host = host
        self.port = port

        self._channel: Optional[grpc_aio.Channel] = None
        self._agent: Optional[agent_pb2_grpc.AgentServiceStub] = None
        self._scene: Optional[scene_pb2_grpc.SceneServiceStub] = None
        self._mujoco: Optional[mujoco_pb2_grpc.MujocoServiceStub] = None
        self._mujoco_scene: Optional[mujoco_scene_pb2_grpc.MujocoSceneServiceStub] = None
        self._debug: Optional[debug_pb2_grpc.DebugServiceStub] = None

    # ---- lifecycle ----

    async def connect(self, timeout_s: float = 30.0) -> None:
        """Open an aio channel and wait until the server is ready."""
        if self._channel is not None:
            return

        target = f"{self.host}:{self.port}"
        logger.info("AsyncSession connecting to %s", target)
        channel = grpc_aio.insecure_channel(target)

        try:
            await asyncio.wait_for(channel.channel_ready(), timeout=timeout_s)
        except asyncio.TimeoutError as exc:
            await channel.close()
            raise TimeoutError(
                f"AsyncSession: gRPC server at {target} not ready after {timeout_s}s"
            ) from exc

        self._channel = channel
        self._agent = agent_pb2_grpc.AgentServiceStub(channel)
        self._scene = scene_pb2_grpc.SceneServiceStub(channel)
        self._mujoco = mujoco_pb2_grpc.MujocoServiceStub(channel)
        self._mujoco_scene = mujoco_scene_pb2_grpc.MujocoSceneServiceStub(channel)
        self._debug = debug_pb2_grpc.DebugServiceStub(channel)
        logger.info("AsyncSession connected to %s", target)

    async def close(self) -> None:
        """Close the underlying aio channel and drop stubs."""
        if self._channel is None:
            return
        ch = self._channel
        self._channel = None
        self._agent = None
        self._scene = None
        self._mujoco = None
        self._mujoco_scene = None
        self._debug = None
        try:
            await ch.close()
        except Exception:
            logger.exception("AsyncSession: error closing channel")

    # ---- context manager ----

    async def __aenter__(self) -> "AsyncSession":
        return self

    async def __aexit__(self, *exc_info) -> None:
        await self.close()

    # ---- introspection ----

    @property
    def is_connected(self) -> bool:
        return self._channel is not None

    def _require_channel(self) -> grpc_aio.Channel:
        if self._channel is None:
            raise RuntimeError(
                "AsyncSession is not connected — call `await session.connect()` first."
            )
        return self._channel

    @property
    def channel(self) -> grpc_aio.Channel:
        """The underlying ``grpc.aio.Channel`` (raises if not connected)."""
        return self._require_channel()

    @property
    def agent(self) -> agent_pb2_grpc.AgentServiceStub:
        self._require_channel()
        return self._agent  # type: ignore[return-value]

    @property
    def scene(self) -> scene_pb2_grpc.SceneServiceStub:
        self._require_channel()
        return self._scene  # type: ignore[return-value]

    @property
    def mujoco(self) -> mujoco_pb2_grpc.MujocoServiceStub:
        self._require_channel()
        return self._mujoco  # type: ignore[return-value]

    @property
    def mujoco_scene(self) -> mujoco_scene_pb2_grpc.MujocoSceneServiceStub:
        self._require_channel()
        return self._mujoco_scene  # type: ignore[return-value]

    @property
    def debug(self) -> debug_pb2_grpc.DebugServiceStub:
        self._require_channel()
        return self._debug  # type: ignore[return-value]

    # ---- convenience awaitables (mirror Session.list_robot_controllers etc.) ----

    async def list_robot_controllers(self) -> List[RobotControllerState]:
        """Enumerate every RobotControllerComponent in the active scene."""
        stub = self.agent
        resp = await stub.ListRobotControllers(agent_pb2.ListRobotControllersRequest())
        return [RobotControllerState._from_pb(c) for c in resp.controllers]

    async def list_policy_descriptors(self) -> List[PolicyDescriptorInfo]:
        """Enumerate entries in the project's PolicyRegistry.yaml."""
        stub = self.agent
        resp = await stub.ListPolicyDescriptors(agent_pb2.ListPolicyDescriptorsRequest())
        return [PolicyDescriptorInfo._from_pb(p) for p in resp.policies]

    # ---- editor lifecycle / scene reset ----

    async def enter_play_mode(self):
        """Trigger the editor Edit -> Play transition (no-op in dist builds).

        Session boundary, not pause/resume — Exit will tear down any in-flight
        recording. Returns immediately; the transition is async, so poll
        agent / model readiness before stepping the simulation."""
        return await self.scene.EnterPlayMode(scene_pb2.EnterPlayModeRequest())

    async def exit_play_mode(self):
        """Trigger the editor Play -> Edit transition (no-op in dist builds).

        Closes out any active recording session as part of the transition."""
        return await self.scene.ExitPlayMode(scene_pb2.ExitPlayModeRequest())

    async def reset_scene(self, preserve_time: bool = False):
        """Soft-reset the live MuJoCo scene back to ``keyframe[0]`` /
        ``qpos0``, zeroing velocities/forces/ctrl and reseeding active
        PolicyRuntime PD targets. Recording continues — the next captured
        frame is tagged with the ``post_reset`` flag bit.
        """
        return await self.mujoco_scene.ResetScene(
            mujoco_scene_pb2.ResetSceneRequest(preserve_time=preserve_time)
        )
