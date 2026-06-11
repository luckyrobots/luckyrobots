"""
Unit tests for :class:`luckyrobots.scene.MujocoScene` (Worker A's wrapper).

If the scene module isn't available yet (Workers haven't merged), the file
is skipped at collection time via ``pytest.importorskip`` so the rest of the
suite still collects cleanly.
"""

from __future__ import annotations

import numpy as np
import pytest

# Skip the entire module when Worker A's wrapper hasn't landed yet — keeps
# `pytest --collect-only` clean for the rest of the suite.
mujoco_scene = pytest.importorskip("luckyrobots.scene.mujoco_scene")
ms_pb2 = pytest.importorskip("luckyrobots.grpc.generated.mujoco_scene_pb2")

from luckyrobots.scene import MujocoScene  # noqa: E402


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_model_info_response():
    """A 2-joint, 1-actuator GetModelInfoResponse."""
    resp = ms_pb2.GetModelInfoResponse(
        success=True, message="", nq=8, nv=7, nu=2, njnt=2
    )
    j0 = resp.joints.add()
    j0.index = 0
    j0.name = "left_hip"
    j0.type = ms_pb2.MJ_JNT_HINGE
    j0.qpos_adr = 7
    j0.qvel_adr = 6
    j0.limited = True
    j0.range_lo = -1.5
    j0.range_hi = 1.5
    j0.claimed_by_policy_slot_id = 1
    j0.claimed_by_rl_agent = False

    j1 = resp.joints.add()
    j1.index = 1
    j1.name = "left_knee"
    j1.type = ms_pb2.MJ_JNT_HINGE
    j1.qpos_adr = 8
    j1.qvel_adr = 7
    j1.limited = False
    j1.range_lo = 0.0
    j1.range_hi = 0.0
    j1.claimed_by_policy_slot_id = 0
    j1.claimed_by_rl_agent = True

    a0 = resp.actuators.add()
    a0.index = 0
    a0.name = "left_hip_act"
    a0.ctrl_limited = True
    a0.ctrl_range_lo = -1.0
    a0.ctrl_range_hi = 1.0
    a0.target_joint_index = 0

    a1 = resp.actuators.add()
    a1.index = 1
    a1.name = "left_knee_act"
    a1.ctrl_limited = False
    a1.target_joint_index = 1

    return resp


def _make_full_state_response(included_joints=None, included_actuators=None):
    resp = ms_pb2.GetFullStateResponse(success=True, message="")
    resp.state.qpos.extend([0.1, 0.2, 0.3])
    resp.state.qvel.extend([0.0, 0.0, 0.0])
    resp.state.ctrl.extend([0.5, -0.5])
    resp.state.time = 1.234
    resp.state.frame_number = 99
    if included_joints:
        resp.included_joint_indices.extend(included_joints)
    if included_actuators:
        resp.included_actuator_indices.extend(included_actuators)
    return resp


# ---------------------------------------------------------------------------
# model_info() caching
# ---------------------------------------------------------------------------


def test_model_info_caches(fake_session):
    """Calling model_info() twice without refresh hits the stub once."""
    stub = fake_session.engine_client.mujoco_scene
    stub.GetModelInfo.return_value = _make_model_info_response()

    scene = MujocoScene(fake_session)
    first = scene.model_info()
    second = scene.model_info()

    assert first is second
    assert stub.GetModelInfo.call_count == 1


def test_model_info_refresh_re_fetches(fake_session):
    """``refresh=True`` invalidates the cache and re-hits the stub."""
    stub = fake_session.engine_client.mujoco_scene
    stub.GetModelInfo.return_value = _make_model_info_response()

    scene = MujocoScene(fake_session)
    scene.model_info()
    scene.model_info(refresh=True)

    assert stub.GetModelInfo.call_count == 2


# ---------------------------------------------------------------------------
# state() filter wiring
# ---------------------------------------------------------------------------


