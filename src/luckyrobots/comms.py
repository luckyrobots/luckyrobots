from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
import random
import time
import json
import uvicorn
import logging
from .event_handler import event_emitter  # Import the event_emitter from event_handler.py

app = FastAPI()
port = 3000
tasks = []
tasks_index = 0

def get_random_int(min=0, max=1000):
    return random.randint(min, max)


def create_instructions(commands=[], callback=None):
    
    instructions = {"LuckyCode": []}
    
    if isinstance(commands, dict) and 'batchID' in commands:
        batch_id = commands['batchID']
        commands = commands['commands']
    else:
        batch_id = get_random_int()

    
    for command in commands:
        instructions["LuckyCode"].append({
            "ID": str(command["id"]) if isinstance(command, dict) and 'id' in command else str(get_random_int()),
            "batchID": batch_id,
            "code": str(command["code"]) if isinstance(command, dict) and 'code' in command else str(command),
            "time": str(int(time.time() * 1000)),
            "callback": "on"
        })
    
    instructions["status"] = "queued"
    tasks.append(instructions)

def check_if_batch_is_complete(task_id):
    batch_id = None
    for task_array in tasks:
        for task in task_array["LuckyCode"]:
            if task["ID"] == task_id:
                batch_id = task["batchID"]
                # print(f"Batch ID matching task ID {task_id} is {batch_id}")
                break
        if batch_id:
            break

    is_complete = False
    for task_array in tasks:
        for task in task_array["LuckyCode"]:
            if task["batchID"] == batch_id:
                all_completed = all(t.get("status") == "completed" for t in task_array["LuckyCode"])
                if all_completed:
                    # print(f"Batch {batch_id} is complete")
                    event_emitter.emit("batch_complete",batch_id, f"Batch {batch_id} is complete")
                    is_complete = True
                break
        if is_complete:
            break

    return is_complete

def mark_task_as_complete(task_id):
    for task_array in tasks:
        for task in task_array["LuckyCode"]:
            if task["ID"] == task_id:
                task["status"] = "completed"
                break

@app.post("/")
async def handle_post(request: Request):
    global tasks_index
    json_data = await request.json()

    if "ID" in json_data:
        event_emitter.emit("task_complete", json_data["ID"], "task complete.")
        mark_task_as_complete(json_data["ID"])

        if check_if_batch_is_complete(json_data["ID"]):
            if tasks_index < len(tasks) - 1:
                event_emitter.emit("message", "batch is complete increasing index")
                # print("batch is complete increasing index")
                tasks_index += 1
            else:
                event_emitter.emit("message", "all tasks complete waiting for new ones...")

    return "POST request received"

@app.get("/")
async def handle_get():
    global tasks_index
    if tasks_index >= len(tasks):
        return JSONResponse(content={"LuckyCode": []})
    next_command = tasks[tasks_index]

    if tasks_index < len(tasks):
        next_command = tasks[tasks_index]
    else:
        return JSONResponse(content={"LuckyCode": []})
    
    if next_command["status"] == "queued":
        next_command["status"] = "in-progress"
        return JSONResponse(content=next_command)
    else:
        return JSONResponse(content={"LuckyCode": []})

def run_server():
    # commands = [
    #     ["W 1 1"]
    # ]

    # for command in commands:
    #     create_instructions(command)

    # print("tasks", json.dumps(tasks, indent=2))
    event_emitter.emit("message", "running server on port 3000")
    
    # Configure logging
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    
    # Run the server with custom log config
    uvicorn.run(app, host="0.0.0.0", port=port, log_level="warning")