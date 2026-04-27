"""
RobotController: Python wrapper for RobotControllerComponent over gRPC.

Mirrors the in-editor Hazel.RobotController struct so external agents get the
same PolicySlot + DrivenJoints + MotionGraph surface (SetPolicyActive,
SetFloat, SetDrivenJoints, SetMotionGraphActive, etc.) without having to form
protobuf messages by hand.

Quick start:

    from luckyrobots import Session
    from luckyrobots.robots import RobotController, list_robot_controllers

    with Session() as sess:
        sess.start(scene="Unitree_PickPlace", robot="G1", task="walk")

        # Enumerate robots + policies available in the loaded scene.
        controllers = list_robot_controllers(sess)
        walker_ids  = {d.policy_id: d for d in list_policy_descriptors(sess)}

        robot = RobotController.from_state(sess, controllers[0])
        robot.set_policy_active(slot_id=1, active=True)   # activate Walker slot
        robot.set_command_float(slot_id=1, command_id=1, value=0.5)  # SetVx
        robot.set_driven_joints(slot_id=2, joints=["left_arm_*", "right_arm_*"])
        robot.set_motion_graph_active(False)
"""

from __future__ import annotations

import dataclasses
from contextlib import contextmanager
from typing import Iterable, Iterator, List, Mapping, Optional, Sequence, Tuple, Union

import numpy as np

from ..grpc.generated import agent_pb2 as _agent_pb2
from ..grpc.generated import common_pb2 as _common_pb2


# ---------------------------------------------------------------------------
# Data classes mirroring the proto messages, but friendlier for Python callers.
# (Raw protobuf messages use CamelCase attributes with RepeatedField/Map
#  wrappers, which feel foreign to most Python code. Thin dataclasses keep
#  the wire mapping obvious while supporting dict-like iteration.)
# ---------------------------------------------------------------------------

@dataclasses.dataclass(frozen=True)
class PolicyCommandIdEntry:
    id: int
    name: str
    type: str  # "float" | "bool" | "int" | "uint" | "vec2" | "vec3" | "vec4" | "string"

    @classmethod
    def _from_pb(cls, pb) -> "PolicyCommandIdEntry":
        return cls(id=pb.id, name=pb.name, type=_command_type_to_string(pb.type))


@dataclasses.dataclass(frozen=True)
class PolicySlotState:
    slot_id: int
    name: str
    descriptor_path: str
    active: bool
    priority: int
    driven_joints: Sequence[str]
    clamp_observation_for_unclaimed_joints: bool
    ready: bool
    active_policy_id: str
    command_id_map: Sequence[PolicyCommandIdEntry]
    policy_joint_names: Sequence[str]

    @classmethod
    def _from_pb(cls, pb) -> "PolicySlotState":
        return cls(
            slot_id=pb.slot_id,
            name=pb.name,
            descriptor_path=pb.descriptor_path,
            active=pb.active,
            priority=pb.priority,
            driven_joints=tuple(pb.driven_joints),
            clamp_observation_for_unclaimed_joints=pb.clamp_observation_for_unclaimed_joints,
            ready=pb.ready,
            active_policy_id=pb.active_policy_id,
            command_id_map=tuple(PolicyCommandIdEntry._from_pb(c) for c in pb.command_id_map),
            policy_joint_names=tuple(pb.policy_joint_names),
        )

    def command_id(self, name: str) -> Optional[int]:
        """Resolve a command name to its uint id (or None if not declared)."""
        for entry in self.command_id_map:
            if entry.name == name:
                return entry.id
        return None


@dataclasses.dataclass(frozen=True)
class RobotControllerState:
    entity_id: int
    entity_name: str
    motion_graph_active: bool
    slots: Sequence[PolicySlotState]

    @classmethod
    def _from_pb(cls, pb) -> "RobotControllerState":
        return cls(
            entity_id=pb.entity.id,
            entity_name=pb.entity_name,
            motion_graph_active=pb.motion_graph_active,
            slots=tuple(PolicySlotState._from_pb(s) for s in pb.slots),
        )

    def slot(self, slot_id_or_name: Union[int, str]) -> Optional[PolicySlotState]:
        """Look up a slot by uint id OR by name (as declared in the inspector)."""
        if isinstance(slot_id_or_name, str):
            for s in self.slots:
                if s.name == slot_id_or_name:
                    return s
            return None
        for s in self.slots:
            if s.slot_id == slot_id_or_name:
                return s
        return None