def test_state_no_filter_returns_full_arrays(fake_session):
    stub = fake_session.engine_client.mujoco_scene
    stub.GetFullState.return_value = _make_full_state_response()

    scene = MujocoScene(fake_session)
    snap = scene.state()

    assert snap.qpos.shape == (3,)
    assert snap.qvel.shape == (3,)
    assert snap.ctrl.shape == (2,)
    assert snap.included_joint_indices is None
    assert snap.included_actuator_indices is None
    # The request shouldn't carry a populated filter when no dict was passed.
    req = stub.GetFullState.call_args.args[0]
    assert not req.HasField("filter")


def test_state_with_filter_emits_index_arrays(fake_session):
    stub = fake_session.engine_client.mujoco_scene
    stub.GetFullState.return_value = _make_full_state_response(
        included_joints=[0, 4, 7], included_actuators=[1, 2]
    )

    scene = MujocoScene(fake_session)
    snap = scene.state(filter={"include_only_policy_claimed_joints": True})

    assert isinstance(snap.included_joint_indices, np.ndarray)
    assert snap.included_joint_indices.tolist() == [0, 4, 7]
    assert isinstance(snap.included_actuator_indices, np.ndarray)
    assert snap.included_actuator_indices.tolist() == [1, 2]

    req = stub.GetFullState.call_args.args[0]
    assert req.HasField("filter")
    assert req.filter.include_only_policy_claimed_joints is True


# ---------------------------------------------------------------------------
# set_qpos
# ---------------------------------------------------------------------------


def test_set_qpos_indexed_dict(fake_session):
    """Indexed-write should produce one IndexedQposEntry per dict item."""
    stub = fake_session.engine_client.mujoco_scene
    stub.SetQpos.return_value = ms_pb2.SetQposResponse(
        success=True, values_written=2
    )

    scene = MujocoScene(fake_session)
    scene.set_qpos(indexed={2: 1.5, 5: -0.25})

    req = stub.SetQpos.call_args.args[0]
    pairs = sorted((e.qpos_index, e.value) for e in req.indexed)
    assert pairs == [(2, pytest.approx(1.5)), (5, pytest.approx(-0.25))]
    assert len(req.bulk) == 0


def test_set_qpos_skip_policy_reseed_propagates(fake_session):
    """``skip_policy_reseed=True`` should land in the proto request."""
    stub = fake_session.engine_client.mujoco_scene
    stub.SetQpos.return_value = ms_pb2.SetQposResponse(success=True)

    scene = MujocoScene(fake_session)
    scene.set_qpos(indexed={0: 0.0}, skip_policy_reseed=True)

    req = stub.SetQpos.call_args.args[0]
    assert req.skip_policy_reseed is True


# ---------------------------------------------------------------------------
# Actuator gains
# ---------------------------------------------------------------------------


def test_actuator_gains_neutralized_flag_decoded(fake_session):
    stub = fake_session.engine_client.mujoco_scene
    resp = ms_pb2.GetActuatorGainsResponse(success=True)
    a = resp.actuators.add()
    a.actuator_index = 0
    a.actuator_name = "left_hip_act"
    a.gain_prm_0 = 0.0
    a.bias_prm_0 = 0.0
    a.neutralized = True
    b = resp.actuators.add()
    b.actuator_index = 1
    b.actuator_name = "left_knee_act"
    b.gain_prm_0 = 80.0
    b.bias_prm_0 = -2.0
    b.neutralized = False
    stub.GetActuatorGains.return_value = resp

    scene = MujocoScene(fake_session)
    gains = scene.actuator_gains()

    assert len(gains) == 2
    assert gains[0].neutralized is True
    assert gains[0].gain_prm_0 == pytest.approx(0.0)
    assert gains[1].neutralized is False
    assert gains[1].gain_prm_0 == pytest.approx(80.0)


# ---------------------------------------------------------------------------
# Joint lookup parity (name vs. index)
# ---------------------------------------------------------------------------


def test_joint_lookup_by_name_and_index(fake_session):
    stub = fake_session.engine_client.mujoco_scene
    stub.GetModelInfo.return_value = _make_model_info_response()

    scene = MujocoScene(fake_session)
    by_index = scene.joint(0)
    by_name = scene.joint("left_hip")

    assert by_index == by_name
    assert by_name.name == "left_hip"
    assert by_name.qpos_adr == 7
