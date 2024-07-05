from pyee import EventEmitter

event_emitter = EventEmitter()

def on_message(event_name):
    def decorator(func):
        event_emitter.add_listener(event_name, func)
        return func
    return decorator
