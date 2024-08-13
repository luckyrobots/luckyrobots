# Lucky Robots
## A simulation platform for deploying end-to-end AI models for robotics

https://github.com/user-attachments/assets/f500287b-b785-42bb-92d8-6d90b5602d6b

Whether you're an AI/ML Developer, aspiring to design the next Roomba, or interested in delving into robotics, there's no need to invest thousands of dollars in a physical robot and attempt to train it in your living space. With Lucky, you can master the art of training your robot, simulate its behavior with up to 90% accuracy, and then reach out to the robot's manufacturer to launch your new company.

Lucky Robots will feed robot's cameras to your Python application, and you can control the robot using your end to end AI Models. Details below.

(Note for the repository: Our Unreal repo got too big for GitHub (250GB+!), so we moved it to a local Perforce server. Major bummer for collab. We're setting up read-only FTP access to the files. If you need access or have ideas to work around this, give us a shout. I'll hook you up with FTP access for now.)

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

## FULL LIST OF CONTROLS

### FORWARD - BACKWARD
- `[DIRECTION] [DISTANCE] [SPEED]` Example: `W 50 1`
  - `[DIRECTION]`: W is forward, S is backward
  - `[DISTANCE]`: Travel distance, 360 is full revolution of the wheels. 3600 is 10 revolutions.
  - `[SPEED]`: Speed at which motor will react - km/h
  - Send via API: `lr.send_message([["W 360 1"]])`

### LEFT - RIGHT
- `[DIRECTION] [DEGREE]` Example: `A 30`
  - `[DIRECTION]`: A is left, D is right
  - `[DEGREE]`: Spin Rotation in degrees
  - Or: `lr.send_message([["A 30"]])`
  - Remember, the back wheel only requires an angle adjustment. To turn the robot, set this angle and then command it to move forward. When you want robot to stop turning, set it back to `A 0`
    
### RESET
- `RESET`: Resets all positions and rotations to the zero pose
- Or: `lr.send_message([["RESET"]])`

### STRETCH-3 

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

### LUCKY ROBOT-3 

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

To start the robot simulation, use:

```python
lr.start(binary_path, sendBinaryData=False)
```

### ** WHAT WE ARE WORKING ON NEXT **

*   Releasing our first basic end to end model
*   Drone!!!
*   Scan your own room
*   Import URDFs
*   (your idea?)




### brief history of the project ###
------------------------------

** UPDATE 3/19/24 FIRST LUCKY WORLD UBUNTU BUILD IS COMPLETE: https://drive.google.com/drive/folders/15iYXzqFNEg1b2E6Ft1ErwynqBMaa0oOa

** UPDATE 3/6/24 **

