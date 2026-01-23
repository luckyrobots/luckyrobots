<p align="center">
  <img width="384" alt="Default_Logo_Horizontal@2x" src="https://github.com/user-attachments/assets/ae6ad53a-741e-4e7a-94cb-5a46a8e81398" />
</p>

<p align="center">
   Infinite synthetic data generation for embodied AI
</p>

<!--
<p align="center">
  <a href="https://luckyrobots.github.io/ReleaseV0.1/" target="_blank">
   <img src="https://img.shields.io/badge/Explore_V0.1-Get_Started-grey?style=for-the-badge&labelColor=grey&color=blue" alt="Get Started" />
  </a>
</p>
-->

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

1. **Download LuckyEngine Executable from our [releases page](https://github.com/luckyrobots/luckyrobots/releases/latest) and add its path to your system variables**
   ```bash
   # Set environment variables (choose one method):

   # Method 1: Set LUCKYENGINE_PATH directly to the executable
   export LUCKYENGINE_PATH=/path/to/LuckyEngine.exe  # Windows
   export LUCKYENGINE_PATH=/path/to/LuckyEngine      # Linux/Mac

   # Method 2: Set LUCKYENGINE_HOME to the directory containing the executable
   export LUCKYENGINE_HOME=/path/to/luckyengine/directory
   ```

2. **Create conda environment (recommended)**
   ```bash
   conda create -n luckyrobots python
   conda activate luckyrobots
   ```

3. **Install**
   ```bash
   pip install luckyrobots
   ```

4. **Run Example**
   ```bash
   git clone https://github.com/luckyrobots/luckyrobots.git
   cd luckyrobots/examples
   python controller.py
   ```

## Basic Usage

```python
from luckyrobots import LuckyEngineClient
import numpy as np

client = LuckyEngineClient(host="127.0.0.1", port=50051)
client.connect()

# Send controls (actuator targets depend on the robot you spawned)
client.send_control(controls=[0.1, 0.2, -0.1], robot_name="two_pandas")

# Read back a unified observation snapshot (AgentService.GetObservation)
obs = client.get_observation(
    robot_name="two_pandas",
    include_joint_state=True,
    include_agent_frame=True,
)
print("obs.timestamp_ms:", obs.timestamp_ms)
print("obs.frame_number:", obs.frame_number)
print("obs_vector_len:", len(obs.agent_frame.observations))
```

## Available Robots & Environments

### Robots
- **so100**: 6-DOF manipulator with gripper
- **stretch_v1**: Mobile manipulator
- **dji300**: Quadcopter drone

### Scenes
- **kitchen**: Residential kitchen environment
- **loft**: Open floor plan apartment
- **drone_flight**: Outdoor flight area

### Tasks
- **pickandplace**: Object manipulation
- **navigation**: Path planning and movement

## API Reference

### Core Classes

**LuckyEngineClient**: Direct gRPC client for LuckyEngine
- `wait_for_server(timeout)`: wait until LuckyEngine is reachable
- `send_control(controls, robot_name)`: send actuator controls
- `get_observation(...)`: fetch a unified observation snapshot (server must implement it)

### Observations

Access sensor data from gRPC responses:
```python
obs = client.get_observation(robot_name="two_pandas")
positions = obs.joint_state.positions
velocities = obs.joint_state.velocities
```

## Command Line Interface

```bash
# Basic usage
python controller.py --robot two_pandas --scene ArmLevel --task pickandplace

# Custom rate/host/port
python controller.py --rate 30 --host 192.168.1.100 --port 50051
```

## Configuration

Robot configurations are defined in `src/luckyrobots/config/robots.yaml`:

```yaml
so100:
  action_space:
    actuator_names: [shoulder_pan, shoulder_lift, elbow_flex, wrist_flex, wrist_roll, gripper]
    actuator_limits:
      - name: shoulder_pan
        lower: -2.2
        upper: 2.2
  available_scenes: [kitchen]
  available_tasks: [pickandplace]
```

## Architecture

Lucky Robots is gRPC-only:

- **LuckyEngine**: physics + rendering backend
- **Python client**: connects to LuckyEngine via gRPC (default `127.0.0.1:50051`)

### gRPC Configuration

The Python client connects to LuckyEngine's gRPC server:

```python
client = LuckyEngineClient(host="127.0.0.1", port=50051)
```

The gRPC interface provides access to:
- **SceneService**: Scene inspection and entity manipulation
- **MujocoService**: Joint state queries and control commands
- **AgentService**: RL-style observation/action streaming
- **TelemetryService**: Telemetry data streaming
- **CameraService**: Camera frame streaming
- **ViewportService**: Viewport pixel streaming

## Development

### Setup Development Environment
```bash
git clone https://github.com/luckyrobots/luckyrobots.git
cd luckyrobots
pip install -e .[dev]
```

### Regenerating Python gRPC stubs

The Python gRPC stubs are checked in under `src/luckyrobots/rpc/generated/` and are
generated from the vendored protos under `src/luckyrobots/rpc/proto/`.

```bash
python -m grpc_tools.protoc \
  -I "src/luckyrobots/rpc/proto" \
  --python_out="src/luckyrobots/rpc/generated" \
  --grpc_python_out="src/luckyrobots/rpc/generated" \
  "src/luckyrobots/rpc/proto/common.proto" \
  "src/luckyrobots/rpc/proto/media.proto" \
  "src/luckyrobots/rpc/proto/scene.proto" \
  "src/luckyrobots/rpc/proto/mujoco.proto" \
  "src/luckyrobots/rpc/proto/telemetry.proto" \
  "src/luckyrobots/rpc/proto/agent.proto" \
  "src/luckyrobots/rpc/proto/viewport.proto" \
  "src/luckyrobots/rpc/proto/camera.proto"
```

Note: `grpc_tools.protoc` generates absolute imports in `*_pb2.py` / `*_pb2_grpc.py`.
For this package layout, adjust them to package-relative imports (`from . import ...`).

### Contributing
1. Fork the repository
2. Create a feature branch
3. Make changes and add tests
4. Submit a pull request

## License

MIT License - see [LICENSE](LICENSE) file.

## Support

- **Issues**: [GitHub Issues](https://github.com/luckyrobots/luckyrobots/issues)
- **Discussions**: [GitHub Discussions](https://github.com/luckyrobots/luckyrobots/discussions)
- **Discord**: [Community Server](https://discord.gg/5CH3wx3tAs)
