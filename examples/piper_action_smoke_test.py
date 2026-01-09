"""
Smoke test: drive PiperAgent actions over AgentService.SetAgentActions and verify streaming.

This script sends:
  - a small sinusoidal motion on joint1
  - an alternating open/close command on the gripper (last action dim)

Usage:
  python -m examples.piper_action_smoke_test --address 192.168.1.240:50051 --seconds 8
"""

from __future__ import annotations

import argparse
import time

import numpy as np

from luckyrobots import AgentEnv, GrpcConfig, GrpcSession


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--address", default="127.0.0.1:50051")
    parser.add_argument("--agent-name", default="PiperAgent")
    parser.add_argument("--seconds", type=float, default=8.0)
    parser.add_argument("--fps", type=int, default=30)
    args = parser.parse_args(argv)

    session = GrpcSession(GrpcConfig(address=args.address, secure=False))
    try:
        env = AgentEnv(
            agent_name=args.agent_name,
            session=session,
            robot_name=args.agent_name,
            target_fps=args.fps,
        )
        schema = env.get_schema()
        print(
            f"Connected: agent='{schema.agent_name}' obs={schema.observation_size} act={schema.action_size}"
        )

        _ = env.reset()

        t0 = time.time()
        last_print = -1
        while True:
            t = time.time() - t0
            if t >= args.seconds:
                break

            a = np.zeros((schema.action_size,), dtype=np.float32)
            if schema.action_size >= 1:
                # joint1 wiggle (0.5 Hz)
                a[0] = 0.5 * np.sin(2.0 * np.pi * 0.5 * t)

            if schema.action_size >= 7:
                # gripper is last dim; toggle every second
                a[-1] = 1.0 if (int(t) % 2 == 0) else -1.0

            step = env.step(a)

            # Print roughly 5 Hz
            bucket = int(t * 5)
            if bucket != last_print:
                last_print = bucket
                obs0 = ", ".join(f"{v:.3f}" for v in step.observations[:4])
                # PiperAgent observation layout (by design in PiperAgent.cs):
                #   [ joint_pos (N), joint_vel (N), last_act (N + 1) ]
                # where (N + 1) == schema.action_size (arm joints + gripper).
                n_joints = max(0, int(schema.action_size) - 1)
                la_start = 2 * n_joints
                la_end = la_start + int(schema.action_size)
                last_act = step.observations[la_start:la_end] if la_end <= len(step.observations) else []
                la0 = float(last_act[0]) if len(last_act) >= 1 else 0.0
                lag = float(last_act[-1]) if len(last_act) >= 1 else 0.0
                a0 = float(a[0]) if a.size >= 1 else 0.0
                grip = float(a[-1]) if a.size >= 7 else 0.0
                print(
                    f"t={t:5.2f}s frame={step.frame_number:6d} "
                    f"a0={a0: .3f} grip={grip: .1f} "
                    f"last_act0={la0: .3f} last_act_g={lag: .1f} "
                    f"obs[0:4]=[{obs0}]"
                )

        return 0
    finally:
        session.close()


if __name__ == "__main__":
    raise SystemExit(main())


