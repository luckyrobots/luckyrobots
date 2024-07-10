from luckyrobots.core import start
from luckyrobots.events import on_message

binary_path_win = "C:\\Users\\Goran\\Downloads\\Windows06_28_2024\\Windows06_28_2024"
binary_path_mac = "/Users/d/Projects/myproject/LuckEWorld.app"


@on_message("robot_images_created")
def handle_file_created(robot_images: list):
    print(f"Images created: {len(robot_images)}")

start(binary_path_win)
