"""Integration tests against a live LuckyEngine instance.

Run with: ``pytest -m integration``
Skipped by default (matches existing ``test_client.py`` convention).
"""

from __future__ import annotations

import time

import pytest

from luckyrobots import list_robot_controllers
from luckyrobots.robots import RobotController


@pytest.mark.integration
def test_full_policy_lifecycle(session_connected):
    """Activate Walker -> set Vx command -> verify state reflects activity ->
    deactivate -> confirm fully unloaded.

    Skips if no RobotControllerComponent is present in the loaded scene
    (matches ``test_client.py``'s opt-in skip behaviour)."""
    ctls = list_robot_controllers(session_connected)
    if not ctls:
        pytest.skip("No RobotControllerComponent in the scene.")

    state = ctls[0]
    if not state.slots:
        pytest.skip("RobotControllerComponent has no PolicySlots configured.")

    # Pick the first slot that exposes at least one float command, otherwise
    # fall back to the first slot (we'll only toggle active in that case).
    slot_state = next(
        (
            s
            for s in state.slots
            if any(c.type == "float" for c in s.command_id_map)
        ),
        state.slots[0],
    )

    rc = RobotController.from_state(session_connected, state)
    prior_active = slot_state.active

    # Activate
    rc.set_policy_active(slot_state.slot_id, True)
    # The engine flips ``active`` on the next gameplay tick — give it a beat.
    time.sleep(0.5)
    refreshed = rc.get_state().slot(slot_state.slot_id)
    assert refreshed is not None
    assert refreshed.active is True, "Slot did not report active after enable"

    # If a float command exists, set it via the typed setter and verify.
    float_cmd = next(
        (c for c in slot_state.command_id_map if c.type == "float"), None
    )
    if float_cmd is not None:
        target = 0.25
        rc.set_command_float(slot_state.slot_id, float_cmd.id, target)
        time.sleep(0.1)
        actual = rc.get_command_float(slot_state.slot_id, float_cmd.id)
        assert actual == pytest.approx(target, rel=1e-3, abs=1e-3)

    # Deactivate and verify it falls back to inactive.
    rc.set_policy_active(slot_state.slot_id, False)
    time.sleep(0.5)
    final = rc.get_state().slot(slot_state.slot_id)
    assert final is not None
    assert final.active is False, "Slot did not report inactive after disable"

    # Restore prior state so the test is idempotent.
    if prior_active != final.active:
        rc.set_policy_active(slot_state.slot_id, prior_active)