We have designed [Stretch 3 Robot](https://hello-robot.com/stretch-3-product) and working on adding this robot to our world

<img width="504" alt="image" src="https://github.com/lucky-robots/lucky-robots/assets/203507/54b1bbbc-67e0-4add-a58f-84b08d14e680">


** UPDATE 1/6/24 **

WE GOT OUR FIRST TEST LINUX BUILD (NOT THE ACTUAL WORLD, THAT'S BEING BUILT) (TESTED ON UBUNTU 22.04)

https://drive.google.com/file/d/1_OCMwn8awKZHBfCfc9op00y6TvetI18U/view?usp=sharing


** UPDATE 2/15/24 **

[Luck-e World second release is out (Windows only - we're working on Linux build next)!](https://drive.google.com/drive/folders/10sVx5eCcx7d9ZR6tn0zqeQCaOF84MIQt)


** UPDATE 2/8/24 **

We are now writing prompts against the 3d environment we have reconstructed using point clouds...


https://github.com/lucky-robots/lucky-robots/assets/203507/a93c9f19-2891-40e1-8598-717ad13efba6




** UPDATE 2/6/24 **

Lucky first release: https://drive.google.com/file/d/1qIbkez1VGU1WcIpqk8UuXTbSTMV7VC3R/view?amp;usp=embed_facebook

Now you can run the simulation on your Windows Machine, and run your AI models against it. If you run into issues, please submit an issue.

** UPDATE 1/15/24 **

Luck-e is starting to understand the world around us and navigate accordingly!

https://github.com/lucky-robots/lucky-robots/assets/203507/4e56bbc5-92da-4754-92f4-989b9cb86b6f


** UPDATE 1/13/24 **

We are able to construct a 3d world using single camera @niconielsen32 (This is not a 3d room generated by a game engine, this is what we generate from what we're seeing through a camera in the game!)

https://github.com/lucky-robots/lucky-robots/assets/203507/f2fd19ee-b40a-4fef-bd30-72c56d0f9ead



** UPDATE 12/29/23 **
We are now flying! Look at these environments, can you tell they're not real?

![Screenshot_18](https://github.com/lucky-robots/lucky-robots/assets/203507/f988a18e-9dc3-484e-9d9f-eb7ad57180b2)
![Screenshot_17](https://github.com/lucky-robots/lucky-robots/assets/203507/f423d73f-d336-47b6-abf0-6f1b174bd740)
![Screenshot_19](https://github.com/lucky-robots/lucky-robots/assets/203507/7f2b9ae2-f84f-41a1-8511-959e2586b809)
![Screenshot_15](https://github.com/lucky-robots/lucky-robots/assets/203507/d65a0fb4-3a4d-4207-9181-2de0e2ce63ce)
![Screenshot_11](https://github.com/lucky-robots/lucky-robots/assets/203507/cf328e8d-fc40-4be3-81ac-a900d0505fd8)
![Screenshot_14](https://github.com/lucky-robots/lucky-robots/assets/203507/5ae9bf2d-246b-437f-ba1b-901a7f10b1fa)
![Screenshot_12](https://github.com/lucky-robots/lucky-robots/assets/203507/e2f0684e-ca18-40b0-8680-76ccec918171)
![Screenshot_8](https://github.com/lucky-robots/lucky-robots/assets/203507/26904b69-c8b8-467d-8355-595cc62ead3f)
![Screenshot_7](https://github.com/lucky-robots/lucky-robots/assets/203507/e43e25b0-b68d-4c1e-9a7d-800b9cf5312b)


** UPDATE 12/27/23 **

Lucky now has a drone  - like the Mars Rover! When it's activated camera feed switches to it automatically!


https://github.com/lucky-robots/lucky-robots/assets/203507/29103a5a-a209-4d49-acd1-adad88e5b590


** UPDATE 12/5/23 **

Completed our first depth map using Midas monocular depth estimation model


https://github.com/lucky-robots/lucky-robots/assets/203507/647a5c32-297a-4157-b72b-afeacdaae48a


https://user-images.githubusercontent.com/203507/276747207-b4db8da0-a14e-4f41-a6a0-ef3e2ea7a31c.mp4

## Table of Contents

- [Features](#features)
- [Support](#support)
- [Contributing](#contributing)
- [Join Our Team](#join-our-team)
- [License](#license)

## Features

1. **Realistic Training Environments**: Train your robots in various scenarios and terrains crafted meticulously in Unreal Engine.
2. **Python Integration**: The framework integrates seamlessly with Python 3.10, enabling developers to write training algorithms and robot control scripts in Python.
3. **Safety First**: No physical wear and tear on robots during training. Virtual training ensures that our robotic friends remain in tip-top condition.
4. **Modular Design**: Easily extend and modify the framework to suit your specific requirements or add new training environments.


## Support

For any queries, issues, or feature requests, please refer to our [issues page](https://github.com/LuckyRobots/LuckyRobotsTrainingFramework/issues).

## Contributing

We welcome contributions! Please read our [contributing guide](CONTRIBUTING.md) to learn about our development process, how to propose bugfixes and improvements, and how to build and test your changes to Lucky Robots.

## Join our team?

Absolutely! Show us a few cool things and/or contribute a few PRs -- let us know!

## License

Lucky Robots Training Framework is released under the [MIT License](LICENSE.md).

---

Happy training! Remember, be kind to robots. 🤖💚
