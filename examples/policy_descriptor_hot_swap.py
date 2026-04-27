"""
Hot-swap a PolicySlot's descriptor at runtime.

Demonstrates ``set_policy_descriptor`` — the runtime feature that lets a
single PolicySlot cycle through multiple compiled policies without
restarting the simulation. The script discovers up to 3 descriptors via
``list_policy_descriptors``, activates the slot once, and then swaps the
backing descriptor every 200 steps so each policy gets a chance to run.

Run:
    uv run python examples/policy_descriptor_hot_swap.py
"""

from __future__ import annotations

import time

from luckyrobots import (
    Session,
    RobotController,
    list_robot_controllers,
    list_policy_descriptors,
)


def main() -> None:
    with Session() as sess:
        sess.connect(timeout_s=30.0)

        descriptors = list_policy_descriptors(sess)
        if not descriptors:
            raise SystemExit("No policy descriptors registered.")
        # Take up to 3 to cycle through.
        cycle = [d.descriptor_path for d in descriptors[:3]]
        print(f"[hot_swap] cycling {len(cycle)} descriptors:")
        for p in cycle:
            print(f"  - {p}")

        controllers = list_robot_controllers(sess)
        if not controllers:
            raise SystemExit("No RobotControllerComponent found in the active scene.")
        state = controllers[0]
        slot_state = state.slot("Walker") or state.slots[0]
        slot_name = slot_state.name

        robot = RobotController.from_state(sess, state)
        robot.set_policy_active(slot_name, True)

        try:
            for step in range(200 * len(cycle)):
                if step % 200 == 0:
                    descriptor = cycle[(step // 200) % len(cycle)]
                    print(f"[hot_swap] step={step} -> {descriptor}")
                    robot.set_policy_descriptor(slot_name, descriptor)
                time.sleep(0.05)
        finally:
            robot.set_policy_active(slot_name, False)


if __name__ == "__main__":
    main()
