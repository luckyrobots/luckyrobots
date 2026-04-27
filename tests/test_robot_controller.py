"""
Unit tests for :class:`luckyrobots.robots.RobotController`.

No live engine — every RPC goes through a Mock-based fake stub installed on
``session.engine_client.agent`` (see ``conftest.fake_session``). Tests
record calls into the stub's ``call_args_list`` and verify routing, caching,
and oneof selection.
"""

from __future__ import annotations

import pytest

from luckyrobots.robots import (
    PolicySlotState,
    RobotController,
    RobotControllerState,
)
from luckyrobots.grpc.generated import agent_pb2, common_pb2


# ---------------------------------------------------------------------------
# Helpers — build canned protobuf responses
# ---------------------------------------------------------------------------


def _make_controller_pb(entity_id: int = 42, slot_specs=None):
    """Build a RobotControllerSummary proto matching the given slot specs."""
    pb = agent_pb2.RobotControllerSummary(
        entity=common_pb2.EntityId(id=entity_id),
        entity_name="TestRobot",
        motion_graph_active=True,
    )
    for spec in slot_specs or []:
        slot = pb.slots.add()
        slot.slot_id = spec["slot_id"]
        slot.name = spec["name"]
        slot.descriptor_path = spec.get("descriptor_path", "")
        slot.active = spec.get("active", False)
        slot.priority = spec.get("priority", 0)
        slot.driven_joints.extend(spec.get("driven_joints", []))
        slot.clamp_observation_for_unclaimed_joints = spec.get(
            "clamp_observation_for_unclaimed_joints", False
        )
        slot.ready = spec.get("ready", True)
        slot.active_policy_id = spec.get("active_policy_id", "")
        for cmd in spec.get("commands", []):
            entry = slot.command_id_map.add()
            entry.id = cmd["id"]
            entry.name = cmd["name"]
            entry.type = cmd.get("type", agent_pb2.POLICY_CMD_FLOAT)
        slot.policy_joint_names.extend(spec.get("policy_joint_names", []))
    return pb


def _walker_state_response():
    """GetRobotControllerResponse advertising a Walker slot with vx + run cmds."""
    pb = _make_controller_pb(
        entity_id=42,
        slot_specs=[
            {
                "slot_id": 1,
                "name": "Walker",
                "active": False,
                "commands": [
                    {"id": 1, "name": "vx", "type": agent_pb2.POLICY_CMD_FLOAT},
                    {"id": 2, "name": "run", "type": agent_pb2.POLICY_CMD_BOOL},
                ],
            },
            {"slot_id": 2, "name": "Rotator"},
        ],
    )
    return agent_pb2.GetRobotControllerResponse(found=True, controller=pb)


# ---------------------------------------------------------------------------
# Construction & state
# ---------------------------------------------------------------------------


def test_robot_controller_construction(fake_session, fake_agent_stub):
    """Plain construction shouldn't fire any RPCs."""
    rc = RobotController(fake_session, entity_id=42)

    assert rc.entity_id == 42
    # No RPC method should have been called by construction alone.
    for method_name in (
        "GetRobotController",
        "SetPolicyActive",
        "ListRobotControllers",
    ):
        assert not getattr(fake_agent_stub, method_name).called, (
            f"{method_name} was called during construction"
        )


def test_from_state_caches_slot_names(fake_session):
    """from_state should pre-populate the slot-name cache so name lookups
    don't hit the wire."""
    state = RobotControllerState(
        entity_id=99,
        entity_name="Bot",
        motion_graph_active=False,
        slots=(
            PolicySlotState(
                slot_id=7,
                name="Walker",
                descriptor_path="",
                active=False,
                priority=0,
                driven_joints=(),
                clamp_observation_for_unclaimed_joints=False,
                ready=True,
                active_policy_id="",
                command_id_map=(),
                policy_joint_names=(),
            ),
        ),
    )
    rc = RobotController.from_state(fake_session, state)
    assert rc.entity_id == 99
    # Slot name 'Walker' should resolve from cache without any RPC.
    assert rc._resolve_slot("Walker") == 7


# ---------------------------------------------------------------------------
# Slot-name caching: GetRobotController is fetched at most once
# ---------------------------------------------------------------------------


