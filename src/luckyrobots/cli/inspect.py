"""``luckyrobots inspect <host:port>`` — one-shot diagnostic dump.

Outputs:
  - gRPC services advertised by the server (via reflection.list_services)
  - Whether the policy RPCs are available (via reflection.has_rpc)
  - A snapshot of every RobotControllerComponent + slot states
  - A 1-frame MujocoScene state summary
  - A 1-row table of actuator gains (neutralized flag highlighted)
"""

from __future__ import annotations

import sys


def inspect_main(host: str, port: int) -> int:
    """Run a one-shot diagnostic dump against a LuckyEngine instance.

    Returns process exit code: 0 on success, non-zero on connection / RPC failure.
    """
    # Imports are deferred to the function body so that ``import
    # luckyrobots.cli.inspect`` is cheap and doesn't drag in grpc / Session
    # for callers that don't actually run the command.
    from luckyrobots import Session, list_robot_controllers
    from luckyrobots.reflection import has_rpc, list_services
    from luckyrobots.scene import MujocoScene

    print(f"Connecting to {host}:{port}...")
    try:
        sess = Session(host=host, port=port)
        sess.connect(timeout_s=10.0)
    except Exception as e:
        print(f"  FAILED: {e}", file=sys.stderr)
        return 2

    try:
        with sess:
            channel = sess.engine_client.channel

            print("\nServices:")
            for s in sorted(list_services(channel)):
                print(f"  {s}")

            policy_ok = has_rpc(
                channel, "hazel.rpc.AgentService/SetPolicyDrivenJoints"
            )
            print(
                "\nPolicy RPC support:",
                "available" if policy_ok else "missing",
            )

            print("\nRobot controllers:")
            for ctl in list_robot_controllers(sess):
                print(
                    f"  entity={ctl.entity_id} name={ctl.entity_name!r}"
                    f" motion_graph={ctl.motion_graph_active}"
                )
                for s in ctl.slots:
                    cmd_names = [c.name for c in s.command_id_map]
                    print(
                        f"    slot {s.slot_id} {s.name!r}"
                        f" active={s.active} ready={s.ready}"
                        f" driven={len(s.driven_joints)} cmds={cmd_names}"
                    )

            scene = MujocoScene(sess)
            info = scene.model_info()
            print(
                f"\nModel: nq={info.nq} nv={info.nv} nu={info.nu}"
                f" njnt={info.njnt}"
            )
            policy_owned = sum(
                1 for j in info.joints if j.claimed_by_policy_slot_id
            )
            agent_owned = sum(1 for j in info.joints if j.claimed_by_rl_agent)
            unclaimed = info.njnt - policy_owned - agent_owned
            print(
                f"Joint ownership: {policy_owned} policy-claimed,"
                f" {agent_owned} RL-agent-claimed, {unclaimed} unclaimed"
            )

            gains = scene.actuator_gains()
            neutralized = [g for g in gains if g.neutralized]
            if neutralized:
                print(f"\nNeutralized actuators ({len(neutralized)}):")
                for g in neutralized[:10]:
                    print(f"  {g.actuator_name}  gain={g.gain_prm_0:.3f}")
        return 0
    except Exception as e:
        print(f"\nERROR during inspect: {e}", file=sys.stderr)
        return 3
