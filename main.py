import sqlite3
import time
import redis
import cv2
import numpy as np

POOL = redis.ConnectionPool(host='localhost', port=6379, db=0)
conn = sqlite3.connect('file:./Content/Database/output.sqlite?mode=ro', uri=True)
c = conn.cursor()

def getRedisVariable(variable_name):
    my_server = redis.Redis(connection_pool=POOL)
    response = my_server.get(variable_name)
    return response

def setRedisVariable(variable_name, variable_value):
    my_server = redis.Redis(connection_pool=POOL)
    my_server.set(variable_name, variable_value)

def showImage(img,i):
    # The image is stored in a blob, retrieve it as such
    image_blob = img
    
    # Convert the binary blob to a numpy array
    image_array = np.frombuffer(image_blob, dtype=np.uint8)
    
    # Decode the image from PNG format
    image = cv2.imdecode(image_array, cv2.IMREAD_UNCHANGED)

    # Check if the image was successfully decoded
    if image is not None:
        # Display the image
        cv2.imshow('Image', image)

        if cv2.waitKey(100) & 0xFF == ord('q'):  # Press 'q' to exit the loop
            cv2.destroyAllWindows()
            exit()
            
    else:
        print("Could not decode the image data.")

def getLatestImage():
    try:
        error1 = False
        c.execute("SELECT * FROM SCREENSHOTS ORDER BY taken_date DESC LIMIT 1")

    except sqlite3.Error as e:
        # Print out the error message if an exception occurs
        print(f"An error occurred: {e}")
        error1 = True
        print("Error1")
        return False
    finally:
        if not error1:
            row = c.fetchone()
            print(row[0])            
            return row[1]
i=0
while True:
    i=i+1
    img = getLatestImage()
    setRedisVariable("next_move", "d")
    if img != False:
        showImage(img, i)
    time.sleep(0.1)


