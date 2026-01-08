#!/usr/bin/env python3
"""
PiperAgent gRPC Random-Control Demo

This demo connects to LuckyEditor running PiperAgent via gRPC and:
  - Fetches the agent schema to discover observation/action layout
  - Streams observations (including camera RGB)
  - Sends random actions each step
  - Extracts and displays camera statistics

Prerequisites:
  1. LuckyEditor running with the gRPC server enabled (GrpcPanel -> Start Server at 0.0.0.0:50051)
  2. RobotSandbox scene loaded with PiperAgent
  3. Python environment with luckyrobots installed: `pip install -e .` from luckyrobots/

Usage:
  python examples/piper_random_control_demo.py [--address 127.0.0.1:50051] [--seconds 10]
"""

from __future__ import annotations

import argparse
import sys
import time
from dataclasses import dataclass
from typing import Optional

import numpy as np

# Add parent dir to path so we can import hazel_rpc_pb2 from repo root
sys.path.insert(0, str(__file__).rsplit("luckyrobots", 1)[0])

try:
    from luckyrobots import AgentEnv, AgentStep, GrpcConfig, GrpcSession
except ImportError:
    # Fallback: try direct import from source
    sys.path.insert(0, str(__file__).rsplit("examples", 1)[0] + "src")
    from luckyrobots import AgentEnv, AgentStep, GrpcConfig, GrpcSession


# =============================================================================
# Piper-specific observation layout
# =============================================================================

@dataclass
class PiperObsLayout:
    """
    Hard-coded observation layout for PiperAgent based on C# ObservationSpec.

    Piper has:
      - 6 joints
      - Camera: 64x48 RGB

    Layout:
      [0 : 6)           joint_pos
      [6 : 12)          joint_vel
      [12 : 18)         last_act
      [18 : 18 + 9216)  cam_main_rgb  (64 * 48 * 3 = 9216)
    """

    num_joints: int = 6
    cam_width: int = 64
    cam_height: int = 48
    cam_channels: int = 3

    @property
    def cam_size(self) -> int:
        return self.cam_width * self.cam_height * self.cam_channels

    @property
    def total_obs_size(self) -> int:
        return 3 * self.num_joints + self.cam_size

    @property
    def joint_pos_slice(self) -> slice:
        return slice(0, self.num_joints)

    @property
    def joint_vel_slice(self) -> slice:
        return slice(self.num_joints, 2 * self.num_joints)

    @property
    def last_act_slice(self) -> slice:
        return slice(2 * self.num_joints, 3 * self.num_joints)

    @property
    def cam_start(self) -> int:
        return 3 * self.num_joints

    @property
    def cam_slice(self) -> slice:
        return slice(self.cam_start, self.cam_start + self.cam_size)

    def extract_camera(self, obs: np.ndarray) -> np.ndarray:
        """Extract and reshape camera data to (H, W, C)."""
        cam_flat = obs[self.cam_slice]
        return cam_flat.reshape(self.cam_height, self.cam_width, self.cam_channels)


PIPER_LAYOUT = PiperObsLayout()


# =============================================================================
# Demo Runner
# =============================================================================

def print_schema_info(env: AgentEnv) -> None:
    """Print agent schema information."""
    schema = env.get_schema()
    print("\n" + "=" * 60)
    print("AGENT SCHEMA")
    print("=" * 60)
    print(f"  Agent Name:       {schema.agent_name}")
    print(f"  Observation Size: {schema.observation_size}")
    print(f"  Action Size:      {schema.action_size}")
    print(f"  Observation Names: {schema.observation_names}")
    print(f"  Action Names:      {schema.action_names}")
    print()

    # Note: The underlying engine may expose a compact telemetry layout (e.g. joint
    # positions / velocities only) or a richer Piper-specific layout including
    # camera pixels. We don't enforce a specific size here; the rest of the demo
    # only relies on the first few joint-related entries for logging.
    print("=" * 60 + "\n")


