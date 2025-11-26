"""
async_mjpeg_ringbuffer.py

Usage:
    python3 async_mjpeg_ringbuffer.py

Dependencies:
    pip install opencv-python
ffmpeg must be installed on the system path.

What it does:
    - Runs ffmpeg to read HLS -> outputs MJPEG frames to stdout.
    - Async reader extracts JPEG frames and writes them into a small ring buffer (max_frames).
    - Main loop reads the latest frame from buffer and runs OpenCV processing/display.
    - Press ESC to exit.
"""

import asyncio
import cv2
import numpy as np
import time

# ---- CONFIG ----
FFMPEG_CMD = [
    "ffmpeg",
    "-user_agent", "Mozilla/5.0",
    "-headers", "Referer: https://players.media.verkeerscentrum.be/\r\nOrigin: https://players.media.verkeerscentrum.be\r\n",
    "-i", "https://hls.media.verkeerscentrum.be/WEB_K_O5027_A11_ZELZATETNL__103.7_A.stream/chunklist.m3u8",
    "-vf", "scale=1280:720",
    "-f", "mjpeg",
    "-q:v", "5",
    "-"
]
WIDTH = 1280
HEIGHT = 720
MAX_FRAMES = 8                # ring buffer depth (tune 2-8)
DISPLAY_FPS = 24              # desired display rate
READ_CHUNK = 4096

# ---- Ring buffer (holds latest frames only) ----
class RingBuffer:
    def __init__(self, maxsize):
        self.maxsize = maxsize
        self.buffer = [None] * maxsize
        self.index = 0
        self.count = 0
        self.lock = asyncio.Lock()

    async def push(self, frame):
        async with self.lock:
            self.buffer[self.index] = frame
            self.index = (self.index + 1) % self.maxsize
            self.count = min(self.count + 1, self.maxsize)

    async def get_latest(self):
        async with self.lock:
            if self.count == 0:
                return None
            # latest is index-1
            idx = (self.index - 1) % self.maxsize
            return self.buffer[idx]

async def ffmpeg_reader(proc, ring):
    """Asynchronously read stdout, extract MJPEG frames and push to ring buffer."""
    buf = bytearray()
    while True:
        chunk = await proc.stdout.read(READ_CHUNK)
        if not chunk:
            break
        buf.extend(chunk)
        # find JPEG markers
        while True:
            start = buf.find(b'\xff\xd8')
            end = buf.find(b'\xff\xd9', start + 2) if start != -1 else -1
            if start != -1 and end != -1:
                jpg = bytes(buf[start:end+2])
                del buf[:end+2]
                # decode
                arr = np.frombuffer(jpg, dtype=np.uint8)
                frame = cv2.imdecode(arr, cv2.IMREAD_COLOR)
                if frame is None:
                    continue
                # push latest
                await ring.push(frame)
            else:
                break

async def run():
    ring = RingBuffer(MAX_FRAMES)
    # start ffmpeg
    proc = await asyncio.create_subprocess_exec(
        *FFMPEG_CMD,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.DEVNULL
    )

    reader_task = asyncio.create_task(ffmpeg_reader(proc, ring))

    # main display/process loop
    frame_interval = 1.0 / DISPLAY_FPS
    try:
        while True:
            t0 = time.time()
            frame = await ring.get_latest()
            if frame is not None:
                # Example processing: convert to grayscale (replace with your processing)
                processed = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                # show processed (convert back to BGR for imshow)
                show = cv2.cvtColor(processed, cv2.COLOR_GRAY2BGR)
                cv2.imshow("Async MJPEG - processed", show)
            else:
                # nothing yet; show a blank screen or wait
                black = np.zeros((HEIGHT, WIDTH, 3), dtype=np.uint8)
                cv2.imshow("Async MJPEG - processed", black)

            key = cv2.waitKey(1) & 0xFF
            if key == 27:  # ESC
                break

            # sleep to maintain display rate, but keep responsive
            dt = time.time() - t0
            to_sleep = frame_interval - dt
            if to_sleep > 0:
                await asyncio.sleep(to_sleep)
            else:
                await asyncio.sleep(0)  # yield
    finally:
        reader_task.cancel()
        proc.kill()
        await proc.wait()
        cv2.destroyAllWindows()

if __name__ == "__main__":
    try:
        asyncio.run(run())
    except KeyboardInterrupt:
        pass