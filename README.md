<p align="center">
  <img width="384" alt="Default_Logo_Horizontal@2x" src="https://github.com/user-attachments/assets/ae6ad53a-741e-4e7a-94cb-5a46a8e81398" />
</p>

<p align="center">
   Infinite synthetic data generation for embodied AI
</p>

<div align="center">

[![GitHub stars](https://img.shields.io/github/stars/luckyrobots/luckyrobots?style=social)](https://github.com/luckyrobots/luckyrobots/stargazers)
[![PyPI version](https://img.shields.io/pypi/v/luckyrobots.svg)](https://pypi.org/project/luckyrobots/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python Version](https://img.shields.io/pypi/pyversions/luckyrobots)](https://pypi.org/project/luckyrobots/)
[![Status](https://img.shields.io/badge/Status-Alpha-orange)](https://pypi.org/project/luckyrobots/)
[![Examples](https://img.shields.io/badge/Examples-View_Code-green)](https://github.com/luckyrobots/luckyrobots/tree/main/examples)
[![Discord](https://dcbadge.vercel.app/api/server/5CH3wx3tAs?style=flat)](https://discord.gg/5CH3wx3tAs)

</div>

https://github.com/user-attachments/assets/0ab2953d-b188-4af7-a225-71decdd2378c

## Why Lucky Robots?

Our vision for accessible robotics was born out of trying to teach our kids how to train robots for simple tasks like picking and placing objects. We quickly discovered that existing simulators were either restricted to those with academic affiliations, prohibitively complex, or simply insufficient for modern robotic learning... so we decided to create something better.

We built Lucky Robots to democratize robotic learning. Our platform pairs an intuitive Python API with [Lucky World](https://luckyrobots.com/luckyrobots/luckyworld), our state-of-the-art simulator that levarages UE5's hyperrealistic rendering and MuJoCo's precise physics. This combination makes professional-grade robotic simulation accessible to everyone, with no need for specialized hardware or a PhD-level understanding.

Whether you're a parent inspiring the next generation, a researcher pushing the boundaries of science, or an industry professional developing cutting-edge applications, Lucky Robots was built for you.

<p align="center">
  <img width="49%" alt="Bedroom environment in Lucky World" src="https://github.com/user-attachments/assets/279a7864-9a8b-453e-8567-3a174f5db8ab" />
  <img width="49%" alt="Open floor plan in Lucky World" src="https://github.com/user-attachments/assets/68c72b97-98ab-42b0-a065-8a4247b014c7" />
</p>

## Getting Started

To start building with Lucky Robots:

1. Clone the repository

```bash
git clone https://github.com/luckyrobots/luckyrobots.git
cd luckyrobots/examples
```

2. Create your environment and install

```bash
conda create -n lr python=3.8
conda activate lr
pip install luckyrobots  # or use uv for faster installation
```

3. Run any of the following examples

```bash
python basic_usage.py
python yolo_example.py
python yolo_mac_example.py
python vlm_gpt.py
```

This will automatically download our simulation binary and run it for you.

## Event Listeners

Lucky Robots provides several event listeners to interact with the simulated robot and receive updates on its state:

1. **@lr.on("robot_output")**: Receives robot output, including RGB and depth images, and coordinates.

   Example output:

   ```python
   {
       "body_pos": {"Time": "1720752411", "rx": "-0.745724", "ry": "0.430001", "rz": "0.007442", "tx": "410.410786", "ty": "292.086556", "tz": "0.190011", "file_path": "/.../4_body_pos.txt"},
       "depth_cam1": {"file_path": "/.../4_depth_cam1.jpg"},
       "depth_cam2": {"file_path": "/.../4_depth_cam2.jpg"},
       "hand_cam": {"Time": "1720752411", "rx": "-59.724758", "ry": "-89.132507", "rz": "59.738461", "tx": "425.359645", "ty": "285.063092", "tz": "19.006545", "file_path": "/.../4_hand_cam.txt"},
       "head_cam": {"Time": "1720752411", "rx": "-0.749195", "ry": "0.433544", "rz": "0.010893", "tx": "419.352843", "ty": "292.814832", "tz": "59.460736", "file_path": "/.../4_head_cam.txt"},
       "rgb_cam1": {"file_path": "/.../4_rgb_cam1.jpg"},
       "rgb_cam2": {"file_path": "/.../4_rgb_cam2.jpg"}
   }
   ```
2. **@lr.on("message")**: Decodes messages from the robot to understand its internal state.
3. **@lr.on("start")**: Triggered when the robot starts, allowing for initialization tasks.
4. **@lr.on("tasks")**: Manages the robot's task list.
5. **@lr.on("task_complete")**: Triggered when the robot completes a task.
6. **@lr.on("batch_complete")**: Triggered when the robot completes a batch of tasks.
7. **@lr.on("hit_count")**: Tracks the robot's collisions.

## Controlling the Robot

To control the robot, send commands using the `lr.send_message()` function:

```python
commands = [["W 3600 1"]]  # This makes the main wheels turn 10 times.
```

For multiple commands and to know when a particular one ends, assign an ID field to your command:

```python
commands = [[{"id": 1234, "code": "W 18000 1"}]]
```

If you want to send a whole set of instructions, add multiple command lists. Each command list will wait until the previous command list finishes. Commands inside one list are executed simultaneously, allowing smoother movements like the robot lifting its arms while moving forward or turning its head while placing an object.

```python
commands = [["W 1800 1","a 30"],["a 0", "W 1800 1"]]
```

Commands in one list will override previous commands if they conflict. For instance, if you instruct your robot to turn its wheels 20 times, and on the 5th turn, you instruct it again to turn 3 times, the robot will travel a total of 8 revolutions and stop.

To know when a particular batch of commands finishes, give it an ID and listen for that ID:

```python
commands = [
    ["RESET"],
    {"commands": [{"id": 123456, "code": "W 5650 1"}, {"id": 123457, "code": "a 30 1"}], "batchID": "123456"},
    ["A 0 1", "W 18000 1"]
]
lr.send_message(commands)
```

### Moving the Robots

**Forward/Backward**

- `[DIRECTION] [DISTANCE] [SPEED]` Example: `W 50 1`
  - `[DIRECTION]`: W is forward, S is backward
  - `[DISTANCE]`: Travel distance in centimeters
  - `[SPEED]`: Speed at which motor will react - km/h
  - Send via API: `lr.send_message([["W 50 1"]])`

**Left/Right**

- `[DIRECTION] [DEGREE]` Example: `A 30`
  - `[DIRECTION]`: A is left, D is right
  - `[DEGREE]`: Spin Rotation in degrees
  - Send via API: `lr.send_message([["A 30"]])`

**Reset**

- `RESET`: Resets all positions and rotations to the zero pose
- Send via API: `lr.send_message([["RESET"]])`

### Stretch v1

- `[JOINT][DISTANCE]` Example: `EX1 30`

  - `EX1 10`  (extend 1st joint 10cm outwards)
  - `EX2 -10` (extend 2nd joint 10cm inwards)
  - `EX3 10`  (extend 3rd joint 10cm outwards)
  - `EX4 10`  (extend 4th joint 10cm outwards)
  - Or: `lr.send_message([["EX1 10"]])`, `lr.send_message([["EX2 -10"]])`, etc.
- `U 10` (Up) - Or: `lr.send_message([["U 10"]])`
- `U -10` (Down) - Or: `lr.send_message([["U -10"]])`
- Gripper: `G 5` or `G -10` - Or: `lr.send_message([["G 5"]])` or `lr.send_message([["G -10"]])`
- Hand Cam Angle:

  - `R1 10` - Or: `lr.send_message([["R1 10"]])`
  - `R2 -30` (turn cam) - Or: `lr.send_message([["R2 -30"]])`

### Luck-e v3

- `[JOINT][DEGREE]` Example: `EX1 30`

  - `EX1 20`  (1st rotate the joint 20 degrees)
  - `EX2 -10` (2nd rotate the joint -10 degrees)
  - `EX3 10`  (3rd rotate the joint 10 degrees)
  - `EX4 10`  (4th rotate the joint 10 degrees)
  - Or: `lr.send_message([["EX1 20"]])`, `lr.send_message([["EX2 -10"]])`, etc.
- `U 10` (Up) - Or: `lr.send_message([["U 10"]])`
- `U -10` (Down) - Or: `lr.send_message([["U -10"]])`
- Gripper: `G 5` or `G -10` - Or: `lr.send_message([["G 5"]])` or `lr.send_message([["G -10"]])`
- Hand Cam Angle: `R 10` - Or: `lr.send_message([["R 10"]])`

## Starting the Robot

To start the robot simulation with custom options:

```python
lr.start(binary_path, sendBinaryData=False)
```

Set `sendBinaryData=True` to include file contents in the `robot_output` object.

## What's Next?

* Drones
* VLA demo
* 3D scene reconstruction
* (your idea?)

## Contributing

Contributions are welcome! Check out our [contribution guidelines](https://claude.ai/chat/CONTRIBUTING.md) to get started.

## Join our team?

Absolutely! Show us a few cool things and/or contribute a few PRs - let us know!

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
