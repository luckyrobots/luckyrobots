import luckyrobots as lr
from luckyrobots.events import on_message

lr.core.binary_path = "C:\\Users\\Goran\\Downloads\\Windows06_28_2024\\Windows06_28_2024"

@on_message("robot_images_created")
def handle_file_created(robot_images: list):
    print(f"Images created: {len(robot_images)}")

lr.start()
