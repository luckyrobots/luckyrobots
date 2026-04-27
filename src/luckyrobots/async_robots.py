"""Async mirror of :class:`luckyrobots.robots.RobotController`.

Reuses the ``RobotControllerState`` / ``PolicySlotState`` /
``PolicyCommandIdEntry`` dataclasses from the sync module — the wire
mapping is identical, only the call style changes.

Quick start:

    from luckyrobots.async_session import AsyncSession
    from luckyrobots.async_robots import AsyncRobotController

    async with AsyncSession() as sess:
        await sess.connect()
        controllers = await sess.list_robot_controllers()
        robot = AsyncRobotController.from_state(sess, controllers[0])
        await robot.set_policy_active("Walker", True)
        await robot.set_command_float("Walker", 1, 0.5)
"""

from __future__ import annotations

from typing import AsyncIterator, Iterable, List, Tuple, Union

import numpy as np

from .grpc.generated import agent_pb2 as _agent_pb2
from .grpc.generated import common_pb2 as _common_pb2
from .robots.robot_controller import (
    PolicyCommandIdEntry,  # re-exported for convenience
    PolicySlotState,
    RobotControllerState,
    _string_to_command_type,
)

# Silence "imported but unused" — re-exported for callers that want to
# build their own helpers on top of the dataclasses.
__all__ = [
    "AsyncRobotController",
    "PolicyCommandIdEntry",
    "PolicySlotState",
    "RobotControllerState",
    "SlotId",
]

SlotId = Union[int, str]