def print_step_info(step: AgentStep, layout: PiperObsLayout, show_camera_stats: bool = True) -> None:
    """Print per-step debug info."""
    obs = step.observations

    joint_pos = obs[layout.joint_pos_slice]
    joint_vel = obs[layout.joint_vel_slice]
    last_act = obs[layout.last_act_slice]

    pos_str = ", ".join(f"{v:+.3f}" for v in joint_pos)
    vel_str = ", ".join(f"{v:+.3f}" for v in joint_vel)
    act_str = ", ".join(f"{v:+.3f}" for v in last_act)

    print(f"Frame {step.frame_number:5d} | ts={step.timestamp_ms:10d}ms")
    print(f"  joint_pos: [{pos_str}]")
    print(f"  joint_vel: [{vel_str}]")
    print(f"  last_act:  [{act_str}]")

    if show_camera_stats and len(obs) >= layout.cam_start + layout.cam_size:
        cam_img = layout.extract_camera(obs)
        print(f"  cam_rgb:   shape={cam_img.shape}, "
              f"min={cam_img.min():.3f}, max={cam_img.max():.3f}, mean={cam_img.mean():.3f}")
    print()


def run_random_control_demo(
    address: str = "127.0.0.1:50051",
    agent_name: str = "PiperAgent",
    seconds: float = 10.0,
    target_fps: int = 30,
    verbose: bool = True,
) -> None:
    """
    Main demo loop: connect to Piper, stream observations, send random actions.
    """
    print(f"\n[Demo] Connecting to gRPC server at {address}...")

    config = GrpcConfig(address=address, secure=False)
    session = GrpcSession(config)

    try:
        env = AgentEnv(
            agent_name=agent_name,
            session=session,
            robot_name=agent_name,
            target_fps=target_fps,
        )

        # 1. Fetch and display schema
        print_schema_info(env)

        schema = env.get_schema()
        action_size = schema.action_size

        # Piper currently exposes 6 arm joints in its observation layout. We keep
        # the hard-coded Piper layout for printing/debugging only; control
        # commands always use the full action vector reported by the schema.
        layout = PIPER_LAYOUT

        # 2. Reset / get first frame
        print("[Demo] Starting streaming loop (reset)...")
        step = env.reset()
        if verbose:
            print_step_info(step, layout)

        # 3. Random action loop
        print(f"[Demo] Running random control for {seconds:.1f} seconds...")
        t_start = time.time()
        t_end = t_start + seconds
        frame_count = 0

        while time.time() < t_end:
            # Sample random actions in [-1, 1]
            actions = np.random.uniform(-1.0, 1.0, size=(action_size,)).astype(np.float32)

            # Step environment
            step = env.step(actions)
            frame_count += 1

            # Print every N frames
            if verbose and frame_count % 30 == 0:
                print_step_info(step, layout)

        elapsed = time.time() - t_start
        avg_fps = frame_count / elapsed if elapsed > 0 else 0

        print(f"\n[Demo] Completed: {frame_count} frames in {elapsed:.2f}s ({avg_fps:.1f} fps avg)")

    except Exception as e:
        import grpc as grpc_module
        if isinstance(e, grpc_module.RpcError):
            print(f"\n[Error] gRPC error: {e.code()} - {e.details()}")  # type: ignore
        else:
            raise
    finally:
        print("[Demo] Closing session...")
        session.close()


# =============================================================================
# CLI Entry Point
# =============================================================================

def main() -> None:
    parser = argparse.ArgumentParser(
        description="PiperAgent gRPC Random-Control Demo",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--address", "-a",
        default="127.0.0.1:50051",
        help="gRPC server address (default: 127.0.0.1:50051)",
    )
    parser.add_argument(
        "--agent", "-n",
        default="PiperAgent",
        help="Agent name / bridge name (default: PiperAgent)",
    )
    parser.add_argument(
        "--seconds", "-s",
        type=float,
        default=10.0,
        help="Duration to run the demo in seconds (default: 10.0)",
    )
    parser.add_argument(
        "--fps", "-f",
        type=int,
        default=30,
        help="Target FPS for streaming (default: 30)",
    )
    parser.add_argument(
        "--quiet", "-q",
        action="store_true",
        help="Reduce verbosity (only print summary)",
    )

    args = parser.parse_args()

    run_random_control_demo(
        address=args.address,
        agent_name=args.agent,
        seconds=args.seconds,
        target_fps=args.fps,
        verbose=not args.quiet,
    )


if __name__ == "__main__":
    main()

