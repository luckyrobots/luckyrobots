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
    """
    Run the inference and interpolate.

    Args:
        device (torch.device): the torch device used
        model: the model used for inference
        model_type: the type of the model
        image: the image fed into the neural network
        input_size: the size (width, height) of the neural network input (for OpenVINO)
        target_size: the size (width, height) the neural network output is interpolated to
        optimize: optimize the model to half-floats on CUDA?
        use_camera: is the camera used?

    Returns:
        the prediction
    """
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
    """
    Take an RGB image and depth map and place them one on top of the other. This includes a proper normalization of the depth map
    for better visibility.

    Args:
        image: the RGB image
        depth: the depth map
        grayscale: use a grayscale colormap?

    Returns:
        the image and depth map placed one on top of the other
    """
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
    


"""# select device
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
#device = 'cpu'
print("Device: %s" % device)

model_path = 'weights/dpt_beit_large_512.pt'
model_type = 'dpt_beit_large_512'
optimize = False
height = None
square = False
side=False
grayscale=False

model, transform, net_w, net_h = load_model(device, model_path, model_type, optimize, height, square)


with torch.no_grad():
    fps = 1
    cap = cv2.VideoCapture(0)
    time_start = time.time()
    frame_index = 0
    while True:
        _, frame = cap.read()
        if frame is not None:

            start_time = time.perf_counter()
            original_image_rgb = np.flip(frame, 2)  # in [0, 255] (flip required to get RGB)
            image = transform({"image": original_image_rgb/255})["image"]

            prediction = generate_depth_map(device, model, model_type, image, (net_w, net_h),
                                original_image_rgb.shape[1::-1], optimize, True)

            original_image_bgr = np.flip(original_image_rgb, 2) if side else None
            depth_map = create_side_by_side(original_image_bgr, prediction, grayscale)

            depth_map = depth_map/255

        

            end_time = time.perf_counter()
            total_time = end_time - start_time
            fps = 1 / total_time
            cv2.putText(depth_map, f"FPS: {fps:.2f}", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 0), 2)
            cv2.imshow('MiDaS Depth Estimation - Press Escape to close window ', depth_map)

            if cv2.waitKey(1) == 27:  # Escape key
                break

            frame_index += 1

    cv2.destroyAllWindows()
    cap.release()
"""
