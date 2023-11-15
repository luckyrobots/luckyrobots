import sqlite3
import time
import redis
import cv2
import numpy as np

POOL = redis.ConnectionPool(host='localhost', port=6379, db=0)
conn = sqlite3.connect('file:./Content/Database/output.sqlite?mode=ro', uri=True)
c = conn.cursor()

def getVariable(variable_name):
    my_server = redis.Redis(connection_pool=POOL)
    response = my_server.get(variable_name)
    return response

def setVariable(variable_name, variable_value):
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


            
    else:
        print("Could not decode the image data.")

def convertImageToNumpyArray(img):
    image_blob = img
    
    # Convert the binary blob to a numpy array
    image_array = np.frombuffer(image_blob, dtype=np.uint8)
    
    # Decode the image from PNG format
    image = cv2.imdecode(image_array, cv2.IMREAD_UNCHANGED)

    # Check if the image was successfully decoded
    if image is not None:
        # Display the image
        return image
    else:
        print("Could not decode the image data.")
        return False    

def getLatestImage(execution_id = 0):
    try:
        error1 = False
        c.execute("SELECT * FROM SCREENSHOTS ORDER BY taken_date DESC LIMIT 1")

    except sqlite3.Error as e:
        # Print out the error message if an exception occurs
        print(f"An error occurred: {e}")
        error1 = True
        print("Error connecting to sqlite but that's ok - we'll resume in a second")
        return False
    finally:
        if not error1:
            row = c.fetchone()
            print(f"resumed with row id: {row[0]} execution id: {execution_id}")            
            return convertImageToNumpyArray(row[1])
        
def makeACircularPath(pathArray):

    arr = []
    a=0
    for i in pathArray[::2]:
        for j in range(0, i):            
            arr.append(pathArray[a+1])
        a=a+2
    return arr 
#                                    ileri         ilk kose                   ikinci kose          ucuncu kose         geridonme 
path = makeACircularPath([10,"Reset",1400,"w",200,"d",300,"w",300,"d",500,"w",450,"d",1500,"w",500,"d",750,"w",500,"d",10,"Reset",1600,"a",700,"w",505,"a",1600,"w",550,"a",600,"w",200,"a",200,"w",300,"a",1300,"w"])


# Define the codec and create VideoWriter object
fourcc = cv2.VideoWriter_fourcc(*'XVID')  # or (*'MP4V'), (*'MJPG'), (*'X264'), depending on the format you want
fps = 20  # or whatever FPS you want
frame_size = (640, 480)  # should match the size of the images
out = cv2.VideoWriter('output.avi', fourcc, fps, frame_size)

i=0
while True:    
    img = getLatestImage()
    out.write(img)

    # if img != False:
    #     showImage(img, i)
    
    if i == 100:
        out.release()
        time.sleep(3)
        exit()

    # if cv2.waitKey(1) & 0xFF == 27:  # Press 'esc' to exit the loop
    #     out.release()
    #     exit()
    i=i+1
    time.sleep(0.1)

    
    


