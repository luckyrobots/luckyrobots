from flask import Flask, Response
import cv2
import numpy as np
import base64

app = Flask(__name__)

@app.route('/showImage')
def show_image():
    # Define a base64 encoded image string
    base64_image = open('./base64img.txt', 'r').read().strip()

    # Decode the base64 string
    image_data = base64.b64decode(base64_image)

    # Convert to numpy array
    np_arr = np.frombuffer(image_data, np.uint8)

    # Decode the image
    image = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)

    # Encode image to send as HTTP response
    _, buffer = cv2.imencode('.jpg', image)
    response = Response(buffer.tobytes(), mimetype='image/jpeg')
    return response

if __name__ == '__main__':
    app.run(debug=True)
