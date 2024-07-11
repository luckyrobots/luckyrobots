class EventEmitter:
    def __init__(self):
        self._events = {}

    def on(self, event, fn):
        if event not in self._events:
            self._events[event] = []
        self._events[event].append(fn)

    def emit(self, event, *args, **kwargs):
        if event in self._events:
            for fn in self._events[event]:
                fn(*args, **kwargs)