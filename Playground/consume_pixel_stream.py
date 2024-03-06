import asyncio
import cv2
import numpy as np
from aiortc import RTCPeerConnection, VideoStreamTrack
from aiortc.contrib.media import MediaBlackhole, MediaPlayer, MediaRecorder

class VideoImageTrack(VideoStreamTrack):
    """
    We're not going to use this anymore - so let's delete soon.
    A video track that returns an image received from the WebRTC stream.
    """
    def __init__(self, track):
        super().__init__()  # don't forget this!
        self.track = track

    async def recv(self):
        frame = await self.track.recv()

        # convert PIL image to OpenCV format
        img = cv2.cvtColor(np.array(frame.to_pil()), cv2.COLOR_RGB2BGR)

        # process image with OpenCV
        img = cv2.Canny(img, 100, 200)

        # return modified image
        return img

async def run(pc):
    def add_tracks():
        if player and player.video:
            pc.addTrack(VideoImageTrack(player.video))

    @pc.on("track")
    def on_track(track):
        print("Track %s received" % track.kind)
        if track.kind == "video":
            local_video = VideoImageTrack(track)
            pc.addTrack(local_video)

    player = MediaPlayer('ws://localhost:8888')
    add_tracks()

    await pc.setLocalDescription(await pc.createOffer())
    await asyncio.sleep(1)

if __name__ == "__main__":
    pc = RTCPeerConnection()
    loop = asyncio.get_event_loop()
    try:
        loop.run_until_complete(run(pc))
    except Exception as e:
        print(e)
    finally:
        loop.run_until_complete(pc.close())