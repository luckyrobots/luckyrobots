import asyncio
from fastapi import FastAPI, WebSocket
from fastapi.responses import JSONResponse
import random
import time
import json
import uvicorn
import logging
from .event_handler import event_emitter

app = FastAPI()
port = 3000
ws = None
application_already_started = False

def get_random_int(min=0, max=1000):
    return random.randint(min, max)

async def emit_start():
    print("emitting start event")
    event_emitter.emit("start")
    
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    global ws, application_already_started

    try:
        await websocket.accept()
        print("WebSocket connection established")
        ws = websocket
        event_emitter.emit("start")
        
    except Exception as e:
        print(f"Failed to establish WebSocket connection: {e}")
        return

    


    try:
        while True:
            data = await websocket.receive_text()
            handle_event(data)
    except Exception as e:
        print(f"WebSocket error: {e}")
    finally:
        ws = None
        print("WebSocket connection closed")

async def send_text_async(data):
    global ws
    if ws is None:
        print("No WebSocket connection")
        return
    try:
        await ws.send_text(json.dumps(data))
    except Exception as e:
        print(f"Error sending WebSocket message: {e}")
        ws = None

def create_instructions(commands=[], callback=None):
    
    if isinstance(commands, list):
        instructions = {"LuckyCode": []}
    
        for command in commands:
            instructions["LuckyCode"].append({
                "ID": str(command["id"]) if isinstance(command, dict) and 'id' in command else str(get_random_int()),
                "code": str(command["code"]) if isinstance(command, dict) and 'code' in command else str(command),
                "time": str(int(time.time() * 1000)),
                "callback": "off"
            })
    else:
        instructions = commands 
    # print("instructions", instructions)
    
    try:
        print("sending instructions", instructions)
        loop = asyncio.get_event_loop_policy().get_event_loop()
        if loop.is_running():
            asyncio.run_coroutine_threadsafe(send_text_async(instructions), loop)
        else:
            loop.run_until_complete(send_text_async(instructions))
    except RuntimeError:
        print("No running event loop. Unable to send instructions.")

@app.get("/")
async def handle_get():
    return "Hello, World!"

def handle_event(message):
    
    print("--> message: ", message)
    try:
        json_data = json.loads(message)
        ID = json_data.get("id")

        if ID is not None:
            # print("task complete", ID)
            event_emitter.emit("task_complete", ID)
            pass
        
            
        match (json_data.get("name")):
            case "hit":
                event_emitter.emit("hit_count", json_data.get("count"))                
            case "start":
                event_emitter.emit("start")                
            case "reconnected":
                event_emitter.emit("reconnected")
            case "ready":
                event_emitter.emit("ready")
            case "level_is_loaded":
                event_emitter.emit("level_is_loaded")   
            case "game_is_loaded":
                event_emitter.emit("game_is_loaded")
            case "game_is_starting":
                event_emitter.emit("game_is_starting")
            case "game_is_finished":
                event_emitter.emit("game_is_finished")
            case "game_is_paused":
                event_emitter.emit("game_is_paused")
            case "game_is_resumed":
                event_emitter.emit("game_is_resumed")

        
    except json.JSONDecodeError:
        print(f"Invalid JSON received: {message}")
    except Exception as e:
        print(f"Error handling event: {e}")

def run_server():
    # event_emitter.emit("message", "running server on port 3000")
    # asyncio.get_event_loop().run_until_complete(event_emitter.emit("message", "running server on port 3000"))
    # Configure logging
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    
    # Run the server with custom log config
    uvicorn.run(app, host="0.0.0.0", port=port, log_level="warning")