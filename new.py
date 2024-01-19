import asyncio
import websockets
import json
import cv2
from http.server import BaseHTTPRequestHandler, HTTPServer
from aiohttp import web
from aiortc import (
  RTCIceCandidate,
  RTCPeerConnection,
  RTCSessionDescription,
  RTCConfiguration,
  VideoStreamTrack,
  RTCIceServer,
)
from aiortc.contrib.media import MediaRelay, MediaRecorder
import threading
import queue
import numpy as np

next_move = 'a'

async def handle(request):
    global next_move
    a = next_move
    next_move = '0'
    return web.Response(text=a)


app = web.Application()
app.router.add_get('/', handle)



async def start_server(app):
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, 'localhost', 3000)
    await site.start()

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
  uri = "ws://localhost/?StreamerId=LeftCamera"

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


# Create a queue to hold frames
frame_queue = queue.Queue()

def display_images():
    global next_move
    while True:
        frame = frame_queue.get()
        if frame is None:
            print("shit frame")
            break
        if len(frame.shape) == 3:
            # print("This frame is an image.")
            frame = cv2.resize(frame, (640, 320))
            cv2.imshow('stream', frame)
            cv2.waitKey(1)  # Display the image for 1 ms

            array = ["a","s","d","q","w","e","z","x"]
            random_item = np.random.choice(array)
            next_move = random_item

        elif len(frame.shape) == 4:
            print("This frame is a video.")
            break



# Start the display thread
display_thread = threading.Thread(target=display_images)
display_thread.start()

pc = RTCPeerConnection()

@pc.on("track")
async def on_track(track):
    print("Receiving %s" % track.kind)
    if track.kind == "video":
        relay = MediaRelay()
        relayed_track = relay.subscribe(track)
        while True:
            frame = await relayed_track.recv()
            video_frame = frame.to_ndarray(format="bgr24")
            frame_queue.put(video_frame)  # Add the frame to the queue

@pc.on("connectionstatechange")
async def on_connectionstatechange():
  print("Connection state is", pc.connectionState)


@pc.on("signalingstatechange")
async def on_connectionstatechange():
  print("Signaling state is", pc.signalingState)


loop = asyncio.get_event_loop()

try:
    loop.run_until_complete(
        asyncio.gather(
            run(pc=pc),
            start_server(app)
        )
    )
except KeyboardInterrupt:
    print("KeyboardInterrupt")
finally:
    frame_queue.put(None)  # Put the sentinel value in the queue
    display_thread.join()  # Wait for the display thread to finish
    loop.run_until_complete(pc.close())
    print("done")