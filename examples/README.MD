# Lucky Robots: Simulated Robot Control System

Welcome to Lucky Robots, a system for simulating and controlling virtual robots. This README will guide you through the setup process and explain the key components of the `basic_usage.py` file.

## Getting Started

To begin using Lucky Robots:

1. Install the package using pip:
   ```
   pip install luckyrobots
   ```
2. Download the appropriate binary for your operating system:
    https://drive.google.com/drive/folders/15iYXzqFNEg1b2E6Ft1ErwynqBMaa0oOa

## Binary Path Chooser

First and foremost, download your binary and run it in your system, make sure HTTP and Capture mode is on.

If your binary is running from ~/Downloads directory write it down so:

```python
    # linux
    binary_path = "/Users/yourname/Downloads/luckyrobots-linux-070824/Linux_07_08_2024"
    # mac
    binary_path = "/Users/yourname/Downloads/LuckEWorld.app" #don't forget the .app
    # windows
    binary_path = r"C:\...\LuckEWorld" # don't forget the --> r <-- at the beginning 
```

## Event Listeners

Lucky Robots provides several event listeners that allow you to interact with the simulated robot and receive updates on its state. These event listeners are:

MOST IMPORTANT ONE
1. **@lr.on_message("robot_output")**: This listener receives output from the robot, providing details on its current state and actions.

this event will give you all the rgb and depth images as well as coordinates that are particular to the milisecond that the shots are captured.

```python
{
    "body_pos": {
        "contents": {
            "Time": "1720752411",
            "rx": "-0.745724",
            "ry": "0.430001",
            "rz": "0.007442",
            "tx": "410.410786",
            "ty": "292.086556",
            "tz": "0.190011"
        },
        "file_path": "/.../4_body_pos.txt"
    },
    "depth_cam1": {
        "contents": null,
        "file_path": "/.../4_depth_cam1.jpg"
    },
    "depth_cam2": {
        "contents": null,
        "file_path": "/.../4_depth_cam2.jpg"
    },
    "hand_cam": {
        "contents": {
            "Time": "1720752411",
            "rx": "-59.724758",
            "ry": "-89.132507",
            "rz": "59.738461",
            "tx": "425.359645",
            "ty": "285.063092",
            "tz": "19.006545"
        },
        "file_path": "/.../4_hand_cam.txt"
    },
    "head_cam": {
        "contents": {
            "Time": "1720752411",
            "rx": "-0.749195",
            "ry": "0.433544",
            "rz": "0.010893",
            "tx": "419.352843",
            "ty": "292.814832",
            "tz": "59.460736"
        },
        "file_path": "/.../4_head_cam.txt"
    },
    "rgb_cam1": {
        "contents": null,
        "file_path": "/.../4_rgb_cam1.jpg"
    },
    "rgb_cam2": {
        "contents": null,
        "file_path": "/.../4_rgb_cam2.jpg"
    }
}


```



2. **@lr.on_message("message")**: This listener decodes messages from the robot, allowing you to understand its internal state.
3. **@lr.on_message("on_start")**: This listener is triggered when the robot starts, allowing you to perform initialization or setup tasks.
4. **@lr.on_message("tasks")**: This listener manages the robot's task list, allowing you to add or remove tasks as needed.
5. **@lr.on_message("task_complete")**: This listener is triggered when the robot completes a task, allowing you to track progress or take action based on task completion.
6. **@lr.on_message("batch_complete")**: This listener is triggered when the robot completes a batch of tasks, allowing you to take action or perform batch-level processing.
7. **@lr.on_message("hit_count")**: This listener tracks the number of times the robot has collided with objects, allowing you to monitor its movement and interactions.

## Controlling the Robot

To control the robot, you can send commands using the `lr.send_message()` function. For example:


## Controlling the Robot's Movement

You can easily control the robot's movement by sending simple commands. Here's an example of how to make the robot's main wheels turn 10 turns (every 360 is one revolution):


commands = [["W 3600 1"]] this will make the robots main wheels turn 10 times.

if you are going to send multiple commands, and you want to know when a particular one ends, then assign an id field to your command

commands = [["id": 1234, "code": "W 18000 1"]]

if you want to send whole set of instructions, you do that by adding multiple arrays. each array will wait until previous array finishes. we call them batches. commands inside one array are executed simultaneously, this is for to allow smoother movements like robot lifting its arms while going forward, turning their head while placing an object etc. (i'm still not 100% happy with this as it has it's own limitations, feel free to suggest a different method.)


commands = [["W 1800 1","a 30"],["a 0", "W 1800 1"]]

if you send one W command in one commands list, then another W, it will override the previous W. Meaning, if you instructed your robot turn its wheels 20 times, on the 5th turn you instructed again to turn 3 times, robot will travel total 8 revolutions and stop.

if you want to know when a particular batch finishes, then give it an id, and listen for that id. (we might create a handy function for this later)

in the end, you will have a commands object like below and you send that to the robot with @lr.send_message



```python
commands = [
    ["RESET"],
    {"commands":[{"id":123456, "code":"w 5650 1"}, {"id":123457, "code":"a 30 1"}], "batchID": "123456"},
    ["A 0 1", "W 18000 1"],
    # ... more commands ...
]
lr.send_message(commands)
```

This allows you to control the robot's movements, actions, and tasks.

## Starting the Robot

To start the robot simulation, use the following code:

```python
lr.start(binary_path, sendBinaryData=False)
```

if you to sendBinaryData=True, Lucky Robots will read the contents of the files and send it inside robot_output object.

This will launch the robot simulation and allow you to interact with it using the event listeners and control commands.

## Conclusion

Lucky Robots provides a powerful system for simulating and controlling virtual robots. By following this README and understanding the key components of the `basic_usage.py` file, you can leverage this system to develop and test robot control algorithms, simulate complex scenarios, and explore the capabilities of virtual robots.