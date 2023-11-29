import time
import redis
import cv2
import numpy as np
import urllib.request

POOL = redis.ConnectionPool(host='localhost', port=6379, db=0)

def getVariable(variable_name):
    my_server = redis.Redis(connection_pool=POOL)
    response = my_server.get(variable_name)
    return response

def setVariable(variable_name, variable_value):
    my_server = redis.Redis(connection_pool=POOL)
    my_server.set(variable_name, variable_value)



def display_stream():
    stream = urllib.request.urlopen('ws://localhost:8888')
    bytes = b''
    while True:
        bytes += stream.read(1024)
        a = bytes.find(b'\xff\xd8')
        b = bytes.find(b'\xff\xd9')
        if a != -1 and b != -1:
            jpg = bytes[a:b+2]
            bytes = bytes[b+2:]
            img = cv2.imdecode(np.frombuffer(jpg, dtype=np.uint8), cv2.IMREAD_COLOR)
            cv2.imshow('stream', img)
            if cv2.waitKey(1) == 27:
                exit(0)


def move_robot():
    while True:    
        setVariable("next_move", "a")
        time.sleep(0.1)


# move_robot()


display_stream()