@dataclasses.dataclass(frozen=True)
class PolicyDescriptorInfo:
    policy_id: str
    descriptor_path: str
    joints: Sequence[str]
    command_id_map: Sequence[PolicyCommandIdEntry]
    freeze_joint_names: Sequence[str]
    command_aliases: Mapping[str, str]

    @classmethod
    def _from_pb(cls, pb) -> "PolicyDescriptorInfo":
        return cls(
            policy_id=pb.policy_id,
            descriptor_path=pb.descriptor_path,
            joints=tuple(pb.joints),
            command_id_map=tuple(PolicyCommandIdEntry._from_pb(c) for c in pb.command_id_map),
            freeze_joint_names=tuple(pb.freeze_joint_names),
            command_aliases=dict(pb.command_aliases),
        )


# ---------------------------------------------------------------------------
# RobotController — the main high-level surface.
# ---------------------------------------------------------------------------

SlotId = Union[int, str]


class RobotController:
    """
    Ergonomic wrapper around the AgentService policy + motion-graph RPCs,
    scoped to a single RobotControllerComponent (by entity id).

    Construct with either ``RobotController(session, entity_id)`` or
    ``RobotController.from_state(session, state)``; slot ids may be passed
    as uint *or* as the slot's inspector name (resolved via GetRobotController
    on first use and then cached).
    """

    def __init__(self, session, entity_id: int) -> None:
        self._session = session
        self._entity_id = int(entity_id)
        self._slot_name_cache: dict[str, int] = {}

    # ---- construction helpers ----

    @classmethod
    def from_state(cls, session, state: RobotControllerState) -> "RobotController":
        rc = cls(session, state.entity_id)
        for s in state.slots:
            rc._slot_name_cache[s.name] = s.slot_id
        return rc

    # ---- internals ----

    def _stub(self):
        client = self._session.engine_client
        if client is None:
            raise RuntimeError("Session is not connected — call session.start()/connect() first.")
        return client.agent

    def _entity(self) -> "_common_pb2.EntityId":
        return _common_pb2.EntityId(id=self._entity_id)

    def _resolve_slot(self, slot: SlotId) -> int:
        if isinstance(slot, int):
            return slot
        if slot in self._slot_name_cache:
            return self._slot_name_cache[slot]
        # Miss — fetch the full state and rebuild the cache.
        state = self.get_state()
        for s in state.slots:
            self._slot_name_cache[s.name] = s.slot_id
        if slot in self._slot_name_cache:
            return self._slot_name_cache[slot]
        raise KeyError(f"PolicySlot with name '{slot}' not found on entity {self._entity_id}")

    @staticmethod
    def _check_ack(ack) -> None:
        if not ack.success:
            raise RuntimeError(f"Policy RPC failed: {ack.message}")

    # ---- introspection ----

    @property
    def entity_id(self) -> int:
        return self._entity_id

    def get_state(self) -> RobotControllerState:
        resp = self._stub().GetRobotController(
            _agent_pb2.GetRobotControllerRequest(entity=self._entity())
        )
        if not resp.found:
            raise LookupError(f"No RobotControllerComponent on entity {self._entity_id}")
        state = RobotControllerState._from_pb(resp.controller)
        for s in state.slots:
            self._slot_name_cache[s.name] = s.slot_id
        return state

    def stream_state(self, target_fps: int = 30) -> Iterator[RobotControllerState]:
        req = _agent_pb2.StreamRobotControllerRequest(entity=self._entity(), target_fps=target_fps)
        for frame in self._stub().StreamRobotController(req):
            yield RobotControllerState._from_pb(frame)

    def stream_slot_state(self, slot: SlotId, target_fps: int = 30) -> Iterator[PolicySlotState]:
        req = _agent_pb2.StreamPolicySlotStateRequest(
            entity=self._entity(),
            slot_id=self._resolve_slot(slot),
            target_fps=target_fps,
        )
        for frame in self._stub().StreamPolicySlotState(req):
            yield PolicySlotState._from_pb(frame)

    # ---- slot control ----

    def set_policy_active(self, slot: SlotId, active: bool) -> None:
        req = _agent_pb2.SetPolicyActiveRequest(
            entity=self._entity(), slot_id=self._resolve_slot(slot), active=active
        )
        self._check_ack(self._stub().SetPolicyActive(req))

    def set_policy_descriptor(self, slot: SlotId, descriptor_path: str) -> None:
        req = _agent_pb2.SetPolicyDescriptorRequest(
            entity=self._entity(),
            slot_id=self._resolve_slot(slot),
            descriptor_path=descriptor_path,
        )
        self._check_ack(self._stub().SetPolicyDescriptor(req))

    def set_driven_joints(self, slot: SlotId, joints: Iterable[str]) -> None:
        req = _agent_pb2.SetPolicyDrivenJointsRequest(
            entity=self._entity(), slot_id=self._resolve_slot(slot)
        )
        req.joint_names.extend(joints)
        self._check_ack(self._stub().SetPolicyDrivenJoints(req))

    def set_policy_clamp_observation(self, slot: SlotId, clamp: bool) -> None:
        req = _agent_pb2.SetPolicyClampObservationRequest(
            entity=self._entity(),
            slot_id=self._resolve_slot(slot),
            clamp_observation_for_unclaimed_joints=clamp,
        )
        self._check_ack(self._stub().SetPolicyClampObservation(req))

    def set_policy_priority(self, slot: SlotId, priority: int) -> None:
        req = _agent_pb2.SetPolicyPriorityRequest(
            entity=self._entity(),
            slot_id=self._resolve_slot(slot),
            priority=int(priority),
        )
        self._check_ack(self._stub().SetPolicyPriority(req))

    # ---- commands ----

    def set_command_float(self, slot: SlotId, command_id: int, value: float) -> None:
        req = _agent_pb2.SetPolicyCommandFloatRequest(
            entity=self._entity(),
            slot_id=self._resolve_slot(slot),
            command_id=int(command_id),
            value=float(value),
        )
        self._check_ack(self._stub().SetPolicyCommandFloat(req))

    def set_command_bool(self, slot: SlotId, command_id: int, value: bool) -> None:
        req = _agent_pb2.SetPolicyCommandBoolRequest(
            entity=self._entity(),
            slot_id=self._resolve_slot(slot),
            command_id=int(command_id),
            value=bool(value),
        )
        self._check_ack(self._stub().SetPolicyCommandBool(req))

    def get_command_float(self, slot: SlotId, command_id: int) -> float:
        req = _agent_pb2.GetPolicyCommandFloatRequest(
            entity=self._entity(),
            slot_id=self._resolve_slot(slot),
            command_id=int(command_id),
        )
        resp = self._stub().GetPolicyCommandFloat(req)
        if not resp.success:
            raise RuntimeError(f"GetPolicyCommandFloat failed: {resp.message}")
        return resp.value

    def get_command_bool(self, slot: SlotId, command_id: int) -> bool:
        req = _agent_pb2.GetPolicyCommandBoolRequest(
            entity=self._entity(),
            slot_id=self._resolve_slot(slot),
            command_id=int(command_id),
        )
        resp = self._stub().GetPolicyCommandBool(req)
        if not resp.success:
            raise RuntimeError(f"GetPolicyCommandBool failed: {resp.message}")
        return resp.value

    # ---- motion graph ----

    @property
    def motion_graph_active(self) -> bool:
        resp = self._stub().GetMotionGraphActive(
            _agent_pb2.GetMotionGraphActiveRequest(entity=self._entity())
        )
        if not resp.success:
            raise RuntimeError(f"GetMotionGraphActive failed: {resp.message}")
        return resp.active

    def set_motion_graph_active(self, active: bool) -> None:
        req = _agent_pb2.SetMotionGraphActiveRequest(entity=self._entity(), active=active)
        self._check_ack(self._stub().SetMotionGraphActive(req))

    def set_motion_graph_input(self, input_id: int, value) -> None:
        """Set a motion-graph input. `value` may be bool / int / float /
        3-tuple-or-list-of-floats. Use :meth:`fire_motion_graph_trigger` for
        pure trigger events."""
        mg = _agent_pb2.MotionGraphInputValue()
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
        self._check_ack(self._stub().SetMotionGraphInput(req))

    def get_motion_graph_input(self, input_id: int, type_hint: str = "float"):
        type_enum = _string_to_command_type(type_hint)
        req = _agent_pb2.GetMotionGraphInputRequest(
            entity=self._entity(), input_id=int(input_id), type_hint=type_enum
        )
        resp = self._stub().GetMotionGraphInput(req)
        if not resp.success:
            raise RuntimeError(f"GetMotionGraphInput failed: {resp.message}")
        v = resp.value
        case = v.WhichOneof("value")
        if case == "bool_val": return v.bool_val
        if case == "int_val":  return v.int_val
        if case == "float_val": return v.float_val
        if case == "vec3_val": return (v.vec3_val.x, v.vec3_val.y, v.vec3_val.z)
        if case == "trigger":  return bool(v.trigger)
        return None

    def fire_motion_graph_trigger(self, input_id: int) -> None:
        req = _agent_pb2.FireMotionGraphTriggerRequest(
            entity=self._entity(), input_id=int(input_id)
        )
        self._check_ack(self._stub().FireMotionGraphTrigger(req))

    # ---- runtime diagnostics ----

    def get_base_pose(self, slot: SlotId):
        """Return the active PolicyRuntime's base pose as a dict with MuJoCo
        and Hazel-frame fields. Raises LookupError when the slot is inactive
        or the runtime hasn't loaded yet."""
        req = _agent_pb2.GetPolicyBasePoseRequest(
            entity=self._entity(), slot_id=self._resolve_slot(slot)
        )
        resp = self._stub().GetPolicyBasePose(req)
        if not resp.success:
            raise LookupError(f"GetPolicyBasePose failed: {resp.message}")
        return {
            "x": resp.x, "y": resp.y, "yaw": resp.yaw,
            "x_hz": resp.x_hz, "z_hz": resp.z_hz, "yaw_hz": resp.yaw_hz,
        }

    def get_last_action(self, slot: SlotId) -> Tuple[np.ndarray, List[str]]:
        """Return (action_values, joint_names) for the last ONNX inference.
        Raises LookupError when the slot is inactive or hasn't inferred yet.

        ``action_values`` is a 1-D ``numpy.ndarray`` (float32) so callers can
        do vectorized math on the result; iteration still works the same
        as it did when this returned a list."""
        req = _agent_pb2.GetPolicyLastActionRequest(
            entity=self._entity(), slot_id=self._resolve_slot(slot)
        )
        resp = self._stub().GetPolicyLastAction(req)
        if not resp.success:
            raise LookupError(f"GetPolicyLastAction failed: {resp.message}")
        return np.asarray(resp.action, dtype=np.float32), list(resp.joint_names)

    # ---- ergonomic accessors ----

    def commands(self, slot: SlotId) -> "CommandStoreView":
        """Dict-like view of a slot's commands keyed by *name* (not uint id).

        Reads go through :meth:`get_command_float`; writes pick the right
        Float vs Bool RPC based on the Python type of the value. The
        name->id resolution is cached on the view, so tight loops only
        hit ``GetRobotController`` once."""
        return CommandStoreView(self, slot)

    # ---- context managers ----

    @contextmanager
    def policy_slot(self, slot: SlotId, *, active: bool = True):
        """Activate a slot for the duration of a ``with`` block.

        Usage::

            with robot.policy_slot('Walker'):
                robot.commands('Walker')['vx'] = 0.5
                ...

        Restores the slot's prior active state on exit (so nested or
        overlapping uses compose correctly)."""
        prior_state = self.get_state().slot(slot)
        if prior_state is None:
            raise KeyError(f"PolicySlot '{slot}' not found on entity {self._entity_id}")
        prior = prior_state.active
        self.set_policy_active(slot, active)
        try:
            yield self
        finally:
            self.set_policy_active(slot, prior)

    @contextmanager
    def motion_graph_disabled(self):
        """Disable the motion graph for the duration of a ``with`` block.

        Usage::

            with robot.motion_graph_disabled():
                ...   # PolicySlots run without graph gating

        Restores the prior motion-graph active state on exit."""
        prior = self.motion_graph_active
        self.set_motion_graph_active(False)
        try:
            yield self
        finally:
            self.set_motion_graph_active(prior)


