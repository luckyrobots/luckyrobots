import cv2
import numpy as np


class ImageProcessor:
    """Example class for image processing"""
    def __init__(self, frame):
        self.frame = frame

    def process_image(self, server):
        while True:
            frame = server.frame_queue.get()
            if frame is None:
                break
            array = ["a", "s", "d", "q", "w", "e", "z", "x"]
            server.next_move = np.random.choice(array)
            self.frame = cv2.resize(self.frame, (640, 320))
            cv2.imshow('stream', self.frame)
            cv2.waitKey(1)