import sys
import os
import json
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
    print("start")
    commands = [
        ["RESET"],
        ["w 5650 1","a 30 1"],
        ["A 0 1", "W 1800 1"],
        ["w 2500 1", "d 30 1", "EX1 10", "EX2 10", "G 100 1"],
        ["w 3000 1", "a 0 1", "u 100"],
        ["u -200"]
    ]
    lr.send_message(commands)
    
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
def handle_hit_count(id, count):
    print("hit count:", count)

if __name__ == '__main__':
    lr.start()




