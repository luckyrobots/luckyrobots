"""
MujocoScene: Python wrapper for MujocoSceneService over gRPC.

Unlike the per-agent ``MujocoService`` (in ``mujoco.proto``), the
``MujocoSceneService`` exposes the *whole* loaded ``mjModel``/``mjData`` —
every joint, every actuator, the full ``qpos``/``qvel``/``ctrl`` vectors, and
the live actuator gain/bias parameters that PolicySlot torque-policy
neutralization touches.

Quick start::

    from luckyrobots import Session

    with Session() as sess:
        sess.start(scene="Unitree_PickPlace", robot="G1", task="walk")

        scene = sess.scene
        model = scene.model_info()
        print(model.nq, model.nu, [j.name for j in model.joints[:5]])

        snap = scene.state(filter={"include_only_policy_claimed_joints": True})
        print(snap.qpos.shape, snap.included_joint_indices)

        scene.set_control(named={"left_knee_actuator": 0.25})
        scene.set_qpos(indexed={model.joint("torso_z").qpos_adr: 1.05})
"""

from __future__ import annotations

import dataclasses
from typing import Iterator, Mapping, Optional, Sequence, Union

import numpy as np

from ..grpc.generated import common_pb2 as _common_pb2  # noqa: F401  (kept for parity with sibling wrappers)
from ..grpc.generated import mujoco_scene_pb2 as _ms_pb2


# ---------------------------------------------------------------------------
# Joint type enum -> string mapping
# ---------------------------------------------------------------------------

_JOINT_TYPE_NAMES = {
    _ms_pb2.MJ_JNT_FREE:    "free",
    _ms_pb2.MJ_JNT_BALL:    "ball",
    _ms_pb2.MJ_JNT_SLIDE:   "slide",
    _ms_pb2.MJ_JNT_HINGE:   "hinge",
    _ms_pb2.MJ_JNT_UNKNOWN: "unknown",
}


def _joint_type_to_string(enum_value) -> str:
    return _JOINT_TYPE_NAMES.get(enum_value, "unknown")


# ---------------------------------------------------------------------------
# Dataclasses mirroring the proto messages
# ---------------------------------------------------------------------------

NameOrIndex = Union[int, str]


@dataclasses.dataclass(frozen=True)
class JointInfo:
    index: int
    name: str
    type: str             # "free" | "ball" | "slide" | "hinge" | "unknown"
    qpos_adr: int
    qvel_adr: int
    limited: bool
    range_lo: float
    range_hi: float
    claimed_by_policy_slot_id: int   # 0 = none
    claimed_by_rl_agent: bool

    @classmethod
    def _from_pb(cls, pb) -> "JointInfo":
        return cls(
            index=int(pb.index),
            name=pb.name,
            type=_joint_type_to_string(pb.type),
            qpos_adr=int(pb.qpos_adr),
            qvel_adr=int(pb.qvel_adr),
            limited=bool(pb.limited),
            range_lo=float(pb.range_lo),
            range_hi=float(pb.range_hi),
            claimed_by_policy_slot_id=int(pb.claimed_by_policy_slot_id),
            claimed_by_rl_agent=bool(pb.claimed_by_rl_agent),
        )


@dataclasses.dataclass(frozen=True)
class ActuatorInfo:
    index: int
    name: str
    ctrl_limited: bool
    ctrl_range_lo: float
    ctrl_range_hi: float
    target_joint_index: int          # -1 if not joint-transmitted
    claimed_by_policy_slot_id: int
    claimed_by_rl_agent: bool

    @classmethod
    def _from_pb(cls, pb) -> "ActuatorInfo":
        return cls(
            index=int(pb.index),
            name=pb.name,
            ctrl_limited=bool(pb.ctrl_limited),
            ctrl_range_lo=float(pb.ctrl_range_lo),
            ctrl_range_hi=float(pb.ctrl_range_hi),
            target_joint_index=int(pb.target_joint_index),
            claimed_by_policy_slot_id=int(pb.claimed_by_policy_slot_id),
            claimed_by_rl_agent=bool(pb.claimed_by_rl_agent),
        )


