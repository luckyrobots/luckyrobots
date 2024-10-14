import sys
import os
import asyncio
import json
# Add the parent directory of 'src' to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from luckyrobots import core as lr

async def handle_robot_output(message, robot_images: list):
    print("Received robot output:", message)
    if robot_images:
        print("Number of robot images received:", len(robot_images))
        print("robot_images:", json.dumps(robot_images, indent=2))
        # Here you can add code to analyze the images, calculate angles and distances, etc.

async def main():
    # Initialize the Lucky Robots core
    robot = lr.LuckyRobots()

    # Set up the message handler
    robot.message_receiver(handle_robot_output)

    # Start the robot
    await robot.start()

    try:
        # Keep the program running
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        print("Stopping the robot...")
    finally:
        # Stop the robot when done
        await robot.stop()

if __name__ == '__main__':
    asyncio.run(main())
