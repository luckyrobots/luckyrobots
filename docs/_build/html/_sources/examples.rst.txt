Examples
========

Basic Robot Controller
-----------------------

Here's a simple example showing how to create a robot controller:

.. code-block:: python

    from luckyrobots import LuckyRobots, Node, Reset, Step
    import numpy as np
    import asyncio

    class MyController(Node):
        def __init__(self):
            super().__init__("my_controller")

        async def _setup_async(self):
            # Create service clients for reset and step
            self.reset_client = self.create_client(Reset, "/reset")
            self.step_client = self.create_client(Step, "/step")

        async def run_robot(self):
            # Reset the environment
            await self.reset_client.call(Reset.Request())
            print("Environment reset!")
            
            # Run 10 steps with random actions
            for i in range(10):
                # Sample random action (6 values for so100 robot)
                action = np.random.uniform(-1, 1, size=6)
                
                # Send action to robot
                response = await self.step_client.call(
                    Step.Request(actuator_values=action.tolist())
                )
                
                print(f"Step {i+1}: Action sent, got observation")
                await asyncio.sleep(0.1)  # Small delay

    # Setup and run
    controller = MyController()
    luckyrobots = LuckyRobots()
    luckyrobots.register_node(controller)

    # Start simulation
    luckyrobots.start(
        scene="kitchen", 
        robot="so100", 
        task="pickandplace"
    )

Using Robot Configuration
-------------------------

Access robot-specific settings for proper action limits:

.. code-block:: python

    from luckyrobots import LuckyRobots, Node, Reset, Step
    import numpy as np

    class ConfiguredController(Node):
        def __init__(self, robot_name="so100"):
            super().__init__("configured_controller")
            self.robot_config = LuckyRobots.get_robot_config(robot_name)

        async def _setup_async(self):
            self.reset_client = self.create_client(Reset, "/reset")
            self.step_client = self.create_client(Step, "/step")

        def sample_valid_action(self):
            """Sample action within robot's actual limits"""
            limits = self.robot_config["action_space"]["actuator_limits"]
            lower = [limit["lower"] for limit in limits]
            upper = [limit["upper"] for limit in limits]
            return np.random.uniform(lower, upper)

        async def control_loop(self):
            await self.reset_client.call(Reset.Request())
            
            for step in range(20):
                action = self.sample_valid_action()
                await self.step_client.call(
                    Step.Request(actuator_values=action.tolist())
                )
                print(f"Step {step}: Valid action within limits")

Accessing Observations
----------------------

Get sensor data from the robot:

.. code-block:: python

    class ObservationController(Node):
        async def _setup_async(self):
            self.reset_client = self.create_client(Reset, "/reset")
            self.step_client = self.create_client(Step, "/step")

        async def observe_robot(self):
            # Reset and get initial observation
            reset_response = await self.reset_client.call(Reset.Request())
            observation = reset_response.observation
            
            # Print joint states
            joint_states = observation.observation_state
            print(f"Joint positions: {joint_states}")
            
            # Check for cameras
            if observation.observation_cameras:
                print(f"Found {len(observation.observation_cameras)} cameras")
                for camera in observation.observation_cameras:
                    print(f"Camera: {camera.camera_name}")

Command Line Usage
------------------

Run the included controller example with different options:

.. code-block:: bash

    # Basic usage
    python controller.py

    # Specify robot and scene
    python controller.py --robot so100 --scene kitchen --task pickandplace

    # Show camera feed
    python controller.py --show-camera

    # Custom rate
    python controller.py --rate 30

    # Custom host
    python controller.py --host 192.168.1.100 --port 3001

Simple Complete Example
-----------------------

Put it all together:

.. code-block:: python

    from luckyrobots import LuckyRobots, Node, Reset, Step, run_coroutine
    import numpy as np
    import asyncio

    class SimpleRobot(Node):
        async def _setup_async(self):
            self.reset_client = self.create_client(Reset, "/reset")
            self.step_client = self.create_client(Step, "/step")

        async def move_robot(self):
            # Reset
            await self.reset_client.call(Reset.Request())
            
            # Move for 5 steps
            for i in range(5):
                action = [0.1, 0.0, 0.0, 0.0, 0.0, 1.0]  # Simple action
                await self.step_client.call(Step.Request(actuator_values=action))
                await asyncio.sleep(0.5)
            
            print("Robot movement complete!")

    def main():
        robot = SimpleRobot()
        luckyrobots = LuckyRobots()
        luckyrobots.register_node(robot)
        luckyrobots.start(scene="kitchen", robot="so100", task="pickandplace")
        
        # Run the robot
        run_coroutine(robot.move_robot())

    if __name__ == "__main__":
        main()
---------------------------

Example showing how to access camera data from observations:

.. code-block:: python

    import cv2
    from luckyrobots import LuckyRobots, Node, Reset, Step

    class CameraController(Node):
        async def _setup_async(self):
            self.reset_client = self.create_client(Reset, "/reset")
            self.step_client = self.create_client(Step, "/step")

        async def process_cameras(self, observation):
            """Process camera data from observation"""
            if observation.observation_cameras:
                for camera in observation.observation_cameras:
                    print(f"Camera: {camera.camera_name}")
                    print(f"Image shape: {camera.shape}")
                    
                    # Display image (if image_data is processed)
                    if hasattr(camera, 'image_data') and camera.image_data is not None:
                        cv2.imshow(camera.camera_name, camera.image_data)
                        cv2.waitKey(1)

        async def run_with_cameras(self):
            reset_response = await self.reset_client.call(Reset.Request())
            await self.process_cameras(reset_response.observation)
            
            for i in range(50):
                action = [0.1, 0.0, 0.0, 0.0, 0.0, 1.0]  # Simple action
                step_response = await self.step_client.call(
                    Step.Request(actuator_values=action)
                )
                await self.process_cameras(step_response.observation)

Command Line Interface
----------------------

The included controller example supports command line arguments:

.. code-block:: bash

    # Basic usage
    python controller.py --robot so100 --scene kitchen --task pickandplace

    # With camera display
    python controller.py --show-camera --rate 30

    # Custom host/port  
    python controller.py --host 192.168.1.100 --port 3001

Service and Publisher Examples
------------------------------

Creating custom services and publishers:

.. code-block:: python

    from luckyrobots import Node

    class ServiceNode(Node):
        async def _setup_async(self):
            # Create a custom service
            await self.create_service(
                MyServiceType, 
                "my_service", 
                self.handle_my_service
            )
            
            # Create a publisher
            self.my_publisher = self.create_publisher(
                MyMessageType, 
                "my_topic"
            )
            
            # Create a subscriber
            self.my_subscriber = self.create_subscription(
                MyMessageType,
                "other_topic", 
                self.handle_message
            )

        async def handle_my_service(self, request):
            # Process service request
            return MyServiceType.Response(success=True)

        def handle_message(self, message):
            # Process received message
            print(f"Received: {message}")

        def publish_data(self, data):
            # Publish a message
            message = MyMessageType(data=data)
            self.my_publisher.publish(message)