# ---------------------------------------------------------------------------
# Dict-like view of a slot's policy commands, keyed by name.
# ---------------------------------------------------------------------------

class CommandStoreView:
    """Dict-like view of a slot's commands keyed by NAME, not uint id.

    Resolves command name -> id via the slot's ``command_id_map`` on first
    use and caches the mapping. Reads return floats (booleans go through
    :meth:`get_bool`); writes choose Float vs Bool by the Python type of
    the assigned value.
    """

    def __init__(self, robot: "RobotController", slot: SlotId) -> None:
        self._robot = robot
        self._slot = slot
        self._name_to_id: dict[str, int] = {}
        self._name_to_type: dict[str, str] = {}

    # ---- internals ----

    def _refresh(self) -> None:
        state = self._robot.get_state().slot(self._slot)
        if state is None:
            raise KeyError(
                f"PolicySlot '{self._slot}' not found on entity {self._robot.entity_id}"
            )
        self._name_to_id = {entry.name: entry.id for entry in state.command_id_map}
        self._name_to_type = {entry.name: entry.type for entry in state.command_id_map}

    def _resolve(self, name: str) -> int:
        if name in self._name_to_id:
            return self._name_to_id[name]
        self._refresh()
        if name not in self._name_to_id:
            raise KeyError(
                f"Unknown policy command '{name}' on slot '{self._slot}'."
            )
        return self._name_to_id[name]

    # ---- Mapping-style surface ----

    def __getitem__(self, name: str) -> float:
        return self._robot.get_command_float(self._slot, self._resolve(name))

    def __setitem__(self, name: str, value: Union[float, bool]) -> None:
        cmd_id = self._resolve(name)
        # ``bool`` is a subclass of ``int`` in Python, so check it first.
        if isinstance(value, bool):
            self._robot.set_command_bool(self._slot, cmd_id, value)
        else:
            self._robot.set_command_float(self._slot, cmd_id, float(value))

    def __contains__(self, name: object) -> bool:
        if not isinstance(name, str):
            return False
        if name in self._name_to_id:
            return True
        try:
            self._refresh()
        except KeyError:
            return False
        return name in self._name_to_id

    def get_bool(self, name: str) -> bool:
        return self._robot.get_command_bool(self._slot, self._resolve(name))

    def keys(self) -> List[str]:
        self._refresh()
        return list(self._name_to_id.keys())

    def items(self) -> List[Tuple[str, float]]:
        self._refresh()
        return [
            (name, self._robot.get_command_float(self._slot, cmd_id))
            for name, cmd_id in self._name_to_id.items()
        ]


