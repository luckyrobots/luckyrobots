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
  <img width="49%" alt="Bedroom environment in Lucky World" src="https://github.com/user-attachments/assets/279a7864-9a8b-453e-8567-3a174f5db8ab" />
  <img width="49%" alt="Open floor plan in Lucky World" src="https://github.com/user-attachments/assets/68c72b97-98ab-42b0-a065-8a4247b014c7" />
</p>

## Quick Start

1. **Download Lucky World Executable from our [releases page](https://github.com/luckyrobots/luckyrobots/releases/latest) and add its path to your system variables**
   ```bash
   # Set environment variables (choose one method):

   # Method 1: Set LUCKYWORLD_PATH directly to the executable
   export LUCKYWORLD_PATH=/path/to/LuckyWorld.exe  # Windows
   export LUCKYWORLD_PATH=/path/to/LuckyWorld      # Linux/Mac

   # Method 2: Set LUCKYWORLD_HOME to the directory containing the executable
   export LUCKYWORLD_HOME=/path/to/luckyworld/directory
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
from luckyrobots import LuckyRobots, Node
import numpy as np

# Create controller node
class RobotController(Node):
    async def control_loop(self):
        # Reset environment
        reset_response = await self.reset_client.call(Reset.Request())

        # Send actions
        actuator_values = np.array([0.1, 0.2, -0.1, 0.0, 0.5, 1.0])
        step_response = await self.step_client.call(Step.Request(actuator_values=actuator_values))

        # Access observations
        observation = step_response.observation
        joint_states = observation.observation_state
        camera_data = observation.observation_cameras

# Start simulation
luckyrobots = LuckyRobots()
controller = RobotController()
luckyrobots.register_node(controller)
luckyrobots.start(scene="kitchen", robot="so100", task="pickandplace")
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

**LuckyRobots**: Main simulation manager
- `start(scene, robot, task, observation_type)`: Initialize simulation
- `register_node(node)`: Add controller node
- `spin()`: Run main loop

**Node**: Base class for robot controllers
- `create_client(service_type, service_name)`: Create service client
- `create_service(service_type, service_name, handler)`: Create service server

### Services

**Reset**: Reset robot to initial state
```python
request = Reset.Request(seed=42, options={})
response = await reset_client.call(request)
```

**Step**: Send action and get observation
```python
request = Step.Request(actuator_values=[0.1, 0.2, -0.1])
response = await step_client.call(request)
```

### Observations

Access sensor data from step responses:
```python
# Joint positions and velocities
joint_states = response.observation.observation_state

# Camera images (RGB + depth)
for camera in response.observation.observation_cameras:
    image = camera.image_data  # numpy array
    name = camera.camera_name  # "head_cam", "hand_cam", etc.
```

## Command Line Interface

```bash
# Basic usage
python controller.py --robot so100 --scene kitchen --task pickandplace

# With camera display
python controller.py --show-camera --rate 30

# Custom host/port
python controller.py --host 192.168.1.100 --port 3001
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

Lucky Robots uses a distributed node architecture:

- **Manager Node**: Central message routing
- **LuckyRobots Node**: Simulation interface
- **Controller Nodes**: User-defined robot controllers
- **WebSocket Transport**: Inter-node communication
- **Lucky World**: Physics simulation backend

## Development

### Setup Development Environment
```bash
git clone https://github.com/luckyrobots/luckyrobots.git
cd luckyrobots
pip install -e .
```

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
