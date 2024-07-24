# Lucky Robots: Simulated Robot Control System

Welcome to Lucky Robots, a system for simulating and controlling virtual robots. This README will guide you through the setup process and explain the key components.

## Getting Started

To begin using Lucky Robots:


1. if you want to run the examples in this repository: (optional)

```
   git clone https://github.com/luckyrobots/luckyrobots.git
   cd luckyrobots/examples
```
2. Use your fav package manager (optional)
```
   conda create -n lr
   conda activate lr
```

2. Install the package using pip:
```
   pip install luckyrobots
```

3. Run one of the following
```
   python basic_usage.py 
   python yolo_example.py
   python yolo_mac_example.py
```

It will download the binary and will run it for you.

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

To control the robot, send commands using the `lr.send_message()` function. For example, to make the robot's main wheels turn 10 times:

```python
commands = [["W 3600 1"]]  # This makes the main wheels turn 10 times.
```

For multiple commands and to know when a particular one ends, assign an ID field to your command:

```python
commands = [[{"id": 1234, "code": "W 18000 1"}]]
```

If you want to send a whole set of instructions, add multiple arrays. Each array will wait until the previous array finishes. Commands inside one array are executed simultaneously, allowing smoother movements like the robot lifting its arms while moving forward or turning its head while placing an object. 

```python
commands = [["W 1800 1","a 30"],["a 0", "W 1800 1"]]
```

Commands in one list will override previous commands if they conflict. For instance, if you instruct your robot to turn its wheels 20 times, and on the 5th turn, you instruct it again to turn 3 times, the robot will travel a total of 8 revolutions and stop.

To know when a particular batch finishes, give it an ID and listen for that ID:

```python
commands = [
    ["RESET"],
    {"commands": [{"id": 123456, "code": "W 5650 1"}, {"id": 123457, "code": "a 30 1"}], "batchID": "123456"},
    ["A 0 1", "W 18000 1"]
]
lr.send_message(commands)
```

## Starting the Robot

To start the robot simulation, use:

```python
lr.start(binary_path, sendBinaryData=False)
```

Set `sendBinaryData=True` to include file contents in the `robot_output` object.

This launches the robot simulation, allowing you to interact with it using event listeners and control commands.

## Additional CLI Arguments

When running the Lucky Robots binary, you can use the following additional command-line arguments:

1. `--lr-library-dev`: Enables development mode for the Lucky Robots library. Useful for debugging and testing new features. It will symlink ../src/luckyrobots to your current virtual environments site-packages. So you can change the code, and change the behaviour of the library, fix bugs.

2. `--lr-update`: Triggers an update check for the Lucky Robots library and binary. If updates are available, it will prompt for installation.

3. `--lr-verbose`: Enables verbose logging, providing more detailed output about the robot's operations and internal processes.

Example usage:

```bash
python yourfile.py --lr-library-dev --lr-update --lr-verbose
```

You can combine these arguments as needed. These options provide more control over the simulation environment and can be particularly useful for development, troubleshooting, and staying up-to-date with the latest features and improvements.
