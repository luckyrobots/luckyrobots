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

Hyperrealistic robotics simulation framework with Python API for embodied AI training and testing.

<p align="center">
  <img width="49%" alt="Bedroom environment in LuckyEngine" src="https://github.com/user-attachments/assets/279a7864-9a8b-453e-8567-3a174f5db8ab" />
  <img width="49%" alt="Open floor plan in LuckyEngine" src="https://github.com/user-attachments/assets/68c72b97-98ab-42b0-a065-8a4247b014c7" />
</p>

## Quick Start

1. **Download LuckyEngine** from our [releases page](https://github.com/luckyrobots/luckyrobots/releases/latest) and set the path:
   ```bash
   # Set environment variable (choose one method):

   # Method 1: Set LUCKYENGINE_PATH directly to the executable
   export LUCKYENGINE_PATH=/path/to/LuckyEngine      # Linux/Mac
   export LUCKYENGINE_PATH=/path/to/LuckyEngine.exe  # Windows

   # Method 2: Set LUCKYENGINE_HOME to the directory containing the executable
   export LUCKYENGINE_HOME=/path/to/luckyengine/directory
   ```

2. **Install**
   ```bash
   pip install luckyrobots
   ```

3. **Run Example**
   ```bash
   git clone https://github.com/luckyrobots/luckyrobots.git
   cd luckyrobots/examples
   python controller.py --skip-launch  # If LuckyEngine is already running
   ```

## Basic Usage

### Low-level client (direct gRPC)

```python
from luckyrobots import LuckyEngineClient

client = LuckyEngineClient(host="127.0.0.1", port=50051, robot_name="unitreego2")
client.wait_for_server()

# RL step: send action, get observation
obs = client.step(actions=[0.0] * 12)
print(f"Observation: {obs.observation[:5]}...")

# Or separately:
client.send_control(controls=[0.1, 0.2, -0.1, ...])
obs = client.get_observation()
joints = client.get_joint_state()
```

### High-level session (manages engine lifecycle)

```python
from luckyrobots import Session

with Session() as session:
    session.start(scene="velocity", robot="unitreego2", task="locomotion")
    obs = session.step(actions=[0.0] * 12)
    obs = session.reset()
```

## API Overview

### Core Classes

**`LuckyEngineClient`** - Low-level gRPC client
- `wait_for_server(timeout)` - Wait for LuckyEngine connection
- `step(actions)` - Send actions + physics step + get observation (single RPC)
- `get_observation()` - Get RL observation vector
- `get_joint_state()` - Get joint positions/velocities
- `send_control(controls)` - Send actuator commands
- `get_agent_schema()` - Get observation/action names and sizes
- `reset_agent()` - Reset agent state
- `set_simulation_mode(mode)` - Set timing: "fast", "realtime", "deterministic"
- `benchmark(duration, method)` - Benchmark RPC latency

**`Session`** - Managed session (launches + connects to LuckyEngine)
- `start(scene, robot, task)` - Launch engine and connect
- `connect(robot=)` - Connect to already-running engine
- `step(actions)` - RL step
- `reset()` - Reset agent
- `close()` - Disconnect and stop engine

### Models

```python
from luckyrobots import ObservationResponse

# ObservationResponse - returned by step() and get_observation()
obs.observation      # List[float] - flat RL observation vector
obs.actions          # List[float] - last applied actions
obs.timestamp_ms     # int - wall-clock timestamp
obs.frame_number     # int - monotonic counter
obs["name"]          # Named access (if schema fetched)
obs.to_dict()        # Convert to name->value dict
```

## System Identification (optional)

Calibrate MuJoCo model parameters to match real robot behavior.

```bash
pip install luckyrobots[sysid]
```

### CLI

```bash
# Collect trajectory data from the engine
luckyrobots-sysid collect --robot unitreego2 --signal chirp --duration 15 -o traj.npz

# Identify model parameters
luckyrobots-sysid identify traj.npz -m go2.xml --preset go2:motor -o result.json

# Apply calibrated parameters to create a new model
luckyrobots-sysid apply result.json -m go2.xml -o go2_calibrated.xml

# List available parameter presets
luckyrobots-sysid presets
```

### Python API

```python
from luckyrobots.sysid import identify, apply_params, TrajectoryData, load_preset, chirp

# Generate excitation signal
ctrl = chirp(duration=15.0, dt=0.02, amplitude=0.3, num_joints=12)

# Load recorded trajectory
traj = TrajectoryData.load("trajectory.npz")

# Identify parameters
specs = load_preset("go2", "motor")  # armature, damping, frictionloss per joint
result = identify("go2.xml", traj, specs)

# Apply to MuJoCo XML
apply_params("go2.xml", result, "go2_calibrated.xml")
```

## Available Robots & Environments

### Robots
- **unitreego2**: Unitree Go2 quadruped (12 joints)
- **so100**: 6-DOF manipulator with gripper
- **stretch_v1**: Mobile manipulator

### Scenes
- **velocity**: Velocity control training
- **kitchen**: Residential kitchen environment

### Tasks
- **locomotion**: Walking/movement
- **pickandplace**: Object manipulation

## Development

### Setup with uv (recommended)

```bash
# Clone and enter repo
git clone https://github.com/luckyrobots/luckyrobots.git
cd luckyrobots

# Install uv if you haven't
curl -LsSf https://astral.sh/uv/install.sh | sh

# Create venv and install deps
uv sync

# Run tests
uv run pytest

# Run example
uv run python examples/controller.py --skip-launch
```

### Setup with pip

```bash
git clone https://github.com/luckyrobots/luckyrobots.git
cd luckyrobots
pip install -e ".[dev]"
```

### Regenerating gRPC Stubs

The Python gRPC stubs are in `src/luckyrobots/grpc/generated/` and are
generated from protos in `src/luckyrobots/grpc/proto/`.

```bash
python -m grpc_tools.protoc \
  -I "src/luckyrobots/grpc/proto" \
  --python_out="src/luckyrobots/grpc/generated" \
  --grpc_python_out="src/luckyrobots/grpc/generated" \
  src/luckyrobots/grpc/proto/*.proto
```

### Project Structure

```
src/luckyrobots/
├── client.py            # LuckyEngineClient — low-level gRPC client
├── session.py           # Session — managed engine lifecycle
├── debug.py             # Draw helpers (velocity arrows, lines)
├── sim_contract.py      # Simulation contract → protobuf builder
├── utils.py             # Shared utilities
├── models/              # Data classes
│   ├── observation.py   # ObservationResponse
│   └── benchmark.py     # BenchmarkResult, FPS
├── engine/              # Engine process management
├── grpc/                # gRPC internals
│   ├── generated/       # Protobuf stubs
│   └── proto/           # .proto files
├── config/              # Robot configurations (robots.yaml)
└── sysid/               # System identification (optional)
    ├── trajectory.py    # TrajectoryData (save/load recordings)
    ├── parameters.py    # ParamSpec, get/set MuJoCo params, presets
    ├── sysid.py         # identify() optimizer + SysIdResult
    ├── calibrate.py     # apply_params() to MuJoCo XML
    ├── collector.py     # Collector ABC + EngineCollector
    ├── excitation.py    # Signal generators (chirp, multisine, random_steps)
    └── cli.py           # luckyrobots-sysid CLI
```

### Contributing

1. Fork the repository
2. Create a feature branch
3. Make changes and add tests
4. Run `uv run ruff check .` and `uv run ruff format .`
5. Submit a pull request

## Architecture

Lucky Robots uses gRPC for communication:

- **LuckyEngine**: Physics + rendering backend (Unreal Engine + MuJoCo)
- **Python client**: Connects via gRPC (default `127.0.0.1:50051`)

### gRPC Services

| Service | Status | Description |
|---------|--------|-------------|
| MujocoService | ✅ Working | Joint state, controls |
| AgentService | ✅ Working | Observations, reset |
| SceneService | 🚧 Placeholder | Scene inspection |
| TelemetryService | 🚧 Placeholder | Telemetry streaming |
| CameraService | 🚧 Placeholder | Camera frames |
| ViewportService | 🚧 Placeholder | Viewport pixels |

## License

MIT License - see [LICENSE](LICENSE) file.

## Support

- **Issues**: [GitHub Issues](https://github.com/luckyrobots/luckyrobots/issues)
- **Discussions**: [GitHub Discussions](https://github.com/luckyrobots/luckyrobots/discussions)
- **Discord**: [Community Server](https://discord.gg/5CH3wx3tAs)
