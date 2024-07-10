import sys
import os
import json
# Add the parent directory of 'src' to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from src.luckyrobots import core as lr

binary_path_win = "./"
binary_path_mac = "./LuckEWorld.app"
binary_path_linux = "/media/devrim/4gb/Projects/luckeworld-jun10/LuckyRobot/Build/linux/Linux_07_08_2024/"


@lr.on_message("robot_images_created")
def handle_file_created(robot_images: dict):
    print(f"Images created: {len(robot_images)}")
    
    
    print(robot_images["head_cam"]["contents"]["tx"])
    
    # Safely access nested dictionary keys
    # if "head_cam" in robot_images:
    #     if "contents" in robot_images["head_cam"]:
    #         if "tx" in robot_images["head_cam"]["contents"]:
    #             print(robot_images["head_cam"]["contents"]["tx"])
    #         else:
    #             print("No 'tx' key in robot_images['head_cam']['contents']")
    #     else:
    #         print("No 'contents' key in robot_images['head_cam']")
    # else:
    #     print("No 'head_cam' key in robot_images")
    
    # Uncomment this to see the full structure of robot_images
    # print(json.dumps(robot_images, indent=4, sort_keys=True))

lr.start(binary_path_linux)