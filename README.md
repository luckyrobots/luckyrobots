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

```python
from luckyrobots import LuckyEngineClient

# Connect to LuckyEngine
client = LuckyEngineClient(
    host="127.0.0.1",
    port=50051,
    robot_name="unitreego1",
)
client.wait_for_server()

# Optional: Fetch schema for named observation access
client.fetch_schema()

# Get RL observation
obs = client.get_observation()
print(f"Observation: {obs.observation[:5]}...")  # Flat vector for RL
print(f"Timestamp: {obs.timestamp_ms}")

# Named access (if schema fetched)
# obs["proj_grav_x"]  # Access by name
# obs.to_dict()       # Convert to dict

# Send controls
client.send_control(controls=[0.1, 0.2, -0.1, ...])

# Get joint state (separate from RL observation)
joints = client.get_joint_state()
print(f"Positions: {joints.positions}")
print(f"Velocities: {joints.velocities}")
```

## API Overview

### Core Classes

**`LuckyEngineClient`** - Low-level gRPC client
- `wait_for_server(timeout)` - Wait for LuckyEngine connection
- `get_observation()` - Get RL observation vector
- `get_joint_state()` - Get joint positions/velocities
- `send_control(controls)` - Send actuator commands
- `get_agent_schema()` - Get observation/action names and sizes
- `reset_agent()` - Reset agent state

**`LuckyRobots`** - High-level wrapper (launches LuckyEngine)
- `start(scene, robot, task)` - Launch and connect
- `get_observation()` - Get observation
- `step(controls)` - Send controls and get next observation

### Models

```python
from luckyrobots import ObservationResponse, StateSnapshot

# ObservationResponse - returned by get_observation()
obs.observation      # List[float] - flat RL observation vector
obs.actions          # List[float] - last applied actions
obs.timestamp_ms     # int - wall-clock timestamp
obs.frame_number     # int - monotonic counter
obs["name"]          # Named access (if schema fetched)
obs.to_dict()        # Convert to name->value dict
```

## Available Robots & Environments

### Robots
- **unitreego1**: Quadruped robot
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
├── client.py            # LuckyEngineClient (main API)
├── luckyrobots.py       # LuckyRobots high-level wrapper
├── models/              # Pydantic models
│   ├── observation.py   # ObservationResponse, StateSnapshot
│   └── camera.py        # CameraData, CameraShape
├── engine/              # Engine management
├── grpc/                # gRPC internals
│   ├── generated/       # Protobuf stubs
│   └── proto/           # .proto files
└── config/              # Robot configurations
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
