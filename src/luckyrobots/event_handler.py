from .event_emitter import EventEmitter

event_emitter = EventEmitter()

def on(event):
    def decorator(callback):
        event_emitter.on(event, callback)
        return callback
    return decorator