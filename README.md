<p align="center">
  <img width="384" alt="Default_Logo_Horizontal@2x" src="https://github.com/user-attachments/assets/ae6ad53a-741e-4e7a-94cb-5a46a8e81398" />
</p>

<p align="center">
   Infinite synthetic data generation for embodied AI
</p>

<div align="center">

[![PyPI version](https://img.shields.io/pypi/v/luckyrobots.svg)](https://pypi.org/project/luckyrobots/)
[![Documentation](https://img.shields.io/badge/docs-read%20the%20docs-blue)](https://luckyrobots.readthedocs.io)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python Version](https://img.shields.io/pypi/pyversions/luckyrobots)](https://pypi.org/project/luckyrobots/)
[![Status](https://img.shields.io/badge/Status-Alpha-orange)](https://pypi.org/project/luckyrobots/)
[![Discord](https://img.shields.io/badge/Discord-Join%20Server-5865F2?logo=discord&logoColor=white)](https://discord.gg/5CH3wx3tAs)

</div>

https://github.com/user-attachments/assets/0ab2953d-b188-4af7-a225-71decdd2378c

# Lucky Robots

Python SDK for LuckyEngine — a hyperrealistic robotics simulation with MuJoCo physics. Train RL policies with a standard Gymnasium interface, or use the low-level gRPC client for full control.

<p align="center">
  <img width="49%" alt="Bedroom environment in LuckyEngine" src="https://github.com/user-attachments/assets/279a7864-9a8b-453e-8567-3a174f5db8ab" />
  <img width="49%" alt="Open floor plan in LuckyEngine" src="https://github.com/user-attachments/assets/68c72b97-98ab-42b0-a065-8a4247b014c7" />
</p>

## Quick Start

1. **Download LuckyEngine** from our [releases page](https://github.com/luckyrobots/luckyrobots/releases/latest) and set the path:
   ```bash
   export LUCKYENGINE_PATH=/path/to/LuckyEngine      # Linux/Mac
   export LUCKYENGINE_PATH=/path/to/LuckyEngine.exe   # Windows
   ```

2. **Install**
   ```bash
   pip install luckyrobots
   ```

3. **Train a robot in 20 lines**
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

## Three Ways to Use It

### 1. LuckyEnv (Gymnasium interface)

The recommended way to train RL policies. Standard Gymnasium API — works with SB3, skrl, CleanRL, or any Gym-compatible library.

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
)

obs, info = env.reset()
obs, reward, terminated, truncated, info = env.step(action)
# info["reward_signals"] contains per-term engine-computed signals
```

**Key features:**
- Engine computes reward signals and termination flags from MuJoCo state
- You write a `reward_fn` to combine signals into a scalar reward
- `terminated`/`truncated` distinction for proper value function bootstrapping
- Contract negotiation validates your config against engine capabilities at startup

### 2. Session (managed engine lifecycle)

Higher-level wrapper that launches the engine process and manages the connection.

```python
from luckyrobots import Session

with Session() as session:
    session.start(
        scene="velocity",
        robot="unitreego2",
        task="locomotion",
        task_contract={  # Optional: enable engine-side MDP computation
            "rewards": {
                "engine_terms": [{"name": "track_linear_velocity"}],
            },
            "terminations": {
                "terms": [{"name": "fell_over"}, {"name": "time_out", "is_timeout": True}],
            },
        },
    )
    obs = session.step(actions=[0.0] * 12)
    print(obs.reward_signals)  # Engine-computed reward signals
    obs = session.reset()
```

### 3. LuckyEngineClient (low-level gRPC)

Direct gRPC client for full control. Connect to an already-running engine.

```python
from luckyrobots import LuckyEngineClient

client = LuckyEngineClient(host="127.0.0.1", port=50051)
client.connect()
client.wait_for_server()

# Fetch agent schema
schema = client.get_agent_schema()

# RL step
obs = client.step(actions=[0.0] * 12)
print(obs.observation)        # Flat observation vector
print(obs.reward_signals)     # Engine reward signals (if contract negotiated)
print(obs.terminated)         # Episode termination flag

# Discover engine capabilities
manifest = client.get_capability_manifest(robot_name="unitreego2")

# Negotiate task contract
session = client.negotiate_task({
    "task_id": "go2_velocity",
    "robot": "unitreego2",
    "rewards": {"engine_terms": [{"name": "track_linear_velocity"}]},
})

# Reset with domain randomization
client.reset_agent(randomization_cfg={"vel_command_x_range": [-1.0, 1.0]})

client.close()
```

### 4. Engine-wide MuJoCo access (MujocoSceneService)

The default `MujocoService` is **agent-scoped** — `get_joint_state()` returns
only the joints the registered `RobotAgent` has declared. On a humanoid with a
7-joint command abstraction that's 7 values, not the ~41 physical joints.

For full-model access (every joint, every actuator, `qpos`/`qvel`/`ctrl`),
use the `MujocoSceneService` helpers on `LuckyEngineClient`:

```python
# Introspect the full mjModel
info = client.get_model_info()
print(f"nq={info.nq} nv={info.nv} nu={info.nu} njnt={info.njnt}")

# Find a specific subsystem (e.g. the fingers)
fingers = [j for j in info.joints if "finger" in j.name.lower()]

# Read the complete state
state = client.get_full_state().state
print(state.qpos[:5], state.time)

# Drive arbitrary actuators — by name, index, or bulk
client.set_ctrl({"R_thumb_distal": 0.3, "L_index_proximal": -0.1})
client.set_ctrl({0: 0.1, 3: -0.2})
client.set_ctrl([0.0] * info.nu)

# Stream at target FPS
for frame in client.stream_full_state(target_fps=60):
    ...
```

`set_ctrl` is **safety-gated**: writes to actuators owned by a live RL agent
are rejected and reported in `response.rejected_actuators` rather than racing
the policy silently. Values are clamped to each actuator's ctrl range by
default (pass `skip_range_clamp=True` to disable).

### 5. Runtime discovery + extension

The engine registers `grpc.reflection.v1alpha.ServerReflection` (default on),
so the client never needs hard-coded service knowledge:

```python
client.discover_services()
# → ['hazel.rpc.AgentService', 'hazel.rpc.MujocoSceneService', ...]

from luckyrobots.reflection import describe_service
svc = describe_service(client.channel, "hazel.rpc.MujocoSceneService")
print([m.name for m in svc.methods])

# Attach a third-party stub to the same channel
from mypkg.grpc import my_pb2_grpc
client.register_stub("my_service", my_pb2_grpc.MyServiceStub)
client.my_service.DoThing(request, timeout=5.0)
```

Service stubs are **lazy** — each of `client.scene`, `client.mujoco`,
`client.mujoco_scene`, `client.agent`, `client.camera`, `client.debug` is only
instantiated on first access, so pulling in unused ones costs nothing.
`client.channel` is public if you want to bypass the wrappers entirely.

## API Reference

### LuckyEnv

| Method | Description |
|--------|-------------|
| `LuckyEnv(robot, scene, reward_fn, reward_terms, termination_terms, ...)` | Create Gymnasium env |
| `reset(seed, options)` | Reset environment, returns `(obs, info)` |
| `step(action)` | Step environment, returns `(obs, reward, terminated, truncated, info)` |
| `close()` | Disconnect from engine |

**Constructor parameters:**
- `reward_fn`: `Callable[[dict[str, float]], float]` — combines engine signals into scalar reward
- `reward_terms`: List of engine reward signal names to request
- `termination_terms`: List of engine termination condition names
- `observation_terms`: List of observation terms (optional, uses agent defaults if omitted)
- `host`, `port`, `timeout`: Connection settings

### LuckyEngineClient

| Method | Description |
|--------|-------------|
| `connect()` | Open gRPC channel (stubs created lazily) |
| `wait_for_server(timeout)` | Wait for engine to be ready |
| `step(actions, action_groups=...)` | Send actions + physics step + get observation |
| `reset_agent(agent_name, randomization_cfg)` | Reset agent with optional domain randomization |
| `get_agent_schema()` | Get observation/action names and sizes |
| `get_capability_manifest(robot_name)` | Discover available MDP components |
| `negotiate_task(contract)` | Validate and configure engine for task contract |
| `set_simulation_mode(mode)` | Set timing: `"fast"`, `"realtime"`, `"deterministic"` |
| `configure_cameras(cameras)` | Set up camera capture per step |
| `list_cameras()` | Discover cameras in the scene |
| `set_action_group(group_name, actions, indices)` | Preload actions for multi-policy control |
| **`get_model_info()`** | Full mjModel (every joint + actuator) |
| **`get_full_state(include_qpos=, include_qvel=, include_ctrl=)`** | Snapshot full `qpos`/`qvel`/`ctrl` |
| **`stream_full_state(target_fps=30, ...)`** | Server-streamed full state |
| **`set_ctrl(values_or_dict)`** | Write actuator control (safety-gated) |
| **`list_all_joints()` / `list_all_actuators()`** | Lightweight dict view over the model |
| **`discover_services()`** | List services the server advertises via reflection |
| **`register_stub(name, stub_cls)`** | Attach a third-party stub to the same channel |
| `channel` (property) | The underlying `grpc.Channel` — use for custom stubs |
| `benchmark(duration, method)` | Measure step RPC latency |
| `close()` | Disconnect |

**Stub attributes** (lazy): `client.agent`, `client.scene`, `client.mujoco`,
`client.mujoco_scene`, `client.camera`, `client.debug`.

### Session

| Method | Description |
|--------|-------------|
| `start(scene, robot, task, task_contract)` | Launch engine + connect + negotiate contract |
| `connect(robot)` | Connect to already-running engine |
| `step(actions)` | RL step |
| `reset(randomization_cfg)` | Reset agent |
| `close(stop_engine)` | Disconnect and optionally stop engine |

### ObservationResponse

Returned by `step()`, `reset()`, and `get_observation()`.

```python
obs.observation          # List[float] — flat RL observation vector
obs.actions              # List[float] — last applied actions
obs.timestamp_ms         # int — wall-clock timestamp
obs.frame_number         # int — monotonic counter
obs.camera_frames        # List[CameraFrame] — synchronized camera images
obs.reward_signals       # Dict[str, float] — engine-computed reward signals
obs.terminated           # bool — hard termination (episode failure)
obs.truncated            # bool — soft termination (time limit)
obs.termination_flags    # Dict[str, bool] — per-condition flags
obs.info                 # Dict[str, float] — auxiliary diagnostics
obs["name"]              # Named access (if schema fetched)
obs.to_dict()            # Convert to name->value dict
```

### Available Engine MDP Components

**Observations:** `base_lin_vel`, `base_ang_vel`, `projected_gravity`, `joint_pos`, `joint_vel`, `vel_command`, `foot_contact`, `foot_heights`, `foot_contact_forces`, `actions`

**Reward signals:** `track_linear_velocity`, `track_angular_velocity`, `lin_vel_z_penalty`, `ang_vel_xy_penalty`, `joint_acc_penalty`, `feet_air_time`, `orientation_error`, `action_rate`, `action_magnitude`, `foot_slip_penalty`, `stand_still`

**Termination conditions:** `fell_over`, `time_out`, `illegal_contact`

**Domain randomization:** `friction`, `mass_scale`, `motor_strength`, `motor_offset`, `push_disturbance`, `joint_position_noise`, `joint_velocity_noise`, `pose_position_noise`, `pose_orientation_noise`

Use `client.get_capability_manifest()` to discover all available components at runtime.

### Runtime gRPC discovery

Independently of the MDP capability manifest, the engine advertises its gRPC
service surface via `grpc.reflection.v1alpha.ServerReflection`:

```python
client.discover_services()
# → ['hazel.rpc.AgentService', 'hazel.rpc.CameraService',
#    'hazel.rpc.MujocoSceneService', 'hazel.rpc.MujocoService', ...]

from luckyrobots.reflection import describe_service
svc = describe_service(client.channel, "hazel.rpc.MujocoSceneService")
for m in svc.methods:
    print(m.name, m.input_type.full_name, "->", m.output_type.full_name)
```

Useful when the installed SDK predates a server-side service you want to poke at.

## Available Robots & Scenes

| Robot | DOF | Type | Scenes |
|-------|:---:|------|--------|
| `unitreego2` | 12 | Quadruped | velocity |
| `so100` | 6 | Manipulator | pickandplace |
| `piper` | 7 | Manipulator | manipulation |

## System Identification (optional)

Calibrate MuJoCo model parameters to match real robot behavior.

```bash
pip install luckyrobots[sysid]

luckyrobots sysid collect --robot unitreego2 --signal chirp --duration 15 -o traj.npz
luckyrobots sysid identify traj.npz -m go2.xml --preset go2:motor -o result.json
luckyrobots sysid apply result.json -m go2.xml -o go2_calibrated.xml
```

## Development

```bash
git clone https://github.com/luckyrobots/luckyrobots.git
cd luckyrobots
uv sync
uv run pytest
```

### Regenerating gRPC Stubs

After modifying `.proto` files:

```bash
python -m grpc_tools.protoc \
  -I src/luckyrobots/grpc/proto \
  --python_out=src/luckyrobots/grpc/generated \
  --grpc_python_out=src/luckyrobots/grpc/generated \
  src/luckyrobots/grpc/proto/*.proto
```

Then fix imports in generated files to be relative (`from . import common_pb2 as ...`).

### Project Structure

```
src/luckyrobots/
├── client.py            # LuckyEngineClient — low-level gRPC client
├── session.py           # Session — managed engine lifecycle
├── lucky_env.py         # LuckyEnv — Gymnasium wrapper with reward_fn
├── debug.py             # Draw helpers (velocity arrows, lines)
├── sim_contract.py      # SimulationContract protobuf builder
├── utils.py             # Robot config, validation
├── models/
│   ├── observation.py   # ObservationResponse (obs + rewards + termination)
│   └── benchmark.py     # BenchmarkResult, FPS
├── engine/              # Engine process management
├── grpc/
│   ├── generated/       # Protobuf stubs (checked in)
│   └── proto/           # .proto source files
├── config/              # Robot configurations (robots.yaml)
└── sysid/               # System identification (optional)
```

## License

MIT License - see [LICENSE](LICENSE) file.

## Support

- **Issues**: [GitHub Issues](https://github.com/luckyrobots/luckyrobots/issues)
- **Discussions**: [GitHub Discussions](https://github.com/luckyrobots/luckyrobots/discussions)
- **Discord**: [Community Server](https://discord.gg/5CH3wx3tAs)
