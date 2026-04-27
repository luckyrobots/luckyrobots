"""
Drive a single PolicySlot with a sweeping SetVx command.

Connects to a running LuckyEngine, finds the first robot with a
RobotControllerComponent, picks the slot named ``Walker`` (or the first
slot if no Walker is present), activates it, and issues a sinusoidal
``SetVx`` command for 200 simulation ticks. Live state snapshots are
printed every 50 steps so the operator can confirm the slot is ready
and the driven-joints mask matches the configured policy.

Run:
    uv run python examples/single_policy_with_commands.py
"""

from __future__ import annotations

import math
import time

from luckyrobots import Session, RobotController, list_robot_controllers


def main() -> None:
    with Session() as sess:
        sess.connect(timeout_s=30.0)

        controllers = list_robot_controllers(sess)
        if not controllers:
            raise SystemExit("No RobotControllerComponent found in the active scene.")
        state = controllers[0]
        print(f"[single_policy] entity='{state.entity_name}' id={state.entity_id} "
              f"slots={[s.name for s in state.slots]}")

        # Prefer a slot literally named "Walker"; fall back to the first slot.
        slot_state = state.slot("Walker") or state.slots[0]
        slot_name = slot_state.name
        set_vx_id = slot_state.command_id("SetVx")
        if set_vx_id is None:
            raise SystemExit(
                f"Slot '{slot_name}' has no SetVx command. "
                f"Available: {[c.name for c in slot_state.command_id_map]}"
            )

        robot = RobotController.from_state(sess, state)
        robot.set_policy_active(slot_name, True)

        try:
            for step in range(200):
                t = step * 0.05
                vx = 0.5 * math.sin(t)
                robot.set_command_float(slot_name, set_vx_id, vx)
                if step % 50 == 0:
                    live = robot.get_state()
                    s = live.slot(slot_name)
                    print(f"  step={step:>3} t={t:5.2f} vx={vx:+.3f} "
                          f"ready={s.ready} active_id={s.active_policy_id!r} "
                          f"driven_joints={len(s.driven_joints)}")
                time.sleep(0.05)
        finally:
            robot.set_policy_active(slot_name, False)


if __name__ == "__main__":
    main()
