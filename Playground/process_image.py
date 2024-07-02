from . import event_emitter


class ProcessImage:
    def __init__(self):
        pass

    def process(self, image_bytes, image_name):
        if "head_cam" in image_name:
            print("Processing head_cam image")
            event_emitter.emit("head_cam", image_bytes, image_name)
        elif "hand_cam" in image_name:
            print("Processing hand_cam image")
            event_emitter.emit("hand_cam", image_bytes, image_name)
        elif "body_pos" in image_name:
            print("Processing body_pos image")
            event_emitter.emit("body_pos", image_bytes, image_name)
        elif "rgb_cam1" in image_name:
            print("Processing rgb_cam1 image")
            event_emitter.emit("rgb_cam1", image_bytes, image_name)
        elif "rgb_cam2" in image_name:
            print("Processing rgb_cam2 image")
            event_emitter.emit("rgb_cam2", image_bytes, image_name)
        elif "depth_cam1" in image_name:
            print("Processing depth_cam1 image")
            event_emitter.emit("depth_cam1", image_bytes, image_name)
        elif "depth_cam2" in image_name:
            print("Processing depth_cam2 image")
            event_emitter.emit("depth_cam2", image_bytes, image_name)
        return image_bytes
