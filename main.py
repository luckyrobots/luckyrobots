import time
import redis
import cv2
import numpy as np
import urllib.request
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

POOL = redis.ConnectionPool(host='localhost', port=6379, db=0)

def getVariable(variable_name):
    my_server = redis.Redis(connection_pool=POOL)
    response = my_server.get(variable_name)
    return response

def setVariable(variable_name, variable_value):
    my_server = redis.Redis(connection_pool=POOL)
    my_server.set(variable_name, variable_value)

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
  uri = "ws://localhost?StreamerId=LeftCamera"

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


pc = RTCPeerConnection()

@pc.on("track")
async def on_track(track):
  print("Receiving %s" % track.kind)
  if track.kind == "video":
    relay = MediaRelay()
    relayed_track = relay.subscribe(track)
    while True:
      frame = await relayed_track.recv()
      video_frame = frame.to_ndarray(
          format="bgr24")  # Convertir en ndarray
      
      cv2.imshow('stream', video_frame)
      if cv2.waitKey(1) == 27:
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

# move_robot()


# display_stream()



