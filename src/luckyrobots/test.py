import sys
import os
import json
# Add the parent directory of 'src' to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from src.luckyrobots import core as lr

binary_path_win = "./"
binary_path_mac = "/Users/d/Projects/lucky-robots/examples/LuckEWorld.app"
binary_path_linux = "/media/devrim/4gb/Projects/luckeworld-jun10/LuckyRobot/Build/linux/Linux_07_08_2024/"


@lr.on("robot_output")
def handle_robot_output(message):
    print("robot output",message)

@lr.on("message")
def handle_message(message):
    print(f"Received message: {message}", message)
    
    
    # print(robot_images["head_cam"]["contents"]["tx"])
    

@lr.on("on_start")
def on_start():
    print("on_start")
    
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
    

# Detect the operating system and choose the appropriate binary path
if sys.platform.startswith('win'):
    binary_path = binary_path_win
elif sys.platform.startswith('darwin'):
    binary_path = binary_path_mac
elif sys.platform.startswith('linux'):
    binary_path = binary_path_linux
else:
    raise OSError("Unsupported operating system")

print(f"Using binary path: {binary_path}")


lr.start(binary_path)