@dataclasses.dataclass(frozen=True)
class ActuatorGainInfo:
    actuator_index: int
    actuator_name: str
    gain_prm_0: float
    bias_prm_0: float
    neutralized: bool

    @classmethod
    def _from_pb(cls, pb) -> "ActuatorGainInfo":
        return cls(
            actuator_index=int(pb.actuator_index),
            actuator_name=pb.actuator_name,
            gain_prm_0=float(pb.gain_prm_0),
            bias_prm_0=float(pb.bias_prm_0),
            neutralized=bool(pb.neutralized),
        )


@dataclasses.dataclass(frozen=True)
class ModelInfo:
    nq: int
    nv: int
    nu: int
    njnt: int
    joints: tuple
    actuators: tuple

    @classmethod
    def _from_pb(cls, pb) -> "ModelInfo":
        return cls(
            nq=int(pb.nq),
            nv=int(pb.nv),
            nu=int(pb.nu),
            njnt=int(pb.njnt),
            joints=tuple(JointInfo._from_pb(j) for j in pb.joints),
            actuators=tuple(ActuatorInfo._from_pb(a) for a in pb.actuators),
        )

    def joint(self, name_or_index: NameOrIndex) -> JointInfo:
        """Look up a joint by index (int) or name (str). Raises KeyError on miss."""
        if isinstance(name_or_index, (int, np.integer)):
            idx = int(name_or_index)
            for j in self.joints:
                if j.index == idx:
                    return j
            raise KeyError(f"No joint with index {idx}")
        for j in self.joints:
            if j.name == name_or_index:
                return j
        raise KeyError(f"No joint with name '{name_or_index}'")

    def actuator(self, name_or_index: NameOrIndex) -> ActuatorInfo:
        """Look up an actuator by index (int) or name (str). Raises KeyError on miss."""
        if isinstance(name_or_index, (int, np.integer)):
            idx = int(name_or_index)
            for a in self.actuators:
                if a.index == idx:
                    return a
            raise KeyError(f"No actuator with index {idx}")
        for a in self.actuators:
            if a.name == name_or_index:
                return a
        raise KeyError(f"No actuator with name '{name_or_index}'")


@dataclasses.dataclass(frozen=True)
class FullStateSnapshot:
    qpos: np.ndarray              # always float32, 1-D
    qvel: np.ndarray
    ctrl: np.ndarray
    time: float
    included_joint_indices: Optional[np.ndarray]    # None when no filter applied
    included_actuator_indices: Optional[np.ndarray]
    frame_number: int = 0

    @classmethod
    def _from_pb(cls, resp) -> "FullStateSnapshot":
        state = resp.state
        qpos = np.array(state.qpos, dtype=np.float32)
        qvel = np.array(state.qvel, dtype=np.float32)
        ctrl = np.array(state.ctrl, dtype=np.float32)
        joint_idx = (
            np.array(resp.included_joint_indices, dtype=np.int64)
            if len(resp.included_joint_indices) > 0
            else None
        )
        act_idx = (
            np.array(resp.included_actuator_indices, dtype=np.int64)
            if len(resp.included_actuator_indices) > 0
            else None
        )
        return cls(
            qpos=qpos,
            qvel=qvel,
            ctrl=ctrl,
            time=float(state.time),
            included_joint_indices=joint_idx,
            included_actuator_indices=act_idx,
            frame_number=int(state.frame_number),
        )


# ---------------------------------------------------------------------------
# StateFilter helpers
# ---------------------------------------------------------------------------

_STATE_FILTER_FIELDS = frozenset(
    f.name for f in _ms_pb2.StateFilter.DESCRIPTOR.fields
)


def _build_state_filter(filter_dict: Optional[Mapping[str, object]]):
    """Build a StateFilter proto from a dict, or return None if dict is empty/None.

    Accepts keys matching ``StateFilter`` proto field names:
      - include_only_policy_claimed_joints: bool
      - include_only_unclaimed_joints: bool
      - filter_by_slot_id: uint32
    """
    if not filter_dict:
        return None
    unknown = [k for k in filter_dict if k not in _STATE_FILTER_FIELDS]
    if unknown:
        raise ValueError(
            f"Unknown StateFilter field(s): {unknown}. "
            f"Allowed: {sorted(_STATE_FILTER_FIELDS)}"
        )
    sf = _ms_pb2.StateFilter()
    for k, v in filter_dict.items():
        # Use proto setattr to coerce to the right scalar.
        if isinstance(v, bool):
            setattr(sf, k, bool(v))
        elif isinstance(v, (int, np.integer)):
            setattr(sf, k, int(v))
        else:
            setattr(sf, k, v)
    return sf


