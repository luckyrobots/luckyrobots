# Lucky Robots: Simulated Robot Control System

Welcome to Lucky Robots, a system for simulating and controlling virtual robots. This README will guide you through the setup process and explain the key components.

## Getting Started

To begin using Lucky Robots:

1. Install the package using pip:
   ```
   pip install luckyrobots
   ```
2. Download the appropriate binary for your operating system: [Binary Download](https://drive.google.com/drive/folders/15iYXzqFNEg1b2E6Ft1ErwynqBMaa0oOa)

## Binary Path Chooser

Download your binary and run it, ensuring HTTP and Capture mode are on.

Set your binary path:

```python
# Linux
binary_path = "/Users/yourname/Downloads/luckyrobots-linux-070824/Linux_07_08_2024"

# macOS - you need to go to system settings, security & privacy and allow this app to run
binary_path = "/Users/yourname/Downloads/LuckEWorld.app" # don't forget the .app

# Windows
binary_path = r"C:\...\LuckEWorld" # don't forget the --> r <-- at the beginning 
```

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
