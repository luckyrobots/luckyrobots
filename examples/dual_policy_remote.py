"""
Remote mirror of LuckyEditor/RobotSandbox/Assets/Scripts/Source/DualPolicyExample.cs.

Drives two PolicySlots on a single robot over gRPC:
  * Walker  — SetVx command, owns leg+waist joints (higher priority -> primary).
  * Rotator — SetYawRate command, owns arm joints only (via DrivenJoints mask).

Expected engine state before running:
  * The loaded scene has at least one entity with a RobotControllerComponent.
  * That entity has two PolicySlots configured in the inspector:
      - name "Walker",  descriptor resolving to a walker policy
      - name "Rotator", descriptor resolving to a rotator policy
    (Slot names are used — not slot ids — so you don't need to know the ids.)

Run:
    uv run python examples/dual_policy_remote.py
"""

from __future__ import annotations

import time

from luckyrobots import Session, RobotController, list_robot_controllers, list_policy_descriptors


def _find_command_id(slot, name: str) -> int:
    cmd = slot.command_id(name)
    if cmd is None:
        raise RuntimeError(
            f"Policy slot '{slot.name}' has no command named '{name}'. "
            f"Available: {[c.name for c in slot.command_id_map]}"
        )
    return cmd


def main() -> None:
    with Session() as sess:
        # Attach to an already-running editor instance. (If you want this
        # script to also launch the engine, call sess.start(...) instead.)
        sess.connect(timeout_s=30.0)

        # 1) List available policies — sanity check / print for operator.
        descriptors = list_policy_descriptors(sess)
        print(f"[dual_policy] {len(descriptors)} policies in registry:")
        for d in descriptors:
            print(f"  - {d.policy_id}: {d.descriptor_path}")

        # 2) Find the first robot with a RobotControllerComponent.
        controllers = list_robot_controllers(sess)
        if not controllers:
            raise SystemExit("No RobotControllerComponent found in the active scene.")
        state = controllers[0]
        print(f"[dual_policy] Driving entity '{state.entity_name}' (id={state.entity_id}) "
              f"with {len(state.slots)} slots")

        walker_state  = state.slot("Walker")
        rotator_state = state.slot("Rotator")
        if walker_state is None or rotator_state is None:
            raise SystemExit("Expected slots named 'Walker' and 'Rotator'.")

        walker_set_vx      = _find_command_id(walker_state,  "SetVx")
        rotator_set_yawrate = _find_command_id(rotator_state, "SetYawRate")

        # 3) Activate both slots.
        robot = RobotController.from_state(sess, state)
        robot.set_policy_active("Walker",  True)
        robot.set_policy_active("Rotator", True)

        # 4) Drive the commands for a few seconds and print live state.
        for step in range(200):
            phase = step / 50.0
            robot.set_command_float("Walker",  walker_set_vx,      0.5)
            robot.set_command_float("Rotator", rotator_set_yawrate, 1.0 if phase > 2.0 else 0.0)
            if step % 50 == 0:
                live = robot.get_state()
                for s in live.slots:
                    print(f"  slot {s.name}: ready={s.ready} active_id={s.active_policy_id!r} "
                          f"driven_joints={len(s.driven_joints)}")
            time.sleep(0.05)

        # 5) Mid-run mask change on the Rotator — exercises the reseed-on-claim path.
        print("[dual_policy] Narrowing rotator to right_arm_* only …")
        robot.set_driven_joints("Rotator", ["right_arm_*"])
        time.sleep(0.5)

        # 6) Toggle motion graph on and off.
        robot.set_motion_graph_active(False)
        print(f"[dual_policy] motion_graph_active={robot.motion_graph_active}")
        time.sleep(0.5)
        robot.set_motion_graph_active(True)

        # 7) Clean shutdown of both slots.
        robot.set_policy_active("Walker",  False)
        robot.set_policy_active("Rotator", False)


if __name__ == "__main__":
    main()
