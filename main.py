import time
import cv2
import numpy as np
import asyncio
import websockets
import json
from aiortc import (
  RTCIceCandidate,
  RTCPeerConnection,
  RTCSessionDescription,
  RTCConfiguration,
  VideoStreamTrack,
  RTCIceServer,
)
from aiortc.contrib.media import MediaRelay, MediaRecorder
# from ultralytics import YOLO
# import torch
# from MLs.depth_estimation import create_side_by_side, generate_depth_map
# from midas.model_loader import load_model
import threading

import os
os.environ['CUDA_LAUNCH_BLOCKING'] = "1"

def parseCandidate(cand) -> RTCIceCandidate:
    # print('candidate recieved: ', cand)
    sdp = cand['candidate']
    bits = sdp.split()
    assert len(bits) >= 8

    candidate = RTCIceCandidate(
        component=int(bits[1]),
        foundation=bits[0],
        ip=bits[4],
        port=int(bits[5]),
        priority=int(bits[3]),
        protocol=bits[2],
        type=bits[7],
        sdpMid=cand['sdpMid'],
        sdpMLineIndex=cand['sdpMLineIndex']
    )

    for i in range(8, len(bits) - 1, 2):
        if bits[i] == "raddr":
            candidate.relatedAddress = bits[i + 1]
        elif bits[i] == "rport":
            candidate.relatedPort = int(bits[i + 1])
        elif bits[i] == "tcptype":
            candidate.tcpType = bits[i + 1]
    return candidate


async def run(pc):
  uri = "wss://pixel.ngrok.dev/?StreamerId=LeftCamera"

  async with websockets.connect(uri) as websocket:
      while True:
        message = await websocket.recv()
        data = json.loads(message)
        
        if(data['type'] == 'config'):
          iceServers = []
          for server in data['peerConnectionOptions']['iceServers']:
            iceServers.append(RTCIceServer(urls=server['urls']))
          pc.__configration = RTCConfiguration(iceServers)
          print(data['peerConnectionOptions']['iceServers'])
          await websocket.send(json.dumps({ 'type': 'subscribe', 'streamerId': 'LeftCamera'}))
        if(data['type'] == 'offer'):
            await pc.setRemoteDescription(RTCSessionDescription(sdp=data['sdp'], type=data['type']))
            await pc.setLocalDescription(await pc.createAnswer())
            await websocket.send(json.dumps({ 'type': 'answer', 'sdp': pc.localDescription.sdp }))
        if(data['type'] == 'iceCandidate'):
          candidate = parseCandidate(data['candidate'])
          await pc.addIceCandidate(candidate)


model = YOLO('yolov8s-seg.pt')  # pretrained YOLOv8n model

# select device
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
#device = 'cpu'
print("Device: %s" % device)

model_path = 'MLs/weights/dpt_beit_base_384.pt'
model_type = 'dpt_beit_base_384'
optimize = False
height = None
square = False
side=False
grayscale=False

depth_model, transform, net_w, net_h = load_model(device, model_path, model_type, optimize, height, square)


pc = RTCPeerConnection()

def process_frame(frame):
    original_image_rgb = np.flip(frame, 2)  # in [0, 255] (flip required to get RGB)
    image = transform({"image": original_image_rgb/255})["image"]

    cv2.imshow('original', original_image_rgb)
    #return image, original_image_rgb

image_buffer = None
prediction = None
depth_map = None
new_image_event = threading.Event()
depth_event = threading.Event()
yolo_event = threading.Event()
yolo_results = None
yolo_img = None


