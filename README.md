# Lucky Robots Virtual Training Environment

Lucky Robots: Where robots come for a boot camp, like going to a spa day! 🤖💆‍♂️ We use the fancy Unreal Engine 5.2, Open3D and YoloV8 to create a lavish, virtual 5-star resort experience for our metal buddies so they're absolutely pumped before they meet the real world. Our training framework? More like a robotic paradise with zero robot mishaps. "Gentle" methods? We're practically the robot whisperers here, you won't see humans with metal sticks around. That's why it's "Lucky Robots" because every robot leaves our sessions feeling like they just won the jackpot – all without a scratch! 🎰🤣 

Remember, no robots were emotionally or physically harmed in our ultra-luxurious training process. 

Cheers to happy, and more importantly, unbruised robots! 🍀🤖🎉

** UPDATE **

Completed our first depth map using Midas monocular depth estimation model



https://github.com/lucky-robots/lucky-robots/assets/203507/647a5c32-297a-4157-b72b-afeacdaae48a



https://user-images.githubusercontent.com/203507/276747207-b4db8da0-a14e-4f41-a6a0-ef3e2ea7a31c.mp4

## Table of Contents

- [Features](#features)
- [Requirements](#requirements)
- [Installation](#installation)
- [Usage](#usage)
- [Support](#support)
- [Contributing](#contributing)
- [Join Our Team](#join-our-team)
- [License](#license)

## Features

1. **Realistic Training Environments**: Train your robots in various scenarios and terrains crafted meticulously in Unreal Engine.
2. **Python Integration**: The framework integrates seamlessly with Python 3.10, enabling developers to write training algorithms and robot control scripts in Python.
3. **Safety First**: No physical wear and tear on robots during training. Virtual training ensures that our robotic friends remain in tip-top condition.
4. **Modular Design**: Easily extend and modify the framework to suit your specific requirements or add new training environments.

## Requirements

- Unreal Engine 5.2
- Python 3.10
- Modern GPU and CPU for optimal performance

## Installation

1. **Clone the Repository**

   ```bash
   git clone https://github.com/lucky-robots/lucky-robots.git
   cd lucky-robots
   ```

2. **Setup Python Environment**

   Ensure you have Python 3.10 installed. Set up a virtual environment:

   ```
   # Windows Powershell
   python -m venv lr_venv
   .\lr_venv\Scripts\activate.ps1
   pip install -r requirements.txt
   ```
3. **Setup Local Redis with Docker**

   ```
   # Windows Powershell or bash
   docker pull redis
   docker run -p 6379:6379 redis
   ```

4. **Compile project files with VStudio 2019 or 2022**

    Ensure you have VStudio installed (not VSCode) and click Tools > Get Tools and Features
    Make sure you have following modules installed.
        - Game Development with C++
        - .NET Desktop Development
    
    Then 
    - Right-click on controllable_pawn.uproject, 
    - Show More > Generate VStudio Files
    - Double click on newly generated VS file, controllable_pawn.sln
    - Click "Build > Build controllable_pawn"

    If this process ends with zero errors in a few seconds then you're ready run the project, if you have errors, it's mainly because it failed to install VS components.


4. **Setup PixelStreaming**

   - Run `setup.bat` located in `Ressources\SignalingWebServer\platform_scripts\cmd`

5. **Launch Unreal Project**

   Open the provided `controllable_pawn.uproject` file in Unreal Engine 5.2 and let it compile the necessary assets and plugins.


## Usage

1. **Start Unreal Simulation**

   - Run `.\run_pixel_streaming_server.ps1`
   - Inside Unreal Editor you have a big green Play button. before you click that, there is a three dot icon next to it that says "Change Play Mode and Play Settings"
   - Click that and then tick "Standalone Game" 
   - Launch the game by clicking that Play button and play the simulation scenario you wish to train your robot in.
   - Then you can browse to http://127.0.0.1/?StreamerId=LeftCamera and to http://127.0.0.1/?StreamerId=RightCamera to see what your robot is seeing (optional).

2. **Run Python Training Script**

   With the simulation running, execute your Python script to interface with the Unreal simulation and start training your robot.

   ```bash
   python main.py
   ```

## Support

For any queries, issues, or feature requests, please refer to our [issues page](https://github.com/LuckyRobots/LuckyRobotsTrainingFramework/issues).

## Contributing

We welcome contributions! Please read our [contributing guide](CONTRIBUTING.md) to learn about our development process, how to propose bugfixes and improvements, and how to build and test your changes to Lucky Robots.

## Join our team?

Absolutely! Ideally contribute a few PRs and let us know!

## License

Lucky Robots Training Framework is released under the [MIT License](LICENSE.md).

---

Happy training! Remember, be kind to robots. 🤖💚
