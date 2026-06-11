"""
Verify NeutralizeActuatorsForTorquePolicy zero/restore behavior.

A policy that consumes torque needs the engine's built-in PD term on
its claimed actuators zeroed for the duration of the slot being active,
and restored on deactivation. This script dumps ``actuator_gains()``
three times — before activation, while the Walker slot is active, and
after deactivation — so the operator can eyeball the zero-then-restore
cycle on the claimed joints.

Run:
    uv run python examples/actuator_gain_inspector.py
"""

from __future__ import annotations

import time

from luckyrobots import Session, RobotController, list_robot_controllers
from luckyrobots.scene import MujocoScene


def _dump(scene: MujocoScene, label: str) -> None:
    gains = scene.actuator_gains()
    print(f"[gains] {label}")
    print(f"{'idx':>4}  {'actuator':<32} {'kp':>10}  {'kv':>10}")
    print("-" * 60)
    for g in gains:
        kp = getattr(g, "kp", 0.0)
        kv = getattr(g, "kv", 0.0)
        name = getattr(g, "name", "")
        idx = getattr(g, "index", -1)
        print(f"{idx:>4}  {name:<32} {kp:>10.4f}  {kv:>10.4f}")
    print()


def main() -> None:
    with Session() as sess:
        sess.connect(timeout_s=30.0)

        controllers = list_robot_controllers(sess)
        if not controllers:
            raise SystemExit("No RobotControllerComponent found in the active scene.")
        state = controllers[0]
        slot_state = state.slot("Walker") or state.slots[0]
        slot_name = slot_state.name
        print(f"[gains] driving slot '{slot_name}' on entity '{state.entity_name}'")

        robot = RobotController.from_state(sess, state)
        scene = MujocoScene(sess)

        _dump(scene, "before activation (XML defaults)")

        robot.set_policy_active(slot_name, True)
        time.sleep(0.5)
        _dump(scene, f"after set_policy_active('{slot_name}', True)")

        robot.set_policy_active(slot_name, False)
        time.sleep(0.5)
        _dump(scene, f"after set_policy_active('{slot_name}', False) — restored")


if __name__ == "__main__":
    main()
