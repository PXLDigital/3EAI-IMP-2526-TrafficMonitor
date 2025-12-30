import cv2
import subprocess
import numpy as np
import time

# Stream configuration
M3U8_URL = "https://hls.media.verkeerscentrum.be/WEB_K_O5027_A11_ZELZATETNL__103.7_A.stream/chunklist.m3u8"
REFERER = "https://players.media.verkeerscentrum.be/"
ORIGIN = "https://players.media.verkeerscentrum.be"

# Frame dimensions (adjust based on your stream)
WIDTH = 854
HEIGHT = 480

def create_ffmpeg_process():
    """Create ffmpeg process with proper headers and real-time settings"""
    
    # Headers string for ffmpeg
    headers = f"Referer: {REFERER}\r\nOrigin: {ORIGIN}\r\n"
    
    # FFmpeg command optimized for low-latency streaming
    command = [
        'ffmpeg',
        '-headers', headers,
        '-fflags', 'nobuffer',              # Disable buffering
        '-flags', 'low_delay',              # Low delay mode
        '-strict', 'experimental',
        '-analyzeduration', '0',            # Don't analyze stream
        '-probesize', '32',                 # Minimal probe size
        '-i', M3U8_URL,
        '-vsync', '0',                      # Passthrough timestamps (prevents frame duplication)
        '-copytb', '0',                     # Don't copy input stream time base
        '-r', '25',                         # Force output to 25 fps (typical EU camera rate)
        '-vf', f'scale={WIDTH}:{HEIGHT}',   # Scale to target resolution
        '-f', 'rawvideo',                   # Raw video output
        '-pix_fmt', 'bgr24',                # OpenCV compatible format
        '-an',                              # No audio
        '-sn',                              # No subtitles
        '-'                                 # Output to pipe
    ]
    
    process = subprocess.Popen(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        bufsize=10**8  # Large buffer for pipe
    )
    
    return process

def get_frame_size(process, width=WIDTH, height=HEIGHT):
    """Calculate bytes per frame"""
    return width * height * 3  # 3 bytes per pixel for BGR

def main():
    print("Starting m3u8 stream...")
    print(f"Stream URL: {M3U8_URL}")
    print("Press 'q' to quit\n")
    
    # Start ffmpeg process
    process = create_ffmpeg_process()
    
    # Calculate frame size
    frame_size = get_frame_size(process, WIDTH, HEIGHT)
    
    # Frame counter for FPS calculation
    frame_count = 0
    start_time = time.time()
    
    try:
        while True:
            # Read raw frame data from pipe
            raw_frame = process.stdout.read(frame_size)
            
            # Check if we got a complete frame
            if len(raw_frame) != frame_size:
                print(f"Warning: Incomplete frame received ({len(raw_frame)} bytes)")
                # Try to restart the process if stream ends
                if len(raw_frame) == 0:
                    print("Stream ended or connection lost. Attempting to reconnect...")
                    process.kill()
                    time.sleep(2)
                    process = create_ffmpeg_process()
                    continue
                else:
                    continue
            
            # Convert raw bytes to numpy array
            frame = np.frombuffer(raw_frame, dtype=np.uint8)
            frame = frame.reshape((HEIGHT, WIDTH, 3))
            
            # ---------------------------------------------------
            # YOUR PROCESSING CODE HERE
            # Example: Add FPS counter
            frame_count += 1
            elapsed = time.time() - start_time
            fps = frame_count / elapsed if elapsed > 0 else 0
            
            cv2.putText(frame, f"FPS: {fps:.2f}", (10, 30), 
                       cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
            
            # Example: Convert to grayscale (commented out)
            # gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            
            # ---------------------------------------------------
            
            # Display the frame
            cv2.imshow('M3U8 Stream', frame)
            
            # Check for quit
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
                
    except KeyboardInterrupt:
        print("\nStopping stream...")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        # Cleanup
        process.kill()
        cv2.destroyAllWindows()
        print("Stream stopped.")

if __name__ == "__main__":
    main()