# ---------------------------------------------------------------------------
# MujocoScene — main wrapper
# ---------------------------------------------------------------------------

class MujocoScene:
    """Ergonomic wrapper around the MujocoSceneService gRPC surface.

    Mirrors the structural pattern of :class:`RobotController`: a thin object
    that holds a session reference, talks to the engine via a cached stub
    accessor, and returns frozen dataclasses instead of raw protobuf messages.
    """

    def __init__(self, session) -> None:
        self._session = session
        self._cached_model: Optional[ModelInfo] = None
        # Lazy-built name -> index lookups, reset whenever the model is refreshed.
        self._joint_name_to_idx: Optional[dict] = None
        self._actuator_name_to_idx: Optional[dict] = None

    # ---- internals ----

    def _stub(self):
        client = self._session.engine_client
        if client is None:
            raise RuntimeError(
                "Session is not connected — call session.start()/connect() first."
            )
        return client.mujoco_scene

    @staticmethod
    def _check_ok(resp) -> None:
        """Raise RuntimeError when a response carries success=False.

        Matches the convention used by :class:`RobotController._check_ack`.
        """
        if not resp.success:
            raise RuntimeError(resp.message or "MujocoSceneService RPC failed")

    def _ensure_model(self) -> ModelInfo:
        if self._cached_model is None:
            self.model_info(refresh=True)
        return self._cached_model  # type: ignore[return-value]

    def _build_name_caches(self, model: ModelInfo) -> None:
        self._joint_name_to_idx = {j.name: j.index for j in model.joints}
        self._actuator_name_to_idx = {a.name: a.index for a in model.actuators}

    # ---- introspection ----

    def model_info(self, refresh: bool = False) -> ModelInfo:
        """Fetch (and cache) the engine's mjModel summary.

        Pass ``refresh=True`` after a scene change to invalidate the cache.
        """
        if self._cached_model is not None and not refresh:
            return self._cached_model
        resp = self._stub().GetModelInfo(_ms_pb2.GetModelInfoRequest())
        self._check_ok(resp)
        model = ModelInfo._from_pb(resp)
        self._cached_model = model
        self._build_name_caches(model)
        return model

    def joint(self, name_or_index: NameOrIndex) -> JointInfo:
        """Convenience: look up a joint via the cached :class:`ModelInfo`."""
        return self._ensure_model().joint(name_or_index)

    def actuator(self, name_or_index: NameOrIndex) -> ActuatorInfo:
        """Convenience: look up an actuator via the cached :class:`ModelInfo`."""
        return self._ensure_model().actuator(name_or_index)

    # ---- state ----

    def state(
        self,
        filter: Optional[Mapping[str, object]] = None,
        include_qpos: bool = True,
        include_qvel: bool = True,
        include_ctrl: bool = True,
    ) -> FullStateSnapshot:
        """Fetch a single ``FullState`` snapshot.

        ``filter`` is a dict matching :class:`StateFilter` proto fields::

            {"include_only_policy_claimed_joints": True}
            {"filter_by_slot_id": 1}

        When ``filter`` is ``None`` or empty the request is sent without a
        filter and the response covers the entire model.
        """
        req = _ms_pb2.GetFullStateRequest(
            include_qpos=bool(include_qpos),
            include_qvel=bool(include_qvel),
            include_ctrl=bool(include_ctrl),
        )
        sf = _build_state_filter(filter)
        if sf is not None:
            req.filter.CopyFrom(sf)
        resp = self._stub().GetFullState(req)
        self._check_ok(resp)
        return FullStateSnapshot._from_pb(resp)

    def stream_state(
        self,
        filter: Optional[Mapping[str, object]] = None,
        target_fps: int = 30,
        include_qpos: bool = True,
        include_qvel: bool = True,
        include_ctrl: bool = True,
    ) -> Iterator[FullStateSnapshot]:
        """Server-streaming variant of :meth:`state`.

        Yields :class:`FullStateSnapshot` instances at roughly ``target_fps``.
        """
        req = _ms_pb2.StreamFullStateRequest(
            target_fps=int(target_fps),
            include_qpos=bool(include_qpos),
            include_qvel=bool(include_qvel),
            include_ctrl=bool(include_ctrl),
        )
        sf = _build_state_filter(filter)
        if sf is not None:
            req.filter.CopyFrom(sf)
        for resp in self._stub().StreamFullState(req):
            # Stream RPCs return GetFullStateResponse messages too — they may
            # carry success=False if the engine wants to signal an error mid-stream.
            if not resp.success:
                raise RuntimeError(resp.message or "StreamFullState reported failure")
            yield FullStateSnapshot._from_pb(resp)

    # ---- writes ----

    def set_qpos(
        self,
        bulk: Optional[Sequence[float]] = None,
        indexed: Optional[Mapping[int, float]] = None,
        force: bool = False,
        skip_policy_reseed: bool = False,
    ) -> _ms_pb2.SetQposResponse:
        """Teleport ``qpos`` values in the live ``mjData``.

        Pass ``bulk`` for a whole-vector write, or ``indexed`` for sparse
        ``{qpos_index: value}`` updates. The two may be combined; ``indexed``
        applies on top of ``bulk``.

        ``skip_policy_reseed`` defaults to False — i.e. the engine reseeds
        every active PolicyRuntime's PD targets so the policy doesn't yank the
        robot back. Only set this for raw-teleport diagnostics.
        """
        req = _ms_pb2.SetQposRequest(
            force=bool(force),
            skip_policy_reseed=bool(skip_policy_reseed),
        )
        if bulk is not None:
            # Proto repeated float won't accept ndarray directly.
            if isinstance(bulk, np.ndarray):
                req.bulk.extend(bulk.astype(np.float32).tolist())
            else:
                req.bulk.extend(float(v) for v in bulk)
        if indexed:
            for qpos_idx, value in indexed.items():
                req.indexed.add(qpos_index=int(qpos_idx), value=float(value))
        resp = self._stub().SetQpos(req)
        self._check_ok(resp)
        return resp

    def set_control(
        self,
        bulk: Optional[Sequence[float]] = None,
        indexed: Optional[Mapping[int, float]] = None,
        named: Optional[Mapping[str, float]] = None,
        skip_range_clamp: bool = False,
        wait_for_next_step: bool = False,
    ) -> _ms_pb2.SetControlResponse:
        """Drive arbitrary actuators by bulk vector, index, or actuator name.

        The engine refuses to clobber actuators currently owned by an active
        external RL agent and reports them in ``rejected_actuators`` of the
        response (also surfacing via ``success=False``).
        """
        req = _ms_pb2.SetControlRequest(
            skip_range_clamp=bool(skip_range_clamp),
            wait_for_next_step=bool(wait_for_next_step),
        )
        if bulk is not None:
            if isinstance(bulk, np.ndarray):
                req.bulk.extend(bulk.astype(np.float32).tolist())
            else:
                req.bulk.extend(float(v) for v in bulk)
        if indexed:
            for act_idx, value in indexed.items():
                req.indexed.add(actuator_index=int(act_idx), value=float(value))
        if named:
            for act_name, value in named.items():
                req.named.add(actuator_name=str(act_name), value=float(value))
        resp = self._stub().SetControl(req)
        self._check_ok(resp)
        return resp

    # ---- gain inspection ----

    def actuator_gains(self) -> list:
        """Snapshot of every actuator's ``gainprm[0]`` / ``biasprm[0]`` plus the
        ``neutralized`` flag set by ``NeutralizeActuatorsForTorquePolicy``."""
        resp = self._stub().GetActuatorGains(_ms_pb2.GetActuatorGainsRequest())
        self._check_ok(resp)
        return [ActuatorGainInfo._from_pb(g) for g in resp.actuators]
