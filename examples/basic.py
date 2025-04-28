"""Basic example showing how to receive robot output and images"""

import asyncio
import json
import luckyrobots as lr


@lr.message_receiver
async def handle_robot_output(message, robot_images):
    """Setup a basic message receiver to handle robot output and images"""
    print("Received robot output:", message)
    
    # Skip if no images received
    if not robot_images:
        return
    
    # Print the received message
    print("Number of robot images received:", len(robot_images))
    print("robot_images:", json.dumps(robot_images, indent=2))
    
    # Example of sending a message after receiving data
    await lr.send_message("Hello from the basic example!")


async def main():
    lr.start()

if __name__ == '__main__':
    asyncio.run(main())
