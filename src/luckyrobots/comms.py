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
    ID = None
    if request.query_params.get("ID"):
        ID = request.query_params.get("ID")
    else:
        json_data = await request.json()
        ID = json_data.get("ID")
        
    if ID is not None:
        event_emitter.emit("task_complete", ID)
        mark_task_as_complete(ID)

        if check_if_batch_is_complete(ID):
            if tasks_index < len(tasks) - 1:
                event_emitter.emit("message", "batch is complete increasing index")
                tasks_index += 1
            else:
                event_emitter.emit("message", "all tasks complete waiting for new ones...")
    else:
        event_emitter.emit("error", "No task ID provided")

    return "POST request received"


@app.middleware("http")
async def log_requests(request: Request, call_next):    
    if request.method == "GET":
        query_params = dict(request.query_params)
        event_emitter.emit("firehose", {"params": query_params, "type": "GET", "url": request.url})
    elif request.method == "POST":
        body = await request.body()
        event_emitter.emit("firehose", {"body": body.decode(), "type": "POST", "url": request.url})
    
    response = await call_next(request)
    return response


@app.get("/hit")
async def handle_hit(request: Request):
    # Get the query parameters
    query_params = request.query_params
    
    # Get the 'count' parameter, default to 1 if not provided
    count = query_params.get('count', None)
    

    # Emit robot_hit event with hit data 
    event_emitter.emit("hit_count", count)

    # Return a JSON response
    return JSONResponse(content={"status": "success", "message": "Hit event received", "data": count}, status_code=200)
    # try:
    #     json_data = await request.json()
    #     event_emitter.emit("robot_hit", json_data)
    #     return JSONResponse(content={"status": "success", "message": "Hit event received"}, status_code=200)
    # except Exception as e:
    #     return JSONResponse(content={"status": "error", "message": str(e)}, status_code=400)



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