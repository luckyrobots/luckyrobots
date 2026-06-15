<p align="center">
  <img width="384" alt="Default_Logo_Horizontal@2x" src="https://github.com/user-attachments/assets/ae6ad53a-741e-4e7a-94cb-5a46a8e81398" />
</p>

<p align="center">
   Python SDK for LuckyEngine — robot, policy, joint and contract-driven RL control over gRPC.
</p>

<div align="center">

[![PyPI version](https://img.shields.io/pypi/v/luckyrobots.svg)](https://pypi.org/project/luckyrobots/)
[![Documentation](https://img.shields.io/badge/docs-read%20the%20docs-blue)](https://luckyrobots.readthedocs.io)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python Version](https://img.shields.io/pypi/pyversions/luckyrobots)](https://pypi.org/project/luckyrobots/)
[![Status](https://img.shields.io/badge/Status-Alpha-orange)](https://pypi.org/project/luckyrobots/)
[![Discord](https://img.shields.io/badge/Discord-Join%20Server-5865F2?logo=discord&logoColor=white)](https://discord.gg/5CH3wx3tAs)

</div>

# Lucky Robots

`luckyrobots` is the Python client for [LuckyEngine](https://github.com/luckyrobots/luckyrobots), a hyperrealistic MuJoCo-based simulator. It mirrors every gRPC surface the engine exposes — robots and policies, joints and actuators, motion graphs and IK, RL contracts, telemetry, cameras, viewports — with discovery built in. List robots, list policies, list joints with their ownership, drive policy commands, pump arbitrary actuators, train a Gymnasium env on top, record + replay sessions.

## Demo: LuckyEngine + LeRobot Sim2Real

Record demonstrations in LuckyEngine, train an imitation-learning policy with
[LeRobot](https://github.com/huggingface/lerobot), and deploy the same checkpoint
in LE → Genesis → a real SO-100 — **72% success on the real robot, trained only
on simulator demos**. Full walkthrough, with embedded demo videos, in
[`docs/lerobot-luckyengine-tutorial/`](docs/lerobot-luckyengine-tutorial).

## Install + connect

```bash
pip install luckyrobots
export LUCKYENGINE_PATH=/path/to/LuckyEngine          # Linux/Mac
# set   LUCKYENGINE_PATH=C:\path\to\LuckyEngine.exe   # Windows
```

```python
from luckyrobots import Session

with Session() as sess:
    sess.connect(timeout_s=30.0)
    info = sess.get_model_info()
    print(f"nq={info.nq} nu={info.nu}  joints={len(info.joints)}")
```

`connect()` assumes the gRPC server is already running inside the editor (gRPC Server panel → **Start Server**, then **Play** the scene). Use `sess.start(scene=..., robot=..., task=...)` to launch the engine programmatically instead.

## Train a robot in 20 lines

```python
from luckyrobots import LuckyEnv

def my_reward(signals):
    return (2.0 * signals.get("track_linear_velocity", 0)
            + 1.5 * signals.get("track_angular_velocity", 0)
            - 0.01 * signals.get("action_rate", 0))

env = LuckyEnv(
    robot="unitreego2",
    scene="velocity",
    reward_fn=my_reward,
    reward_terms=["track_linear_velocity", "track_angular_velocity", "action_rate"],
    termination_terms=["fell_over", "time_out"],
)

obs, info = env.reset()
for _ in range(100_000):
    action = policy(obs)
    obs, reward, terminated, truncated, info = env.step(action)
    if terminated or truncated:
        obs, info = env.reset()
```

Engine computes the named reward signals + termination flags inline with each `step()` (server-side, no Python round trips). `reward_fn` combines them into a scalar. Negotiation validates your term list against engine capabilities at startup, so typos surface immediately with actionable suggestions ("did you mean `track_angular_velocity`?").

## The API at a glance

| Surface | Use it for | Backed by |
|---|---|---|
| `LuckyEnv` | Standard Gymnasium training (SB3, skrl, CleanRL) | `AgentService.NegotiateTask` + `Step` |
| `RobotController` | Drive in-engine policy slots + motion graphs | `AgentService` policy bridge |
| `MujocoScene` | Full mjModel introspection + arbitrary actuator writes | `MujocoSceneService` |
| `PolicyEnv` | Gym env where actions are *commands* into a fixed policy | `AgentService.SetPolicyCommandFloat` + `Step` |
| `Session` / `LuckyEngineClient` | Direct gRPC with lazy stubs, custom user services, reflection | All services |
| `PolicyMonitor` | Event-driven callbacks when slot state changes | `StreamRobotController` |
| `SessionRecording` / `record_session` | Capture + replay every Set\*/Get\* RPC | All `Set*`/`Get*` RPCs |
| `StreamMultiplexer` | Time-aligned merge of N concurrent server-streams | Any streaming RPC |
| `AsyncSession` / `AsyncRobotController` | Asyncio-native mirror of the sync surface | Same RPCs, aio channel |
| `set_robot_pose` | Teleport via human-friendly inputs | `MujocoSceneService.SetQpos` |
| `RobotController.set_policy_gains` | Per-joint runtime PD/scale/default override | `AgentService.SetPolicyGains` |
| `Session.reset_scene` / `MujocoScene.reset` | Soft reset to keyframe[0]; recording continues | `MujocoSceneService.ResetScene` |
| `Session.enter_play_mode` / `exit_play_mode` | Editor Edit ↔ Play over gRPC | `SceneService.EnterPlayMode` / `ExitPlayMode` |
| `validate_session`, `has_rpc` | Startup feature-detection + warnings | gRPC reflection |

Discovery is the through-line — every API prefers `list_*` / `get_*` / `discover_*` over hardcoded names.

## `RobotController` — drive in-engine policies

```python
from luckyrobots import Session, RobotController, list_robot_controllers

with Session() as sess:
    sess.connect(timeout_s=30.0)

    for state in list_robot_controllers(sess):
        print(state.entity_name, "motion_graph_active=", state.motion_graph_active)
        for slot in state.slots:
            print(f"  slot {slot.slot_id}: {slot.name} prio={slot.priority} active={slot.active}")
            print(f"    joints={list(slot.policy_joint_names)[:4]}…")
            print(f"    commands={[(c.name, c.type) for c in slot.command_id_map]}")

    robot = sess.robot("G1")                                # by entity tag (str) or numeric id (int)

    # Activate a slot for the duration of a `with` block — the slot's prior
    # active state is restored on exit.
    with robot.policy_slot("Walker"):
        robot.commands("Walker")["SetVx"] = 0.5             # → SetPolicyCommandFloat
        robot.set_driven_joints("Walker", ["pelvis", "left_hip_pitch_joint", ...])
        robot.set_policy_clamp_observation("Walker", True)
        robot.set_policy_priority("Walker", 0)

    # Hot-swap a slot's descriptor without restarting the sim.
    robot.set_policy_descriptor("Walker", "Assets/Policies/Walker_v2/policy_descriptor.walker.json")

    # Disable the motion graph for the duration of a block.
    with robot.motion_graph_disabled():
        ...

    # Diagnostics for tuning / debug.
    base = robot.get_base_pose("Walker")          # (x, y, yaw) in MuJoCo + Hazel frames
    action, joint_names = robot.get_last_action("Walker")  # raw ONNX output

    # Per-joint runtime PD/scale/default override — no descriptor reload.
    # Unset fields keep the descriptor's value; `clear` restores everything.
    robot.set_policy_gains("Walker", {
        "torso":     {"kp": 200.0, "kd": 20.0},
        "left_hip":  {"effort_limit": 60.0},        # leave kp/kd alone
    })
    robot.clear_policy_gains("Walker")
```

The `commands(slot)` mapping view (`CommandStoreView`) is dict-like:

```python
cmds = robot.commands("Walker")
cmds["SetVx"] = 0.5             # auto-detects float vs bool from the value's Python type
cmds["UseSprint"] = True
print("SetVx" in cmds, list(cmds.keys()), cmds.items())
print(cmds["SetVx"], cmds.get_bool("UseSprint"))
```

Live state streams:

```python
for state in robot.stream_state(target_fps=30):           # → AgentService.StreamRobotController
    print(state.motion_graph_active, [s.name for s in state.slots])

for slot_state in robot.stream_slot_state("Walker", 60):   # → AgentService.StreamPolicySlotState
    print(slot_state.active, slot_state.driven_joints[:3])
```

Top-level helpers:

```python
from luckyrobots import list_robot_controllers, list_policy_descriptors

for controller in list_robot_controllers(sess):
    ...

for desc in list_policy_descriptors(sess):                 # PolicyRegistry.yaml entries
    print(desc.policy_id, desc.descriptor_path, list(desc.joints), desc.command_aliases)
```

## `MujocoScene` — full mjModel access

```python
from luckyrobots import Session

with Session() as sess:
    sess.connect(timeout_s=30.0)
    scene = sess.scene                                     # cached MujocoScene

    info = scene.model_info()                              # full mjModel
    print(f"nq={info.nq}  nv={info.nv}  nu={info.nu}  njnt={info.njnt}")

    # Joint + actuator ownership flags surface which slot / RL agent owns each DOF.
    for j in info.joints:
        print(f"{j.name:30s}  range=[{j.range_lo:+.2f},{j.range_hi:+.2f}]  "
              f"slot={j.claimed_by_policy_slot_id}  rl={j.claimed_by_rl_agent}")

    # Look up by name or index (raises KeyError on miss).
    pelvis = info.joint("pelvis_joint")
    motor0 = info.actuator(0)

    # Drive any actuator. Writes targeting RL/policy-owned actuators come back in `rejected_actuators`.
    resp = scene.set_control(named={"R_thumb_distal": 0.3, "L_index_proximal": -0.1})
    print(resp.actuators_written, list(resp.rejected_actuators))

    # State filters — the same shape works on `state(filter=...)` and `stream_state(filter=...)`:
    state_full      = scene.state()
    state_slot1     = scene.state(filter={"filter_by_slot_id": 1})
    state_unclaimed = scene.state(filter={"include_only_unclaimed_joints": True})
    state_owned     = scene.state(filter={"include_only_policy_claimed_joints": True})

    # Stream at target FPS — break to stop. Each FullStateSnapshot is np.float32-backed.
    for snap in scene.stream_state(target_fps=60, filter={"filter_by_slot_id": 1}):
        print(snap.time, snap.qpos.shape, snap.frame_number)

    # Inspect actuator gains (verifies NeutralizeActuatorsForTorquePolicy zeroing per slot).
    for g in scene.actuator_gains():
        print(g.actuator_name, g.gain_prm_0, g.bias_prm_0, g.neutralized)

    # Teleport joint positions. Owned joints require force=True; reseed control unless skip_policy_reseed.
    scene.set_qpos(indexed={pelvis.qpos_adr: 1.0})

    # Soft reset to keyframe[0] / qpos0. Zeroes ctrl/forces, reseeds active
    # PolicyRuntime PD targets so they don't yank the robot back. Recording
    # continues — the next captured frame is tagged with the post_reset bit.
    scene.reset(preserve_time=False)
```

For human-friendly teleporting use the `set_robot_pose` helper:

```python
from luckyrobots import set_robot_pose

set_robot_pose(
    sess.scene,
    base_xyz=(0.0, 0.0, 0.5),
    base_quat=(1.0, 0.0, 0.0, 0.0),                # MuJoCo (w, x, y, z) order
    joint_angles={"left_hip_pitch_joint": 0.3, "right_hip_pitch_joint": 0.3},
    skip_policy_reseed=False,
    force=False,
)
```

## `LuckyEnv` — Gymnasium training

```python
from luckyrobots import LuckyEnv
import numpy as np

env = LuckyEnv(
    robot="unitreego2",
    scene="velocity",
    reward_fn=lambda s: np.exp(-3 * s.get("track_linear_velocity", 0)),
    reward_terms=["track_linear_velocity", "feet_air_time", "orientation_error"],
    termination_terms=["fell_over", "time_out"],
    observation_terms=["base_lin_vel", "base_ang_vel", "joint_pos", "joint_vel"],
    randomization_cfg={"vel_command_x_range": [-1.0, 1.0]},
    max_episode_length_s=20.0,
    auto_start=False,                              # True to launch the engine executable
)
```

Engine-side per step:
- `reward_signals[name]` is computed for each name in `reward_terms`.
- `terminated` is set if any non-timeout termination fires; `truncated` for timeouts.
- `info` and `termination_flags` carry per-term diagnostics.

`observation_space` and `action_space` are `gymnasium.spaces.Box` — works with SB3, skrl, CleanRL, etc.

## `PolicyEnv` — Gym env over policy *commands*

For training a high-level controller on top of a frozen low-level policy. Each `action[i]` is fed in as a `SetPolicyCommandFloat(slot, command_names[i], action[i])` on every step.

```python
from luckyrobots import Session, PolicyEnv

with Session() as sess:
    sess.connect(timeout_s=30.0)
    env = PolicyEnv(
        sess,
        robot_entity_id=42,                        # entity id of the RobotController
        slot="Walker",                             # name or numeric slot id
        command_names=["SetVx", "SetVy", "SetYawRate"],
        reward_fn=lambda step_resp: -((step_resp.observation.observations[6])**2),
        termination_fn=lambda step_resp: False,
        observation_mode="full_state_filtered",    # or "last_action"
        action_low=-1.0, action_high=1.0,
        max_steps=500,
    )
    obs, info = env.reset()
    obs, reward, terminated, truncated, info = env.step([0.5, 0.0, 0.0])
```

`observation_mode`:
- `"last_action"` — the policy's last raw ONNX inference output (cheap; size = policy action dim)
- `"full_state_filtered"` — `[qpos | qvel]` filtered to the slot's claimed joints (richer; size = nq + nv for that slot)

## `LuckyEngineClient` — direct gRPC

```python
from luckyrobots import LuckyEngineClient

client = LuckyEngineClient(host="127.0.0.1", port=50051)
client.connect()
client.wait_for_server(timeout=30.0)

# Discover services dynamically (gRPC reflection enabled by default).
print(client.discover_services())

# Lazy stubs — only instantiated on first access:
client.agent.GetAgentSchema(...)
client.scene.SetSimulationMode(...)
client.mujoco.GetMujocoInfo(...)            # agent-scoped joint state
client.mujoco_scene.GetModelInfo(...)        # full mjModel
client.camera.ListCameras(...)
client.telemetry.StreamTelemetry(...)
client.viewport.GetViewportInfo(...)
client.debug.Draw(...)

# Attach a third-party stub to the same channel, no SDK fork required.
from mypkg.grpc import my_pb2_grpc
client.register_stub("my_service", my_pb2_grpc.MyServiceStub)
client.my_service.DoThing(request, timeout=5.0)
```

`client.pb` is a `SimpleNamespace` exposing every checked-in proto module — `client.pb.scene`, `client.pb.agent`, `client.pb.mujoco`, `client.pb.mujoco_scene`, `client.pb.camera`, `client.pb.debug`, `client.pb.telemetry`, `client.pb.viewport`, `client.pb.media`, `client.pb.common` — for hand-rolling requests.

```python
# Editor lifecycle — async transitions; poll readiness before stepping.
# These are session boundaries, NOT pause/resume — Exit ends the active
# recording session (a new EnterPlayMode starts a fresh one).
client.enter_play_mode()
# ...wait for client.get_agent_schema() to succeed...
client.exit_play_mode()

# Soft scene reset — qpos→keyframe[0]/qpos0, zero ctrl/forces, reseed
# active PolicyRuntimes. Recording continues across the reset; the
# first frame after gets `frame_flags & post_reset` set engine-side.
client.reset_scene(preserve_time=False)
```

`Session` exposes the same three as `sess.enter_play_mode()` / `sess.exit_play_mode()` / `sess.reset_scene(preserve_time=...)`. `AsyncSession` mirrors them as awaitables.

## RL step + reset + multi-policy

```python
schema = client.get_agent_schema()
obs = client.step(actions=[0.0] * schema.schema.action_size)

# Reset with domain randomization between episodes.
client.reset_agent(randomization_cfg={
    "vel_command_x_range": [-1.0, 1.0],
    "vel_command_yaw_range": [-0.5, 0.5],
})

# Multi-policy: stage groups separately, fire atomically on Step.
client.set_action_group("locomotion", actions=[0.5, 0.0, 0.1], action_indices=[0, 1, 2])
client.set_action_group("arm",        actions=[1.0, 0.3, 0.0, 0.5], action_indices=[3, 4, 5, 6])
obs = client.step()                                        # both groups fire in one tick

# Or inline, in a single RPC:
obs = client.step(action_groups=[
    {"group_name": "locomotion", "actions": [0.5, 0.0, 0.1], "action_indices": [0, 1, 2]},
    {"group_name": "arm",        "actions": [1.0, 0.3, 0.0, 0.5], "action_indices": [3, 4, 5, 6]},
])
```

`step()` is the RL primitive: actions in, physics tick, observation out — plus camera frames if you've configured cameras, plus enriched `reward_signals`/`terminated`/`truncated`/`info`/`termination_flags` if you've negotiated a contract.

Optional camera capture per step:

```python
client.configure_cameras([{"name": "FrontCam", "width": 640, "height": 480}])
obs = client.step(actions=[...])                           # obs.camera_frames is populated
```

## Task-contract API

The contract surface is what makes `LuckyEnv` work — and you can use it directly for custom training stacks.

```python
manifest = client.get_capability_manifest(robot_name="unitreego2")
print([r["name"] for r in manifest["rewards"]])
# → ['track_linear_velocity', 'track_angular_velocity', 'feet_air_time', ...]

# Validate before negotiating (dry run; useful for CLI tooling).
result = client.validate_task_contract(my_contract_dict)
for err in result["errors"]:
    print(err["component"], err["term_name"], err["message"], err["suggestion"])
print(result["resolved_optionals"], result["unresolved_optionals"])

# Negotiate — engine validates + configures + returns the resolved layout.
session = client.negotiate_task({
    "task_id": "go2_velocity",
    "robot": "unitreego2",
    "rewards": {"engine_terms": [{"name": "track_linear_velocity", "weight": 2.0}]},
    "terminations": {
        "terms": [{"name": "fell_over"}, {"name": "time_out", "is_timeout": True}],
    },
})
print(session["session_id"], session["reward_terms"], session["termination_terms"])

# Subsequent Step responses now carry reward_signals + terminated + truncated inline.
obs = client.step(actions=[0.0] * 12)
print(obs.reward_signals, obs.terminated, obs.truncated, obs.termination_flags)
```

Custom reward / observation / termination terms are added engine-side by decorating C# static methods with `[MdpReward]`, `[MdpObservation]`, `[MdpTermination]` in any RobotSandbox script — they're discovered automatically and appear in the next `get_capability_manifest()` call. See `LuckyEditor/RobotSandbox/Assets/Scripts/Source/MdpExamples.cs` for the pattern.

## Driving IK from Python

There is no direct cartesian IK RPC yet. The supported path is to author a motion graph that exposes `Vec3` Input nodes wired into `LimbIK.TargetPosition`, then drive those inputs from Python:

```python
robot.set_motion_graph_active(True)
robot.set_motion_graph_input("LeftTarget",  (0.30, 0.90,  0.20))
robot.set_motion_graph_input("RightTarget", (0.30, 0.90, -0.20))
robot.fire_motion_graph_trigger("ResetIKBlend")
```

Inputs and triggers are addressed by name; the graph author and the client agree on those names. (See `policy-ik-test-walkthrough.md` for the full G1 walker + LimbIK setup, including the gotcha that the waist must be claimed by the walker policy, not left to the graph.)

## Validation, reflection, feature detection

```python
warnings = sess.validate()                                 # → list[ValidationWarning]
for w in warnings:
    print(w.severity, w.code, w.message, w.entity_id, w.slot_id)

# Feature-detect at runtime — the right way to write code that works against multiple engine versions.
sess.has_rpc("hazel.rpc.AgentService/SetPolicyCommandFloat")  # True
sess.has_rpc("hazel.rpc.AgentService/NegotiateTask")          # True
```

`validate_session` checks for: missing policy RPCs on the server, empty PolicyRegistry, slots referencing descriptors not in the registry, slots with unknown driven joints, duplicate priorities on the same robot, slots with commands but inactive — each returns a typed `ValidationWarning(severity, code, message, entity_id, slot_id)`.

## PolicyMonitor — event-driven slot observer

```python
monitor = sess.policy_monitor(entity_id=robot.entity_id, target_fps=30)

@monitor.on_active_change
def _(slot, was, now):
    print(f"{slot.name} active: {was} → {now}")

@monitor.on_descriptor_swap
def _(slot, old, new):
    print(f"{slot.name} descriptor: {old} → {new}")

@monitor.on_joint_claim_change
def _(slot, added, removed):
    print(f"{slot.name} joints: +{added} -{removed}")

@monitor.on_motion_graph_active_change
def _(was, now):
    print(f"motion graph: {was} → {now}")

thread = monitor.run_in_thread()                           # daemon — keeps invoking callbacks
# ... do other work ...
monitor.stop()
```

Also `on_ready_change(slot, was, now)` for slot ready-state. Callbacks are wrapped so an exception in one doesn't stop the stream.

## Recording + replay

Two distinct things share the word "recording":

1. **RPC capture/replay** (this SDK). Every `Set*` / `Get*` RPC issued through the session can be captured and replayed:

   ```python
   with sess.record() as rec:
       robot.set_policy_active("Walker", True)
       robot.commands("Walker")["SetVx"] = 0.5
       obs = sess.step(actions=[0.0] * 12)

   print(len(rec.events), "events captured")
   rec.save("run.parquet")                                    # or "run.jsonl"

   later = SessionRecording.load("run.parquet")
   later.replay(sess, speed=1.0)                              # re-issue at original timestamps
   ```

   `SessionRecording.events` is a list of `RecordedEvent(timestamp_s, rpc, request_json, response_json)`.

2. **Episode/Parquet recording** (engine-side). The engine writes per-substep `qpos` / `ctrl` rows to Parquet under `data/chunk-XXX/file-YYY.parquet`. As of LuckyEngine `mick/policy-fixes` each row carries a `frame_flags : uint8` bit-packed column:

   | Bit | Mask | Meaning |
   |---|---|---|
   | 0 | `0x01` | `new_policy_step` — at least one active slot ran fresh ONNX inference this substep (vs. holding the previous action under decimation). |
   | 1 | `0x02` | `post_reset` — first frame after a `MujocoSceneService.ResetScene` call; `qpos` teleported and `ctrl` was zeroed. |

   ```python
   import pyarrow.compute as pc, pyarrow.parquet as pq
   table = pq.read_table("data/chunk-000/file-000.parquet")
   flags = table["frame_flags"]
   # Drop held-action ticks AND drop the post-reset discontinuity row
   fresh = table.filter(pc.and_(
       pc.equal(pc.bit_wise_and(flags, 1), 1),
       pc.equal(pc.bit_wise_and(flags, 2), 0),
   ))
   ```

   The SDK doesn't write these files — the engine does. This SDK only reads them.

## Multiplexed streams

Merge N concurrent server-streams into one timestamp-aligned iterator (handy when training loops want both `StreamRobotController` and `StreamFullState`):

```python
from luckyrobots import StreamMultiplexer

mux = StreamMultiplexer()
mux.add("robot", sess.engine_client.agent.StreamRobotController(req1))
mux.add("state", sess.engine_client.mujoco_scene.StreamFullState(req2))

for batch in mux.run(period_s=0.05, timeout_s=10.0):
    # batch = {"robot": <latest RobotControllerSummary>, "state": <latest FullState>}
    ...

mux.stop()
```

Each input stream runs in a daemon thread with a maxsize-1 queue (drops older items for backpressure); `run()` polls every `period_s` and yields the latest dict.

## Async surface

`AsyncSession` and `AsyncRobotController` mirror the sync surface but use `grpc.aio` channels and `await`-able RPCs.

```python
import asyncio
from luckyrobots import AsyncSession, AsyncRobotController

async def main():
    async with AsyncSession() as sess:
        await sess.connect(timeout_s=30.0)
        controller = AsyncRobotController(sess, entity_id=42)
        async with controller.policy_slot("Walker"):
            await controller.set_command_float("Walker", 0, 0.5)
            for _ in range(100):
                await sess.agent.Step(...)

asyncio.run(main())
```

Same RPC surface, same proto types — only the channel + method calling convention differs.

## Available built-in MDP terms

**Observations:** `base_lin_vel`, `base_ang_vel`, `projected_gravity`, `joint_pos`, `joint_vel`, `vel_command`, `foot_contact`, `foot_heights`, `foot_contact_forces`, `actions`

**Reward signals:** `track_linear_velocity`, `track_angular_velocity`, `lin_vel_z_penalty`, `ang_vel_xy_penalty`, `joint_acc_penalty`, `feet_air_time`, `orientation_error`, `action_rate`, `action_magnitude`, `foot_slip_penalty`, `stand_still`

**Terminations:** `fell_over`, `time_out` (truncation), `illegal_contact`

**Domain randomization:** `friction`, `mass_scale`, `motor_strength`, `motor_offset`, `push_disturbance`, `joint_position_noise`, `joint_velocity_noise`, `pose_position_noise`, `pose_orientation_noise`

Add your own with `[MdpReward]` / `[MdpObservation]` / `[MdpTermination]` decorators in any RobotSandbox C# script — `client.get_capability_manifest()` will pick them up on the next call.

## Known engine limitations

- **No cartesian IK RPC.** Drive IK targets through motion-graph inputs by name (above). There is also no schema RPC listing what inputs / triggers a given motion graph exposes — graph author and client must agree on names.
- **Single viewport.** `ViewportService.GetViewportInfo` always returns `["Main"]` on this engine branch — no multi-viewport spectator support.
- **`SetSimulationMode("realtime")`** is rejected while a gRPC client is connected (the action-gate invariant). Use `"deterministic"` for visualization or `"fast"` for training.
- **`MujocoService.GetMujocoInfo` actuator names mirror joint names.** For full actuator metadata use `MujocoSceneService.GetModelInfo` (i.e. `MujocoScene.model_info()`).

## Available robots & scenes

| Robot | DOF | Type | Scenes |
|---|:---:|---|---|
| `unitreego2` | 12 | Quadruped | velocity |
| `so100` | 6 | Manipulator | pickandplace |
| `piper` | 7 | Manipulator | manipulation |

## System identification (optional)

```bash
pip install luckyrobots[sysid]

luckyrobots sysid presets --robot unitreego2                # list available parameter presets
luckyrobots sysid collect --robot unitreego2 --signal chirp --duration 15 -o traj.npz
luckyrobots sysid identify traj.npz -m go2.xml --preset go2:motor -o result.json
luckyrobots sysid apply result.json -m go2.xml -o go2_calibrated.xml
```

`presets`, `collect`, `identify`, `apply` are the four subcommands.

## Examples

`examples/` ships these scripts. All target the current engine; none require a launched executable beyond the gRPC server being up.

| Script | Demonstrates |
|---|---|
| `single_policy_with_commands.py` | Activate a `Walker` slot, drive `SetVx` from a sine wave, print live state every 50 steps |
| `dual_policy_remote.py` | Remote mirror of `DualPolicyExample.cs` — two slots on one robot (Walker + Rotator) |
| `policy_descriptor_hot_swap.py` | Cycle a slot's descriptor every 200 steps to hot-swap policies without restarting |
| `scene_introspection.py` | Dump the full joint/actuator ownership map; stream a slot-filtered state for 5s |
| `actuator_gain_inspector.py` | Verify `NeutralizeActuatorsForTorquePolicy` zero/restore around slot activation |
| `controller.py` | Minimal baseline: launch + connect + step + periodic reset (no policy slots) |

## Tests

`tests/` ships pytest suites for the four big surfaces:

| File | Covers |
|---|---|
| `test_client.py` | `LuckyEngineClient` lifecycle, lazy stubs, schema cache |
| `test_mujoco_scene.py` | `MujocoScene` model info + state filters + actuator gains |
| `test_robot_controller.py` | `RobotController` state, slot control, command store, motion graph |
| `test_robot_controller_integration.py` | End-to-end policy bridge against a live engine |
| `conftest.py` | Shared fixtures (engine mock, sample state) |

## Development

```bash
git clone https://github.com/luckyrobots/luckyrobots.git
cd luckyrobots
uv sync
uv run pytest
```

### Regenerating gRPC stubs

After modifying `.proto` files in `src/luckyrobots/grpc/proto/`:

```bash
python -m grpc_tools.protoc \
  -I src/luckyrobots/grpc/proto \
  --python_out=src/luckyrobots/grpc/generated \
  --grpc_python_out=src/luckyrobots/grpc/generated \
  src/luckyrobots/grpc/proto/*.proto
```

`grpc_tools.protoc` emits sibling-style `import foo_pb2` lines; rewrite them to `from . import foo_pb2` so the package imports cleanly.

### Project structure

```
src/luckyrobots/
├── __init__.py            # Re-exports the public surface
├── client.py              # LuckyEngineClient — low-level gRPC client + lazy stubs
├── session.py             # Session — managed engine lifecycle + convenience forwards
├── lucky_env.py           # LuckyEnv — Gymnasium env with engine-computed rewards
├── policy_env.py          # PolicyEnv — Gymnasium env over policy slot commands
├── monitor.py             # PolicyMonitor — event-driven RobotController observer
├── recording.py           # SessionRecording / record_session — capture + replay
├── streams.py             # StreamMultiplexer — merge N server-streams
├── poses.py               # set_robot_pose — human-friendly qpos teleporter
├── reflection.py          # has_rpc / supported_services / supported_methods
├── validation.py          # validate_session, ValidationWarning
├── debug.py               # DebugService low-level helpers
├── debug_overlay.py       # draw_policy_overlay — colored arrows per active slot
├── async_session.py       # AsyncSession — aio mirror of Session
├── async_robots.py        # AsyncRobotController — aio mirror of RobotController
├── sim_contract.py        # SimulationContract proto builder
├── utils.py               # Robot config helpers
├── robots/
│   └── robot_controller.py   # RobotController + state classes + CommandStoreView
├── scene/
│   └── mujoco_scene.py       # MujocoScene + JointInfo / ActuatorInfo / ModelInfo
├── models/
│   ├── observation.py     # ObservationResponse (with reward_signals + termination)
│   └── benchmark.py       # BenchmarkResult, FPS
├── engine/                # launch_luckyengine / stop_luckyengine
├── grpc/
│   ├── generated/         # Checked-in protobuf stubs
│   └── proto/             # .proto sources
├── config/                # Robot configurations (robots.yaml)
└── sysid/                 # System identification CLI (collect / identify / apply / presets)
```

## License

MIT License — see [LICENSE](LICENSE).

## Support

- **Issues**: [GitHub Issues](https://github.com/luckyrobots/luckyrobots/issues)
- **Discussions**: [GitHub Discussions](https://github.com/luckyrobots/luckyrobots/discussions)
- **Discord**: [Community Server](https://discord.gg/5CH3wx3tAs)
