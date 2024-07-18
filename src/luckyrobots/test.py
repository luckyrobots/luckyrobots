import sys
import os
import json
# Add the parent directory of 'src' to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from src.luckyrobots import core as lr

@lr.on("robot_output")
def handle_robot_output(message):
    print("robot output",message)

@lr.on("message")
def handle_message(message):
    print(f"Received message: {message}", message)
    
    
    # print(robot_images["head_cam"]["contents"]["tx"])
    

@lr.on("start")
def start():
    print("start")
    
    commands = [
        ["RESET"],
        {"commands":[{"id":123456, "code":"w 5650 1"}, {"id":123457, "code":"a 30 1"}], "batchID": "123456"},
        ["A 0 1", "W 18000 1"],
        ["w 2500 1", "d 30 1", "EX1 10", "EX2 10", "G 100 1"],
        ["w 30000 1", "a 0 1", "u 100"],
        ["u -200"]
    ]
    lr.send_message(commands)
    
@lr.on("tasks")
def handle_tasks(message):
    print("tasks:", message)

@lr.on("task_complete")
def handle_task_complete(id, message):
    print("task complete - id:", id, "message:", message)


@lr.on("batch_complete")
def handle_batch_complete(id, message):
    print("batch complete - id:", id, "message:", message)

@lr.on("hit_count")
def handle_robot_hit(count):
    print("robot hit count:", count)

@lr.on("firehose")
def handle_firehose(message):
    print("firehose:", message)
    pass
    



lr.start()
