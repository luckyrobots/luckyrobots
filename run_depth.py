
import asyncio
import websockets
import json
import cv2
from aiohttp import web
from aiortc import (RTCIceCandidate, RTCPeerConnection, RTCSessionDescription, RTCConfiguration, RTCIceServer)
from aiortc.contrib.media import MediaRelay
import threading
import queue
import numpy as np

from MLs.image_processing import ImageProcessor


class WebRTCServer:
    def __init__(self):
        self.pc = RTCPeerConnection()
        self.frame_queue = queue.Queue()
        self.next_move = 'a'
        self.app = web.Application()
        self.app.router.add_get('/', self.handle)
        self.relay = MediaRelay()

    async def handle(self, request):
        a = self.next_move
        self.next_move = '0'
        return web.Response(text=a)

    async def start_server(self):
        runner = web.AppRunner(self.app)
        await runner.setup()
        site = web.TCPSite(runner, 'localhost', 3000)
        await site.start()

    async def run(self):
        print("Inside run method - starting")
        uri = "ws://localhost:8080/?StreamerId=DepthCamera"
        try:
            async with websockets.connect(uri) as websocket:
                print("WebSocket connection established")
                while True:
                    message = await websocket.recv()
                    # print(f"Received message: {message}")
                    data = json.loads(message)

                    if (data['type'] == 'config'):
                        iceServers = []
                        for server in data['peerConnectionOptions']['iceServers']:
                            iceServers.append(RTCIceServer(urls=server['urls']))
                        self.pc.__configration = RTCConfiguration(iceServers)
                        print(data['peerConnectionOptions']['iceServers'])
                        await websocket.send(json.dumps({'type': 'subscribe', 'streamerId': 'Depth Camera'}))
                    if (data['type'] == 'offer'):
                        await self.pc.setRemoteDescription(RTCSessionDescription(sdp=data['sdp'], type=data['type']))
                        await self.pc.setLocalDescription(await self.pc.createAnswer())
                        await websocket.send(json.dumps({'type': 'answer', 'sdp': self.pc.localDescription.sdp}))
                    if (data['type'] == 'iceCandidate'):
                        candidate = parse_candidate(data['candidate'])
                        await self.pc.addIceCandidate(candidate)
        except Exception as e:
            print(f"WebSocket connection failed: {e}")

    async def run_depth(self):
        print("Inside run method - starting")
        uri = "ws://localhost:8080/?StreamerId=DepthCamera"
        try:
            async with websockets.connect(uri) as websocket:
                print("WebSocket connection established")
                while True:
                    message = await websocket.recv()
                    # print(f"Received message: {message}")
                    data = json.loads(message)

                    if (data['type'] == 'config'):
                        iceServers = []
                        for server in data['peerConnectionOptions']['iceServers']:
                            iceServers.append(RTCIceServer(urls=server['urls']))
                        self.pc.__configration = RTCConfiguration(iceServers)
                        print(data['peerConnectionOptions']['iceServers'])
                        await websocket.send(json.dumps({'type': 'subscribe', 'streamerId': 'Depth Camera'}))
                    if (data['type'] == 'offer'):
                        await self.pc.setRemoteDescription(RTCSessionDescription(sdp=data['sdp'], type=data['type']))
                        await self.pc.setLocalDescription(await self.pc.createAnswer())
                        await websocket.send(json.dumps({'type': 'answer', 'sdp': self.pc.localDescription.sdp}))
                    if (data['type'] == 'iceCandidate'):
                        candidate = parse_candidate(data['candidate'])
                        await self.pc.addIceCandidate(candidate)
        except Exception as e:
            print(f"WebSocket connection failed: {e}")

    async def handle_offer(self, data, websocket):
        await self.pc.setRemoteDescription(RTCSessionDescription(sdp=data['sdp'], type=data['type']))
        answer = await self.pc.createAnswer()
        await self.pc.setLocalDescription(answer)
        await websocket.send(json.dumps({'type': 'answer', 'sdp': self.pc.localDescription.sdp}))

    async def handle_ice_candidate(self, data):
        candidate = parse_candidate(data['candidate'])
        await self.pc.addIceCandidate(candidate)

    def setup_peer_connection(self):
        @self.pc.on("track")
        async def on_track(track):
            if track.kind == "video":
                relayed_track = self.relay.subscribe(track)
                while True:
                    frame = await relayed_track.recv()
                    video_frame = frame.to_ndarray(format="bgr24")
                    self.frame_queue.put(video_frame)  # Add the frame to the queue

        @self.pc.on("connectionstatechange")
        async def on_connectionstatechange():
            print("Connection state is", self.pc.connectionState)

        @self.pc.on("signalingstatechange")
        async def on_signalingstatechange():
            print("Signaling state is", self.pc.signalingState)


def parse_candidate(cand) -> RTCIceCandidate:
    sdp = cand['candidate']
    bits = sdp.split()
    if len(bits) < 8:
        raise ValueError("Invalid candidate format")

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

    for i in range(8, len(bits), 2):
        if bits[i] == "raddr":
            candidate.relatedAddress = bits[i + 1]
        elif bits[i] == "rport":
            candidate.relatedPort = int(bits[i + 1])
        elif bits[i] == "tcptype":
            candidate.tcpType = bits[i + 1]

    return candidate


async def main():

    server = WebRTCServer()
    server.setup_peer_connection()
    image_processor = ImageProcessor(server)
    display_thread = threading.Thread(target=image_processor.process_image, args=(server,))
    display_thread.start()

    try:
        await asyncio.gather(
            server.run(),
            #server.start_server()
        )
    except KeyboardInterrupt:
        print("KeyboardInterrupt")
    finally:
        server.frame_queue.put(None)
        display_thread.join()
        await server.pc.close()
        print("done")


if __name__ == "__main__":
    print("Starting server")
    asyncio.run(main())
