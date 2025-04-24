"""Example showing how to control the robot using GPT-4V vision model
Requires:
    pip install openai
    pip install requests
"""
import asyncio
import base64
import os
import time
import random
import requests
import luckyrobots as lr

from pathlib import Path

# Set OpenAI API key from environment variable
api_key = os.getenv('OPENAI_API_KEY')

# Robot movement commands mapping
MOVEMENT_COMMANDS = {
    "W": ["w1 720 3", "w2 720 3"],    # Forward
    "S": ["w1 720 3", "w2 -720 3"],   # Backward
    "A": ["w1 -720 3", "w2 720 3"],   # Turn left
    "D": ["w1 -720 3", "w2 -720 3"]   # Turn right
}

# For demo/testing: set to True to use random movements instead of GPT
USE_RANDOM_MOVEMENT = True


@lr.message_receiver
async def handle_robot_control(message, robot_images):
    if message != "robot_output":
        print("Received message:", message)
        return

    # Skip if no images received
    if not robot_images:
        print("No robot_images received")
        return

    # Get the front camera image path
    if not isinstance(robot_images, dict) or 'rgb_cam1' not in robot_images:
        print("Unexpected structure in robot_images")
        return

    image_path = robot_images['rgb_cam1'].get('file_path')
    if not image_path:
        print("No file_path found in rgb_cam1")
        return

    # Rate limiting: only process every 5 seconds
    current_time = time.time()
    if hasattr(handle_robot_control, 'last_execution_time'):
        if current_time - handle_robot_control.last_execution_time < 5:
            return
    
    if USE_RANDOM_MOVEMENT:
        # Demo mode: use random movements
        movement = random.choice(list(MOVEMENT_COMMANDS.keys()))
        await execute_movement(movement)
    else:
        # Use GPT-4V for movement decisions
        await process_image_with_gpt(image_path)

    handle_robot_control.last_execution_time = current_time


async def process_image_with_gpt(image_path):
    """Process image using GPT-4V to determine robot movement"""
    # Read and encode the image to base64
    with open(image_path, "rb") as image_file:
        base64_image = base64.b64encode(image_file.read()).decode('utf-8')
    
    # Prepare API request
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }
    
    payload = {
        "model": "gpt-4o-mini",
        "messages": [{
            "role": "user",
            "content": [
                {
                    "type": "text",
                    "text": """
You are the vision system for a robot, output single token with one of the following commands:
W to go forward, S to go backwards, A to turn left, D to turn right. 
Try to find a refrigerator in the image. And get close to it.
"""
                },
                {
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/jpeg;base64,{base64_image}"
                    }
                }
            ]
        }],
        "max_tokens": 10,
    }

    try:
        response = requests.post(
            "https://api.openai.com/v1/chat/completions",
            headers=headers,
            json=payload
        )
        
        if response.status_code == 200:
            movement = response.json()['choices'][0]['message']['content']
            await execute_movement(movement)
        else:
            print(f"Error {response.status_code}: {response.json()}")
    except Exception as e:
        print(f"Error communicating with OpenAI API: {str(e)}")


async def execute_movement(movement):
    """Execute robot movement command"""
    if movement in MOVEMENT_COMMANDS:
        print(f"Executing movement: {movement}")
        await lr.send_commands(MOVEMENT_COMMANDS[movement])
    else:
        print(f"Invalid movement command: {movement}")

if __name__ == "__main__":
    """Example showing robot control using GPT-4V vision model or random movements"""    
    
    # Get path for LuckyWorldV2 executable
    binary_path = Path(__file__).parent.parent.parent / "LuckyWorldV2"
    
    lr.start(binary_path=binary_path)