import asyncio
import json
import luckyrobots as lr

async def handle_robot_output(message, robot_images: list):
    print("Received robot output:", message)
    if robot_images:
        print("Number of robot images received:", len(robot_images))
        print("robot_images:", json.dumps(robot_images, indent=2))

async def main():
    @lr.message_receiver(handle_robot_output)
    lr.start()

if __name__ == '__main__':
    asyncio.run(main())