def async_forward():
    global image_buffer, depth_map, yolo_results, yolo_img
    while True:
        new_image_event.wait()
        
        if not depth_event.is_set():

            original_image_rgb = np.flip(image_buffer, 2)  # in [0, 255] (flip required to get RGB)
            image = transform({"image": original_image_rgb/255})["image"]
            prediction = generate_depth_map(device, depth_model, model_type, image, (net_w, net_h), original_image_rgb.shape[1::-1], optimize, True)

            original_image_bgr = np.flip(original_image_rgb, 2) if side else None
            depth_map = create_side_by_side(original_image_bgr, prediction, grayscale)

            depth_map = depth_map/255
            #print(image_buffer.shape)
            #print(prediction)
            depth_event.set()
            new_image_event.clear() 

        if not yolo_event.is_set():

            yolo_img = image_buffer.copy()
           
            yolo_results = model.predict(image_buffer, verbose=False)

            # Process results list
            for result in yolo_results:
                boxes = result.boxes  # Boxes object for bbox outputs
                masks = result.masks  # Masks object for segmentation masks outputs
                keypoints = result.keypoints  # Keypoints object for pose outputs
                probs = result.probs  # Probs object for classification outputs

                for box in boxes.cpu():
                    
                    xyxy = box.xyxy[0]
                    conf = box.conf[0]
                    obj_cls = box.cls[0]

                    x1, y1, x2, y2 = map(int, xyxy)

                    # Draw bounding box
                    yolo_img = cv2.rectangle(yolo_img, (x1, y1), (x2, y2), (0, 255, 0), 2)

                    # Draw class and confidence
                    yolo_img = cv2.putText(yolo_img, f'{obj_cls}: {conf:.2f}', (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 255, 0), 2)

            yolo_event.set()
            new_image_event.clear() 


@pc.on("track")
async def on_track(track):
  print("Receiving %s" % track.kind)

  thread = threading.Thread(target=async_forward)
  thread.start()
  first = True
  if track.kind == "video":
    relay = MediaRelay()
    relayed_track = relay.subscribe(track)

    while True:
      global image_buffer, depth_map, yolo_results, yolo_img
      frame = await relayed_track.recv()
      video_frame = frame.to_ndarray(
          format="bgr24")  # Convertir en ndarray
      
      image_buffer = video_frame
      if first == True:
        yolo_img = image_buffer.copy()
        first = False
      new_image_event.set()

      if depth_event.is_set():
            #depth = prediction
            #cv2.imshow('depth', depth)
            #cv2.waitKey(0)
            
            depth_event.clear()

      if depth_map is not None:
            cv2.imshow('MiDaS Depth Estimation', depth_map)


      if yolo_event.is_set():
    
          cv2.imshow('stream', yolo_img)
          
          yolo_event.clear()

      #if yolo_img is not None:
        #cv2.imshow('yolo', yolo_img)

      

      #start_time = time.perf_counter()
      #await process_frame(video_frame)
      #cv2.imshow('original', original_image_rgb)

      #prediction = generate_depth_map(device, depth_model, model_type, image, (net_w, net_h),original_image_rgb.shape[1::-1], optimize, True)

      #original_image_bgr = np.flip(original_image_rgb, 2) if side else None
      #depth_map = await create_side_by_side(original_image_rgb, prediction, grayscale)

      #depth_map = depth_map/255

      #end_time = time.perf_counter()
      #total_time = end_time - start_time
      #fps = 1 / total_time
      #cv2.putText(depth_map, f"FPS: {fps:.2f}", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 0), 2)
      #cv2.imshow('MiDaS Depth Estimation - Press Escape to close window ', depth_map)


      """try:
        results = model.predict(video_frame, verbose=False, show=True)
        cv2.imshow('stream', video_frame)
      except Exception as e:
        print(video_frame)
        print(e)
        pass"""

      if cv2.waitKey(1) == 27:
        cv2.destroyAllWindows()
        exit(0)
      

@pc.on("connectionstatechange")
async def on_connectionstatechange():
  print("Connection state is", pc.connectionState)


@pc.on("signalingstatechange")
async def on_connectionstatechange():
  print("Signaling state is", pc.signalingState)

loop = asyncio.get_event_loop()



try:
  loop.run_until_complete(
      run(
          pc=pc,
      )
  )
except KeyboardInterrupt:
  pass
finally:
  # cleanup
  loop.run_until_complete(pc.close())


# example usage of robot movement

def move_robot():
    while True:    
        setVariable("next_move", "a")
        time.sleep(0.1)

#move_robot()


# display_stream()



