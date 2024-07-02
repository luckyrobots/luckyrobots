from pyee.base import EventEmitter

event_emitter = EventEmitter()


def data_handler(image_bytes, image_name):
    # print(data)

event_emitter.add_listener("head_cam", data_handler)
