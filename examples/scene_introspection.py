"""
Print the full ownership map and stream a filtered state slice.

Calls ``MujocoScene(sess).model_info()`` and dumps a per-joint table
showing which PolicySlot or RL agent (if any) currently claims each
joint and actuator. Then opens a 5-second filtered ``stream_state``
that only includes policy-claimed joints, so the operator can verify
the StateFilter wiring on the upgraded MujocoSceneService.

Run:
    uv run python examples/scene_introspection.py
"""

from __future__ import annotations

import time

from luckyrobots import Session
from luckyrobots.scene import MujocoScene


def main() -> None:
    with Session() as sess:
        sess.connect(timeout_s=30.0)

        scene = MujocoScene(sess)
        info = scene.model_info()
        print(f"[introspect] nq={info.nq} nv={info.nv} nu={info.nu} njnt={info.njnt}")

        print()
        print(f"{'idx':>4}  {'name':<32} {'type':<8} {'policy_slot':<14} {'rl_agent':<14}")
        print("-" * 76)
        for j in info.joints:
            slot_id = getattr(j, "claimed_by_policy_slot_id", "")
            rl_agent = getattr(j, "claimed_by_rl_agent", "")
            print(f"{j.index:>4}  {j.name:<32} {j.type:<8} "
                  f"{str(slot_id):<14} {str(rl_agent):<14}")

        print()
        print(f"{'idx':>4}  {'actuator':<32} {'policy_slot':<14} {'rl_agent':<14}")
        print("-" * 64)
        for a in info.actuators:
            slot_id = getattr(a, "claimed_by_policy_slot_id", "")
            rl_agent = getattr(a, "claimed_by_rl_agent", "")
            print(f"{a.index:>4}  {a.name:<32} {str(slot_id):<14} {str(rl_agent):<14}")

        # Stream filtered state for ~5 seconds at 10 fps.
        print()
        print("[introspect] streaming policy-claimed joints only for 5s @ 10fps ...")
        deadline = time.perf_counter() + 5.0
        stream = scene.stream_state(
            filter={"include_only_policy_claimed_joints": True},
            target_fps=10,
        )
        for frame in stream:
            included = list(getattr(frame, "included_joint_indices", []) or [])
            qpos = list(getattr(frame, "qpos", []) or [])
            print(f"  qpos_count={len(qpos)} included_joints={len(included)}")
            if time.perf_counter() >= deadline:
                break


if __name__ == "__main__":
    main()
