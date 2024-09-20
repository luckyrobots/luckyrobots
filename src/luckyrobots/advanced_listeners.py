import luckyrobots as lr

@lr.on("object_detected")
def on_object_detected(data):
    print(f"Robot detected object: {data.object_type}")

@lr.on("movement_completed")
def on_movement_completed(data):
    print(f"Robot completed movement: {data.movement_type}, distance: {data.distance}")

@lr.on("battery_low")
def on_battery_low(data):
    print(f"Robot battery low: {data.battery_level}%")

@lr.on("error_occurred")
def on_error_occurred(data):
    print(f"Error occurred: {data.error_message}")

@lr.on("task_completed")
def on_task_completed(data):
    print(f"Task completed: {data.task_name}")