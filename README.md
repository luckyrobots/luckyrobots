# Lucky Robots Training Framework

Lucky Robots is a training framework that uses Unreal Engine 5.2 to provide realistic, immersive, and safe environments for robot training. We believe in "gentle" methods and progressive learning experiences, hence the name "Lucky Robots" - because no robots are harmed in our training processes.

![Lucky Robots Logo](./assets/logo.png)

## Table of Contents

- [Features](#features)
- [Requirements](#requirements)
- [Installation](#installation)
- [Usage](#usage)
- [Support](#support)
- [Contributing](#contributing)
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

   ```bash
   python -m venv venv_lucky_robots
   . venv_lucky_robots/bin/activate
   pip install -r requirements.txt
   ```

3. **Launch Unreal Project**

   Open the provided `.uproject` file in Unreal Engine 5.2 and let it compile the necessary assets and plugins.

4. **Connect Python Script**

   Modify the `config.py` file with the appropriate paths and settings for your setup.

## Usage

1. **Start Unreal Simulation**

   Launch the Unreal Project and play the simulation scenario you wish to train your robot in.

2. **Run Python Training Script**

   With the simulation running, execute your Python script to interface with the Unreal simulation and start training your robot.

   ```bash
   python train_robot.py
   ```

## Support

For any queries, issues, or feature requests, please refer to our [issues page](https://github.com/LuckyRobots/LuckyRobotsTrainingFramework/issues).

## Contributing

We welcome contributions! Please read our [contributing guide](CONTRIBUTING.md) to learn about our development process, how to propose bugfixes and improvements, and how to build and test your changes to Lucky Robots.

## License

Lucky Robots Training Framework is released under the [MIT License](LICENSE.md).

---

Happy training! Remember, be kind to robots. 🤖💚