class AsyncRobotController:
    """Asyncio mirror of :class:`luckyrobots.robots.RobotController`.

    Same RPC semantics, same slot-name caching, same proto-to-dataclass
    conversions — every call is a coroutine and dispatches via the
    ``AsyncSession``'s ``grpc.aio`` stub.
    """

    def __init__(self, session, entity_id: int) -> None:
        self._session = session
        self._entity_id = int(entity_id)
        self._slot_name_cache: dict[str, int] = {}

    # ---- construction helpers ----

    @classmethod
    def from_state(cls, session, state: RobotControllerState) -> "AsyncRobotController":
        rc = cls(session, state.entity_id)
        for s in state.slots:
            rc._slot_name_cache[s.name] = s.slot_id
        return rc

    # ---- internals ----

    def _stub(self):
        # ``AsyncSession.agent`` raises if the session is not connected.
        return self._session.agent

    def _entity(self) -> "_common_pb2.EntityId":
        return _common_pb2.EntityId(id=self._entity_id)

    async def _resolve_slot(self, slot: SlotId) -> int:
        if isinstance(slot, int):
            return slot
        if slot in self._slot_name_cache:
            return self._slot_name_cache[slot]
        # Miss — fetch the full state and rebuild the cache.
        state = await self.get_state()
        for s in state.slots:
            self._slot_name_cache[s.name] = s.slot_id
        if slot in self._slot_name_cache:
            return self._slot_name_cache[slot]
        raise KeyError(
            f"PolicySlot with name '{slot}' not found on entity {self._entity_id}"
        )

    @staticmethod
    def _check_ack(ack) -> None:
        if not ack.success:
            raise RuntimeError(f"Policy RPC failed: {ack.message}")

    # ---- introspection ----

    @property
    def entity_id(self) -> int:
        return self._entity_id

    async def get_state(self) -> RobotControllerState:
        resp = await self._stub().GetRobotController(
            _agent_pb2.GetRobotControllerRequest(entity=self._entity())
        )
        if not resp.found:
            raise LookupError(f"No RobotControllerComponent on entity {self._entity_id}")
        state = RobotControllerState._from_pb(resp.controller)
        for s in state.slots:
            self._slot_name_cache[s.name] = s.slot_id
        return state

    async def stream_state(
        self, target_fps: int = 30
    ) -> AsyncIterator[RobotControllerState]:
        req = _agent_pb2.StreamRobotControllerRequest(
            entity=self._entity(), target_fps=target_fps
        )
        async for frame in self._stub().StreamRobotController(req):
            yield RobotControllerState._from_pb(frame)

    async def stream_slot_state(
        self, slot: SlotId, target_fps: int = 30
    ) -> AsyncIterator[PolicySlotState]:
        slot_id = await self._resolve_slot(slot)
        req = _agent_pb2.StreamPolicySlotStateRequest(
            entity=self._entity(), slot_id=slot_id, target_fps=target_fps
        )
        async for frame in self._stub().StreamPolicySlotState(req):
            yield PolicySlotState._from_pb(frame)

    # ---- slot control ----

    async def set_policy_active(self, slot: SlotId, active: bool) -> None:
        slot_id = await self._resolve_slot(slot)
        req = _agent_pb2.SetPolicyActiveRequest(
            entity=self._entity(), slot_id=slot_id, active=active
        )
        self._check_ack(await self._stub().SetPolicyActive(req))

    async def set_policy_descriptor(self, slot: SlotId, descriptor_path: str) -> None:
        slot_id = await self._resolve_slot(slot)
        req = _agent_pb2.SetPolicyDescriptorRequest(
            entity=self._entity(),
            slot_id=slot_id,
            descriptor_path=descriptor_path,
        )
        self._check_ack(await self._stub().SetPolicyDescriptor(req))

    async def set_driven_joints(self, slot: SlotId, joints: Iterable[str]) -> None:
        slot_id = await self._resolve_slot(slot)
        req = _agent_pb2.SetPolicyDrivenJointsRequest(
            entity=self._entity(), slot_id=slot_id
        )
        req.joint_names.extend(joints)
        self._check_ack(await self._stub().SetPolicyDrivenJoints(req))

    async def set_policy_clamp_observation(self, slot: SlotId, clamp: bool) -> None:
        slot_id = await self._resolve_slot(slot)
        req = _agent_pb2.SetPolicyClampObservationRequest(
            entity=self._entity(),
            slot_id=slot_id,
            clamp_observation_for_unclaimed_joints=clamp,
        )
        self._check_ack(await self._stub().SetPolicyClampObservation(req))

    async def set_policy_priority(self, slot: SlotId, priority: int) -> None:
        slot_id = await self._resolve_slot(slot)
        req = _agent_pb2.SetPolicyPriorityRequest(
            entity=self._entity(),
            slot_id=slot_id,
            priority=int(priority),
        )
        self._check_ack(await self._stub().SetPolicyPriority(req))

    # ---- commands ----

    async def set_command_float(
        self, slot: SlotId, command_id: int, value: float
    ) -> None:
        slot_id = await self._resolve_slot(slot)
        req = _agent_pb2.SetPolicyCommandFloatRequest(
            entity=self._entity(),
            slot_id=slot_id,
            command_id=int(command_id),
            value=float(value),
        )
        self._check_ack(await self._stub().SetPolicyCommandFloat(req))

    async def set_command_bool(
        self, slot: SlotId, command_id: int, value: bool
    ) -> None:
        slot_id = await self._resolve_slot(slot)
        req = _agent_pb2.SetPolicyCommandBoolRequest(
            entity=self._entity(),
            slot_id=slot_id,
            command_id=int(command_id),
            value=bool(value),
        )
        self._check_ack(await self._stub().SetPolicyCommandBool(req))

    async def get_command_float(self, slot: SlotId, command_id: int) -> float:
        slot_id = await self._resolve_slot(slot)
        req = _agent_pb2.GetPolicyCommandFloatRequest(
            entity=self._entity(),
            slot_id=slot_id,
            command_id=int(command_id),
        )
        resp = await self._stub().GetPolicyCommandFloat(req)
        if not resp.success:
            raise RuntimeError(f"GetPolicyCommandFloat failed: {resp.message}")
        return resp.value

    async def get_command_bool(self, slot: SlotId, command_id: int) -> bool:
        slot_id = await self._resolve_slot(slot)
        req = _agent_pb2.GetPolicyCommandBoolRequest(
            entity=self._entity(),
            slot_id=slot_id,
            command_id=int(command_id),
        )
        resp = await self._stub().GetPolicyCommandBool(req)
        if not resp.success:
            raise RuntimeError(f"GetPolicyCommandBool failed: {resp.message}")
        return resp.value

    # ---- motion graph ----
    #
    # NOTE: Python doesn't have native async properties, so the sync
    # ``RobotController.motion_graph_active`` property is exposed here as
    # a coroutine method ``motion_graph_active_async()``. Awaiting a
    # property would require either ``__await__``-on-property hacks or
    # a third-party ``@async_property`` decorator; both add surface
    # area for very little gain.

    async def motion_graph_active_async(self) -> bool:
        resp = await self._stub().GetMotionGraphActive(
            _agent_pb2.GetMotionGraphActiveRequest(entity=self._entity())
        )
        if not resp.success:
            raise RuntimeError(f"GetMotionGraphActive failed: {resp.message}")
        return resp.active

    async def set_motion_graph_active(self, active: bool) -> None:
        req = _agent_pb2.SetMotionGraphActiveRequest(
            entity=self._entity(), active=active
        )
        self._check_ack(await self._stub().SetMotionGraphActive(req))

    async def set_motion_graph_input(self, input_id: int, value) -> None:
        """Set a motion-graph input. Mirrors the sync version's oneof
        type-detection: ``bool`` / ``int`` / ``float`` / 3-tuple-or-list."""
        mg = _agent_pb2.MotionGraphInputValue()
        # ``bool`` is a subclass of ``int`` in Python, so check it first.
        if isinstance(value, bool):
            mg.bool_val = value
        elif isinstance(value, int):
            mg.int_val = value
        elif isinstance(value, float):
            mg.float_val = value
        elif isinstance(value, (tuple, list)) and len(value) == 3:
            mg.vec3_val.x = float(value[0])
            mg.vec3_val.y = float(value[1])
            mg.vec3_val.z = float(value[2])
        else:
            raise TypeError(
                f"Unsupported motion graph input value type: {type(value).__name__}"
            )
        req = _agent_pb2.SetMotionGraphInputRequest(
            entity=self._entity(), input_id=int(input_id), value=mg
        )
        self._check_ack(await self._stub().SetMotionGraphInput(req))

    async def get_motion_graph_input(self, input_id: int, type_hint: str = "float"):
        type_enum = _string_to_command_type(type_hint)
        req = _agent_pb2.GetMotionGraphInputRequest(
            entity=self._entity(), input_id=int(input_id), type_hint=type_enum
        )
        resp = await self._stub().GetMotionGraphInput(req)
        if not resp.success:
            raise RuntimeError(f"GetMotionGraphInput failed: {resp.message}")
        v = resp.value
        case = v.WhichOneof("value")
        if case == "bool_val":
            return v.bool_val
        if case == "int_val":
            return v.int_val
        if case == "float_val":
            return v.float_val
        if case == "vec3_val":
            return (v.vec3_val.x, v.vec3_val.y, v.vec3_val.z)
        if case == "trigger":
            return bool(v.trigger)
        return None

    async def fire_motion_graph_trigger(self, input_id: int) -> None:
        req = _agent_pb2.FireMotionGraphTriggerRequest(
            entity=self._entity(), input_id=int(input_id)
        )
        self._check_ack(await self._stub().FireMotionGraphTrigger(req))

    # ---- runtime diagnostics ----

    async def get_base_pose(self, slot: SlotId) -> dict:
        """Return the active PolicyRuntime's base pose as a dict with
        MuJoCo and Hazel-frame fields. Raises ``LookupError`` when the
        slot is inactive or the runtime hasn't loaded yet."""
        slot_id = await self._resolve_slot(slot)
        req = _agent_pb2.GetPolicyBasePoseRequest(
            entity=self._entity(), slot_id=slot_id
        )
        resp = await self._stub().GetPolicyBasePose(req)
        if not resp.success:
            raise LookupError(f"GetPolicyBasePose failed: {resp.message}")
        return {
            "x": resp.x,
            "y": resp.y,
            "yaw": resp.yaw,
            "x_hz": resp.x_hz,
            "z_hz": resp.z_hz,
            "yaw_hz": resp.yaw_hz,
        }

    async def get_last_action(
        self, slot: SlotId
    ) -> Tuple[np.ndarray, List[str]]:
        """Return ``(action_values, joint_names)`` for the last ONNX
        inference. Raises ``LookupError`` when the slot is inactive or
        hasn't inferred yet."""
        slot_id = await self._resolve_slot(slot)
        req = _agent_pb2.GetPolicyLastActionRequest(
            entity=self._entity(), slot_id=slot_id
        )
        resp = await self._stub().GetPolicyLastAction(req)
        if not resp.success:
            raise LookupError(f"GetPolicyLastAction failed: {resp.message}")
        return np.asarray(resp.action, dtype=np.float32), list(resp.joint_names)