def test_resolve_slot_by_name_caches(fake_session, fake_agent_stub):
    """The first set_policy_active('Walker', ...) should fetch the controller
    state once; subsequent calls reuse the cache."""
    fake_agent_stub.GetRobotController.return_value = _walker_state_response()

    rc = RobotController(fake_session, entity_id=42)
    rc.set_policy_active("Walker", True)
    rc.set_policy_active("Walker", False)

    # Cache hit on the second call -> still only one GetRobotController.
    assert fake_agent_stub.GetRobotController.call_count == 1
    # SetPolicyActive should have been called twice with the resolved id=1.
    calls = fake_agent_stub.SetPolicyActive.call_args_list
    assert len(calls) == 2
    for call, expected_active in zip(calls, [True, False]):
        req = call.args[0]
        assert req.entity.id == 42
        assert req.slot_id == 1
        assert req.active is expected_active


def test_resolve_slot_unknown_raises_keyerror(fake_session, fake_agent_stub):
    """Unknown slot name -> KeyError (after refreshing the cache once)."""
    fake_agent_stub.GetRobotController.return_value = _walker_state_response()

    rc = RobotController(fake_session, entity_id=42)
    with pytest.raises(KeyError, match="Nope"):
        rc.set_policy_active("Nope", True)


# ---------------------------------------------------------------------------
# Motion-graph oneof routing
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "value, expected_field",
    [
        (True, "bool_val"),
        (3, "int_val"),
        (1.5, "float_val"),
        ((0.1, 0.2, 0.3), "vec3_val"),
        ([0.4, 0.5, 0.6], "vec3_val"),
    ],
)
def test_set_motion_graph_input_oneof_routing(
    fake_session, fake_agent_stub, value, expected_field
):
    """Each Python type should land in the matching oneof field of
    MotionGraphInputValue."""
    rc = RobotController(fake_session, entity_id=42)
    rc.set_motion_graph_input(7, value)

    assert fake_agent_stub.SetMotionGraphInput.call_count == 1
    req = fake_agent_stub.SetMotionGraphInput.call_args.args[0]
    assert req.entity.id == 42
    assert req.input_id == 7
    which = req.value.WhichOneof("value")
    assert which == expected_field


def test_set_motion_graph_input_unsupported_type_raises(fake_session):
    """Strings and other unsupported types should raise TypeError."""
    rc = RobotController(fake_session, entity_id=42)
    with pytest.raises(TypeError):
        rc.set_motion_graph_input(0, "hello")


# ---------------------------------------------------------------------------
# CommandStoreView (Worker B)
# ---------------------------------------------------------------------------


def test_command_storeview_setitem_routes_by_type(
    fake_session, fake_agent_stub
):
    """Float -> SetPolicyCommandFloat, bool -> SetPolicyCommandBool."""
    fake_agent_stub.GetRobotController.return_value = _walker_state_response()

    rc = RobotController(fake_session, entity_id=42)
    cmds = rc.commands("Walker")

    cmds["vx"] = 0.75
    cmds["run"] = True

    # Float write
    assert fake_agent_stub.SetPolicyCommandFloat.call_count == 1
    fr = fake_agent_stub.SetPolicyCommandFloat.call_args.args[0]
    assert fr.entity.id == 42
    assert fr.slot_id == 1
    assert fr.command_id == 1
    assert fr.value == pytest.approx(0.75)

    # Bool write
    assert fake_agent_stub.SetPolicyCommandBool.call_count == 1
    br = fake_agent_stub.SetPolicyCommandBool.call_args.args[0]
    assert br.entity.id == 42
    assert br.slot_id == 1
    assert br.command_id == 2
    assert br.value is True

    # Bool path must NOT have hit SetPolicyCommandFloat (and vice versa).
    # ``bool`` is a subclass of ``int``, so this guards the ordering check
    # in :meth:`CommandStoreView.__setitem__`.
    assert fake_agent_stub.SetPolicyCommandFloat.call_count == 1


def test_command_storeview_get_calls_float_rpc(
    fake_session, fake_agent_stub
):
    """Reading a command via ``cmds[name]`` should go through GetPolicyCommandFloat."""
    fake_agent_stub.GetRobotController.return_value = _walker_state_response()
    fake_agent_stub.GetPolicyCommandFloat.return_value = (
        agent_pb2.PolicyCommandFloatValue(success=True, value=1.25)
    )

    rc = RobotController(fake_session, entity_id=42)
    val = rc.commands("Walker")["vx"]

    assert val == pytest.approx(1.25)
    assert fake_agent_stub.GetPolicyCommandFloat.call_count == 1
