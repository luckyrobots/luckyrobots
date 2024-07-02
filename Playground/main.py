from flask import Flask, request, jsonify
import random
import time

app = Flask(__name__)
port = 3000
tasks = []
tasksIndex = 0

def getRandomInt(min=0, max=1000):
    return random.randint(min, max)

def createInstructions(commands=[]):
    instructions = {"LuckyCode": []}
    batchID = getRandomInt()
    for command in commands:
        instructions["LuckyCode"].append({
            "ID": str(getRandomInt()),
            "batchID": batchID,
            "code": command,
            "time": str(int(time.time())),
            "callback": "on"
        })
    instructions["status"] = "queued"
    tasks.append(instructions)

def checkIfBatchIsComplete(taskID):
    batchID = None
    for taskArray in tasks:
        for task in taskArray["LuckyCode"]:
            if task["ID"] == taskID:
                batchID = task["batchID"]
                print(f"Batch ID matching task ID {taskID} is {batchID}")

    isComplete = False
    for taskArray in tasks:
        for task in taskArray["LuckyCode"]:
            if task["batchID"] == batchID:
                allCompleted = all(t["status"] == "completed" for t in taskArray["LuckyCode"])
                if allCompleted:
                    print(f"Batch {batchID} is complete")
                    isComplete = True
    return isComplete

def markTaskAsComplete(taskID):
    for taskArray in tasks:
        for task in taskArray["LuckyCode"]:
            if task["ID"] == taskID:
                task["status"] = "completed"

@app.route('/', methods=['POST'])
def handle_post():
    body = request.get_json()
    print('Received POST request with payload:', body)

    if "ID" in body:
        print(f"{body['ID']} is finished")
        markTaskAsComplete(body["ID"])

        if checkIfBatchIsComplete(body["ID"]):
            global tasksIndex
            if tasksIndex < len(tasks) - 1:
                print("batch is complete increasing index")
                tasksIndex += 1
            else:
                print("all tasks complete waiting for new ones...")
    return 'POST request received', 200

@app.route('/', methods=['GET'])
def handle_get():
    global tasksIndex
    nextCommand = tasks[tasksIndex]
    if nextCommand["status"] == "queued":
        # print("sending nextCommand", nextCommand)
        nextCommand["status"] = "in-progress"
        return jsonify(nextCommand)
    else:
        return jsonify({"LuckyCode": []})

if __name__ == '__main__':
    commands = [["RESET"], ["w 5650 1", "a 30 1"], ["A 0 1", "W 18000 1"], ["w 2500 1", "d 30 1", "EX1 10", "EX2 10", "G 100 1"], ["w 3000 1", "a 0 1", "u 100"], ["u -200"]]
    for command in commands:
        createInstructions(command)
    print("tasks", tasks)
    app.run(port=port)