import os
import glob
import torch
import utils
import cv2
import argparse
import time
import asyncio

import numpy as np

from imutils.video import VideoStream
#from midas.model_loader import default_models, load_model

first_execution = True

@torch.no_grad()
def generate_depth_map(device, model, model_type, image, input_size, target_size, optimize, use_camera):

    global first_execution

    if "openvino" in model_type:
        if first_execution or not use_camera:
            print(f"    Input resized to {input_size[0]}x{input_size[1]} before entering the encoder")
            first_execution = False

        sample = [np.reshape(image, (1, 3, *input_size))]
        prediction = model(sample)[model.output(0)][0]
        prediction = cv2.resize(prediction, dsize=target_size,
                                interpolation=cv2.INTER_CUBIC)
    else:
        sample = torch.from_numpy(image).to(device).unsqueeze(0)

        if optimize and device == torch.device("cuda"):
            if first_execution:
                print("  Optimization to half-floats activated. Use with caution, because models like Swin require\n"
                      "  float precision to work properly and may yield non-finite depth values to some extent for\n"
                      "  half-floats.")
            sample = sample.to(memory_format=torch.channels_last)
            sample = sample.half()

        if first_execution or not use_camera:
            height, width = sample.shape[2:]
            print(f"    Input resized to {width}x{height} before entering the encoder")
            first_execution = False

        prediction = model.forward(sample)
        prediction = (
            torch.nn.functional.interpolate(
                prediction.unsqueeze(1),
                size=target_size[::-1],
                mode="bicubic",
                align_corners=False,
            )
            .squeeze()
            .cpu()
            .numpy()
        )

    return prediction


def create_side_by_side(image, depth, grayscale):

    depth_min = depth.min()
    depth_max = depth.max()
    normalized_depth = 255 * (depth - depth_min) / (depth_max - depth_min)
    normalized_depth *= 3

    bottom_part = np.repeat(np.expand_dims(normalized_depth, 2), 3, axis=2) / 3
    #if not grayscale:
        #bottom_part = cv2.applyColorMap(np.uint8(bottom_part), cv2.COLORMAP)
    bottom_part = np.uint8(bottom_part)
    if image is None:
        return bottom_part
    else:
        return np.concatenate((image, bottom_part), axis=0)
    


