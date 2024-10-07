import sys
import os
import json
import time
import asyncio
# Add the parent directory of 'src' to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from luckyrobots import core as lr

@lr.on("robot_output")
def handle_robot_output(message):
    #print("robot output",message)
    
    # Pretty print the message
    if isinstance(message, dict):
        print(json.dumps(message, indent=4, sort_keys=True))
    else:
        print(message)
    
    # get the image
    # analyze the image
    # calculate the angle and distance to the target
    # send the command to the robot

@lr.on("message")
def handle_message(message):
    print(f"Received message: {message}", message)
    
    
    # print(robot_images["head_cam"]["contents"]["tx"])
    

@lr.on("start")
def start():
    # lr.send_message({"startup_instructions" : {"level" : "LOFT", "character": "STRETCH", "quality": "LOW"}})


    print("level_is_loaded event is received")
    commands = ["w 360 3","EX1 100", "ex2 100", "ex3 100", "ex4 100", "U 20", "G 10", "R 180"] # if index % 2 == 0 else ["s 360 3","EX1 -100", "ex2 -100", "ex3 -100", "ex4 -100", "U -20", "G -10", "R -180"]            
    lr.send_message(commands)    



    
    # print("level_is_loaded event is received")
    # commands = ["s 360 3","EX1 -100", "ex2 -100", "ex3 -100", "ex4 -100", "U -20", "G -10", "R -180"]
    # lr.send_message(commands)   


    # index = 0
    # while True:
    #     print("level_is_loaded event is received")
    #     commands = ["w 360 3","EX1 100", "ex2 100", "ex3 100", "ex4 100", "U 20", "G 10", "R 180"] # if index % 2 == 0 else ["s 360 3","EX1 -100", "ex2 -100", "ex3 -100", "ex4 -100", "U -20", "G -10", "R -180"]            
    #     lr.send_message(commands)            
    #     index +=1        
    #     time.sleep(5)


@lr.on("level_is_loaded")
def level_is_loaded():
    print("level_is_loaded event is received")
    commands = ["w 360 3","EX1 100", "ex2 100", "ex3 100", "ex4 100", "U 20", "G 10", "R 180"] # if index % 2 == 0 else ["s 360 3","EX1 -100", "ex2 -100", "ex3 -100", "ex4 -100", "U -20", "G -10", "R -180"]            
    lr.send_message(commands)        
    
    print("level_is_loaded event is received")
    commands = ["s 360 3","EX1 -100", "ex2 -100", "ex3 -100", "ex4 -100", "U -20", "G -10", "R -180"]
    lr.send_message(commands)   


@lr.on("firehose")    
def handle_firehose(message):
    pass
    # print("firehose:", message)

@lr.on("tasks")
def handle_tasks(message):
    print("tasks:", message)

@lr.on("task_complete")
def handle_task_complete(id, message=""):
    print("task complete - id:", id, "message:", message)


@lr.on("batch_complete")
def handle_batch_complete(id, message=""):
    print("batch complete - id:", id, "message:", message)
    
    
@lr.on("hit_count")
def handle_hit_count(count):
    print("hit count:", count)

if __name__ == '__main__':
    lr.start()




