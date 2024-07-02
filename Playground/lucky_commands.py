from flask import Flask, request, jsonify
import random
import time

app = Flask(__name__)
port = 3000


class RobotCommands:
    tasks = []
    tasksIndex = 0

    def get_random_int(self, min=0, max=1000):
        return random.randint(min, max)

    def get_random_command(self):
        return random.choice(commands)

    def create_instructions(self, commands: list[str]):
        global tasks
        instructions = {"LuckyCode": []}
        batch_id = self.get_random_int()
        for command in commands:
            instructions["LuckyCode"].append({
                "ID": str(self.get_random_int()),
                "batchId": batch_id,
                "code": command,
                "time": str(int(time.time())),
                "callback": "on"
            })
        instructions["status"] = "queued"
        robot_commands.tasks.append(instructions)

    def check_if_batch_is_complete(self, task_id):
        batch_id = None
        for taskArray in robot_commands.tasks:
            for task in taskArray["LuckyCode"]:
                if task["ID"] == task_id:
                    batch_id = task["batchId"]
                    print(f"Batch ID matching task ID {task_id} is {batch_id}")

        is_complete = False
        for taskArray in robot_commands.tasks:
            for task in taskArray["LuckyCode"]:
                if task["batchId"] == batch_id:
                    all_completed = all(t.get("status") == "completed" for t in taskArray["LuckyCode"])
                    if all_completed:
                        print(f"Batch {batch_id} is complete")
                        is_complete = True
        return is_complete

    def mark_task_as_complete(self, task_id):
        for taskArray in robot_commands.tasks:
            for task in taskArray["LuckyCode"]:
                if task["ID"] == task_id:
                    task["status"] = "completed"

robot_commands = RobotCommands()

@app.route('/', methods=['POST'])
def handle_post():
    body = request.get_json()
    print('Received POST request with payload:', body)

    if "ID" in body:
        print(f"{body['ID']} is finished")
        robot_commands.mark_task_as_complete(body["ID"])
        if robot_commands.check_if_batch_is_complete(body["ID"]):
            if robot_commands.tasksIndex < len(robot_commands.tasks) - 1:
                print("batch is complete increasing index")
                robot_commands.tasksIndex += 1
            else:
                print("all tasks complete waiting for new ones...")
    return 'POST request received'


@app.route('/', methods=['GET'])
def handle_get():
    next_command = robot_commands.tasks[robot_commands.tasksIndex]
    if next_command["status"] == "queued":
        # print("sending next_command", next_command)
        next_command["status"] = "in-progress"
        return jsonify(next_command)
    else:
        return jsonify({"LuckyCode": []})


if __name__ == '__main__':
    commands = [["RESET"], ["w 5650 1", "a 30 1"], ["A 0 1", "W 18000 1"], ["w 2500 1", "d 30 1", "EX1 10", "EX2 10", "G 100 1"], ["w 3000 1", "a 0 1", "u 100"], ["u -200"]]
    for command in commands:
        robot_commands.create_instructions(command)
    print("tasks", robot_commands.tasks)
    app.run(port=port)