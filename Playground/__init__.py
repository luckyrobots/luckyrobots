from pyee.base import EventEmitter

event_emitter = EventEmitter()


def data_handler(robot_images: list):
    print(len(robot_images))

event_emitter.add_listener("robot_images", data_handler)