# ---------------------------------------------------------------------------
# Top-level discovery helpers (mirrored as Session methods further down).
# ---------------------------------------------------------------------------

def list_robot_controllers(session) -> List[RobotControllerState]:
    """Enumerate every RobotControllerComponent in the active scene."""
    client = session.engine_client
    if client is None:
        raise RuntimeError("Session is not connected.")
    resp = client.agent.ListRobotControllers(_agent_pb2.ListRobotControllersRequest())
    return [RobotControllerState._from_pb(c) for c in resp.controllers]


def list_policy_descriptors(session) -> List[PolicyDescriptorInfo]:
    """Enumerate entries in the project's PolicyRegistry.yaml + their
    descriptor fields (joints, command ids, obs spec)."""
    client = session.engine_client
    if client is None:
        raise RuntimeError("Session is not connected.")
    resp = client.agent.ListPolicyDescriptors(_agent_pb2.ListPolicyDescriptorsRequest())
    return [PolicyDescriptorInfo._from_pb(p) for p in resp.policies]


# ---------------------------------------------------------------------------
# Internal helpers.
# ---------------------------------------------------------------------------

_CMD_TYPE_NAMES = {
    _agent_pb2.POLICY_CMD_FLOAT:  "float",
    _agent_pb2.POLICY_CMD_BOOL:   "bool",
    _agent_pb2.POLICY_CMD_INT:    "int",
    _agent_pb2.POLICY_CMD_UINT:   "uint",
    _agent_pb2.POLICY_CMD_VEC2:   "vec2",
    _agent_pb2.POLICY_CMD_VEC3:   "vec3",
    _agent_pb2.POLICY_CMD_VEC4:   "vec4",
    _agent_pb2.POLICY_CMD_STRING: "string",
}
_CMD_TYPE_FROM_NAME = {v: k for k, v in _CMD_TYPE_NAMES.items()}


def _command_type_to_string(enum_value) -> str:
    return _CMD_TYPE_NAMES.get(enum_value, "float")


def _string_to_command_type(name: str):
    return _CMD_TYPE_FROM_NAME.get(name.lower(), _agent_pb2.POLICY_CMD_FLOAT)
