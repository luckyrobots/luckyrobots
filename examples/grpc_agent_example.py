"""
Minimal example: drive a gRPC-enabled RobotSandbox agent from Python.

Prerequisites:
  - LuckyEditor running with the gRPC server enabled (see GrpcPanel).
  - A scene loaded that contains a gRPC-bridged agent (e.g. PiperAgent).

Notes:
  - On some Windows setups, other software may already bind 127.0.0.1:50051.
    If you see "unknown service hazel.rpc.v1.*", try:
      - changing the LuckyEditor gRPC port (e.g. to 50052), or
      - connecting via your machine's LAN IP (e.g. 192.168.x.x).
"""

import argparse
import time
from typing import Optional

import numpy as np

from luckyrobots import AgentEnv, GrpcConfig, GrpcSession


def run_episode(
    agent_name: str,
    addr: str = "127.0.0.1:50051",
    seconds: float = 5.0,
) -> None:
    cfg = GrpcConfig(address=addr, secure=False)
    session = GrpcSession(cfg)

    env = AgentEnv(agent_name=agent_name, session=session, robot_name=agent_name)
    schema = env.get_schema()
    print(
        f"Connected to agent '{schema.agent_name}' "
        f"(obs={schema.observation_size}, act={schema.action_size})"
    )

    step = env.reset()
    t_end = time.time() + seconds

    while time.time() < t_end:
        # Example: zero actions (hold default pose).
        actions = np.zeros(schema.action_size, dtype=np.float32)
        step = env.step(actions)

        obs_preview = ", ".join(f"{v:.3f}" for v in step.observations[:4])
        print(
            f"frame={step.frame_number} ts={step.timestamp_ms} "
            f"obs[0:4]=[{obs_preview}]"
        )

    session.close()


def main(argv: Optional[list] = None) -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--address", default="127.0.0.1:50051")
    parser.add_argument("--agent-name", default="PiperAgent")
    parser.add_argument("--seconds", type=float, default=5.0)
    args = parser.parse_args(argv)

    run_episode(agent_name=args.agent_name, addr=args.address, seconds=args.seconds)


if __name__ == "__main__":
    main()


