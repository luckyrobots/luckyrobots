"""
Uses gpt4o-mini model to zero-shot the robot from images.

pip3 install openai
pip3 install requests
"""
import luckyrobots as lr
import os
import time
import base64
import requests

# Set your OpenAI API key
api_key = os.getenv('OPENAI_API_KEY')

@lr.receiver
async def receiver(message, data: list = None):
    if message == "robot_output":
        await robot_control(data)
    else:
        print("Received message:", message)

async def robot_control(robot_images: list):


    if int(time.time() * 1000) % 10 == 0:
        await lr.send_commands(["w 720 3"])
        print("forward")
    if int(time.time() * 1000) % 10 == 1:
        await lr.send_commands(["s 720 3"])
        print("backward")


#     if robot_images:
#         if isinstance(robot_images, dict) and 'rgb_cam1' in robot_images:
#             image_path = robot_images['rgb_cam1'].get('file_path')
#             if image_path:
#                 print(f"Processing image: {image_path}")

#                 # Read and encode the image to base64
#                 with open(image_path, "rb") as image_file:
#                     image_data = image_file.read()
#                     base64_image = base64.b64encode(image_data).decode('utf-8')

#                 # Create data URI for the image
#                 data_uri = f"data:image/jpeg;base64,{base64_image}"

#                 # Prepare the messages payload
#                 messages = [
#                     {
#                         "role": "user",
#                         "content": [
#                             {
#                                 "type": "text",
#                                 "text": """
# You are the vision system for a robot, output a single token with one of the following commands:
# W to go forward, S to go backwards, A to turn left, D to turn right
# """
#                             },
#                             {
#                                 "type": "image_url",
#                                 "image_url": {
#                                     "url": data_uri
#                                 }
#                             }
#                         ]
#                     }
#                 ]

#                 # Prepare headers and payload for the API request
#                 headers = {
#                     "Content-Type": "application/json",
#                     "Authorization": f"Bearer {api_key}"
#                 }

#                 payload = {
#                     "model": "gpt-4o-mini",
#                     "messages": messages,
#                     "max_tokens": 10,
#                 }

#                 try:
#                     # Make the API request to OpenAI
#                     response = requests.post(
#                         "https://api.openai.com/v1/chat/completions",
#                         headers=headers,
#                         json=payload
#                     )

#                     response_json = response.json()
#                     if response.status_code == 200:
#                         output_text = response_json['choices'][0]['message']['content']
#                         print(f"GPT-4 Response: {output_text}")
#                         await lr.send_commands([f"{output_text} 720 3"])
#                         # lr.send_message([f"{output_text} 720 3"])
#                     else:
#                         print(f"Error {response.status_code}: {response_json}")
#                 except Exception as e:
#                     print(f"Error communicating with OpenAI API: {str(e)}")
#             else:
#                 print("No file_path found in rgb_cam1")
#         else:
#             print("Unexpected structure in robot_images")
#     else:
#         print("No robot_images received")
#         pass

if __name__ == "__main__":
    lr.start()