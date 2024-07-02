import paho.mqtt.client as mqtt
import time
import cv2
import numpy as np
import base64
import queue
import threading
# Define the MQTT broker details
broker = "0.0.0.0"  # Example broker, replace with your broker
port = 1883
image_topic = "test/image"
text_topic = "test/text"
i=0
with open('./base64img.txt', 'r') as file:
    base64_image = file.read().strip()

# Create a new MQTT client instance
client = mqtt.Client()

# Connect to the broker
client.connect(broker, port, 60)

def show_image(base64_image):
    image_data = base64.b64decode(base64_image)
    # Save image_data as file
    with open(f'./data/{i}.png', 'wb') as file:
        file.write(image_data)
    # Convert to numpy array
    np_arr = np.frombuffer(image_data, np.uint8)

    # Decode the image
    image = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
    global i
    cv2.imwrite( f'./data/decoded_image_{i}.jpg', image)
    i+=1
    # cv2.imshow('Decoded Image', image)
    # cv2.waitKey(1)
    #cv2.destroyAllWindows()

# Define the callback function for when a message is received
def on_message(client, userdata, msg):
    if msg.topic == image_topic:
        img= msg.payload.decode()
        show_image(img)
        

    elif msg.topic == text_topic:
        text = msg.payload.decode()
        print(f"Received text: {text}")

# Set the on_message callback function
client.on_message = on_message

# Subscribe to the topics
client.subscribe(image_topic)
client.subscribe(text_topic)
#publish test message


# Start the MQTT client loop to process network traffic and dispatch callbacks
client.loop_start()

try:
    while True:
        # client.publish(text_topic, "Terminalden selaminaleykum!")
        client.publish(image_topic, base64_image)
        time.sleep(2)
except KeyboardInterrupt:
    print("Disconnecting from broker...")
    client.loop_stop()
    client.disconnect()
    cv2.destroyAllWindows()
