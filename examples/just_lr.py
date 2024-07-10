import luckyrobots as lr
from luckyrobots.events import on_message

binary_path_win = "./"
binary_path_mac = "./LuckEWorld.app"


@on_message("robot_images_created")
def handle_file_created(robot_images: list):
    print(f"Images created: {len(robot_images)}")
    for i, image in enumerate(robot_images):
        print(f"Image {i + 1}: {image['file_path']}")

lr.start(binary_path_mac)