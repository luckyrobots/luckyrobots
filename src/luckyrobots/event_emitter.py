# import asyncio
# from functools import partial

# class EventEmitter():
#   def __init__(self):
#     self.listeners = {}

#   def on(self, event_name, listener):
#     if not self.listeners.get(event_name, None):
#       self.listeners[event_name] = {listener}
#     else:
#       self.listeners[event_name].add(listener)

#   async def emit(self, event_name, event=None):
#     listeners = self.listeners.get(event_name, [])
#     tasks = []
#     for listener in listeners:
#       if asyncio.iscoroutinefunction(listener):
#         task = asyncio.create_task(listener(event) if event is not None else listener())
#       else:
#         task = asyncio.create_task(self._run_in_executor(listener, event))
#       tasks.append(task)
#     await asyncio.gather(*tasks, return_exceptions=True)

#   async def _run_in_executor(self, func, event=None):
#     loop = asyncio.get_running_loop()
#     if event is not None:
#       await loop.run_in_executor(None, partial(func, event))
#     else:
#       await loop.run_in_executor(None, func)

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