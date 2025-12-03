import cv2
import subprocess
import numpy as np
import time
import threading
import sys
from collections import deque

# Stream configuration
M3U8_URL = "https://hls.media.verkeerscentrum.be/WEB_K_O5027_A11_ZELZATETNL__103.7_A.stream/chunklist.m3u8"
REFERER = "https://players.media.verkeerscentrum.be/"
ORIGIN = "https://players.media.verkeerscentrum.be"

# Frame dimensions
WIDTH = 854
HEIGHT = 480

# Target FPS for display (typical traffic cam framerate)
TARGET_FPS = 25.0
FRAME_DELAY = 1.0 / TARGET_FPS

def drain_stderr(pipe):
    """Continuously drain stderr so ffmpeg won't block on Windows."""
    for line in iter(pipe.readline, b''):
        try:
            sys.stderr.write(line.decode(errors="replace"))
        except:
            pass

def create_ffmpeg_process():
    headers = f"Referer: {REFERER}\r\nOrigin: {ORIGIN}\r\n"
    command = [
        "ffmpeg",
        "-headers", headers,
        "-fflags", "nobuffer",
        "-flags", "low_delay",
        "-analyzeduration", "1000000",  # Increase from 0
        "-probesize", "1000000",        # Increase from 32
        "-i", M3U8_URL,
        "-vf", f"scale={WIDTH}:{HEIGHT}",
        "-fps_mode", "passthrough",
        "-f", "rawvideo",
        "-pix_fmt", "bgr24",
        "-an",
        "-sn",
        "-bufsize", "3M",  # Add output buffer
        "-"
    ]
    process = subprocess.Popen(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        bufsize=10**7  # 10MB buffer
    )
    # Start thread to drain stderr (critical for Windows)
    threading.Thread(target=drain_stderr, args=(process.stderr,), daemon=True).start()
    return process

def get_frame_size(width=WIDTH, height=HEIGHT):
    """Calculate bytes per frame"""
    return width * height * 3  # 3 bytes per pixel for BGR

# Global frame queue for producer-consumer pattern
frame_queue = deque(maxlen=30)  # Buffer up to 30 frames (~1 second at 25fps)
stop_flag = threading.Event()

def frame_reader(process, frame_size):
    """Producer: Read frames from ffmpeg and put them in the queue"""
    buffer = b""
    frame_count = 0
    
    try:
        while not stop_flag.is_set():
            # Read one frame's worth of data
            chunk = process.stdout.read(frame_size)
            if not chunk:
                print("Stream ended")
                break
            
            buffer += chunk
            
            # Process complete frames
            while len(buffer) >= frame_size:
                raw_frame = buffer[:frame_size]
                buffer = buffer[frame_size:]
                
                # Convert to numpy array
                frame = np.frombuffer(raw_frame, dtype=np.uint8).copy()
                frame = frame.reshape((HEIGHT, WIDTH, 3))
                
                # Add to queue (will drop oldest if full)
                frame_queue.append((frame, time.time()))
                frame_count += 1
                
    except Exception as e:
        print(f"Reader error: {e}")
    finally:
        stop_flag.set()
        print(f"Reader thread stopped. Read {frame_count} frames.")

def main():
    print("Starting m3u8 stream...")
    print(f"Stream URL: {M3U8_URL}")
    print(f"Target FPS: {TARGET_FPS}")
    print("Press 'q' to quit\n")
    
    # Start ffmpeg process
    process = create_ffmpeg_process()
    
    # Calculate frame size
    frame_size = get_frame_size(WIDTH, HEIGHT)
    
    # Start reader thread
    reader_thread = threading.Thread(target=frame_reader, args=(process, frame_size), daemon=True)
    reader_thread.start()
    
    # Display metrics
    display_count = 0
    skip_count = 0
    start_time = time.time()
    next_frame_time = time.time()
    
    try:
        print("Waiting for frames...")
        
        # Wait for initial buffer
        while len(frame_queue) < 5 and not stop_flag.is_set():
            time.sleep(0.1)
        
        print(f"Starting playback with {len(frame_queue)} frames buffered")
        
        while not stop_flag.is_set():
            current_time = time.time()
            
            # Check if it's time to display the next frame
            if current_time >= next_frame_time:
                if len(frame_queue) > 0:
                    frame, frame_time = frame_queue.popleft()
                    display_count += 1
                    
                    # ---------------------------------------------------
                    # YOUR PROCESSING CODE HERE
                    
                    # Calculate metrics
                    elapsed = current_time - start_time
                    display_fps = display_count / elapsed if elapsed > 0 else 0
                    buffer_size = len(frame_queue)
                    
                    # Display stats
                    cv2.putText(frame, f"FPS: {display_fps:.1f}", (10, 30), 
                               cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
                    cv2.putText(frame, f"Buffer: {buffer_size}", (10, 60), 
                               cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
                    
                    # Show warning if buffer is low or high
                    if buffer_size < 3:
                        cv2.putText(frame, "BUFFERING...", (10, 90), 
                                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
                    elif buffer_size > 25:
                        cv2.putText(frame, "BUFFER HIGH", (10, 90), 
                                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 0, 0), 2)
                    
                    # Example: Convert to grayscale (commented out)
                    # gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                    # cv2.imshow('Grayscale', gray)
                    
                    # ---------------------------------------------------
                    
                    # Display the frame
                    cv2.imshow('M3U8 Stream', frame)
                    
                    # Schedule next frame
                    next_frame_time += FRAME_DELAY
                    
                    # If we're too far behind, reset timing
                    if next_frame_time < current_time - FRAME_DELAY:
                        next_frame_time = current_time + FRAME_DELAY
                        skip_count += 1
                else:
                    # No frames available, wait a bit
                    time.sleep(0.001)
            else:
                # Sleep until next frame time
                sleep_time = next_frame_time - current_time
                if sleep_time > 0:
                    time.sleep(min(sleep_time, 0.001))
            
            # Check for quit
            if cv2.waitKey(1) & 0xFF == ord('q'):
                print("Quit requested by user")
                break
                
    except KeyboardInterrupt:
        print("\nStopping stream...")
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        # Cleanup
        stop_flag.set()
        print("Cleaning up...")
        print(f"Frames displayed: {display_count}")
        print(f"Frames skipped: {skip_count}")
        print(f"Final buffer size: {len(frame_queue)}")
        
        process.terminate()
        try:
            process.wait(timeout=2)
        except subprocess.TimeoutExpired:
            process.kill()
        
        reader_thread.join(timeout=1)
        cv2.destroyAllWindows()
        print("Stream stopped.")

if __name__ == "__main__":
    main()