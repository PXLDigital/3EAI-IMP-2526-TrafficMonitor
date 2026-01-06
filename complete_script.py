import cv2
import subprocess
import numpy as np
import time
import threading
import sys
from collections import deque
from datetime import datetime

# =============================================================
# TRAFFIC MONITOR CLASS
# =============================================================

class TrafficMonitor:
    def __init__(self):
        self.cap = None
        
        # Background subtractors
        self.bg_mog2 = cv2.createBackgroundSubtractorMOG2(history=500, varThreshold=50, detectShadows=True)
        self.bg_knn = cv2.createBackgroundSubtractorKNN(history=500, dist2Threshold=400, detectShadows=True)
        
        # Vehicle size thresholds (854x480)
        # Parameters 
        self.low_traffic = 10
        self.medium_traffic = 15
        self.high_traffic = 25

        # Parameters for performance can be adjusted by user for better experience
        self.min_area = 700          # min detecting area
        self.max_area = 9000         # max detecting Area
        self.min_width = 30          # min widht bounding box
        self.min_height = 30         # min height bounding box
        self.min_fill_ratio = 0.50   # fill ratio to bound car lights to car box
        self.min_solidity = 0.85     # solidity check ( is it a real car?)
        
        # used for filtering objects by shape
        self.min_aspect_ratio = 0.25 
        self.max_aspect_ratio = 4.5  
        # Extra filtering 
        self.morphology_closed_iter = 1
        self.morphology_dilate_iter = 1
        self.morphology_erode_iter = 1
        self.morphology_open_iter = 3 


    def detect_vehicles(self, frame):
        """
        Vehicle detection optimized for:
        - Merging separate headlights into one vehicle
        - Removing road lights (treat as shadows)
        - Better camion detection
        """
        
        # === 1. Preprocessing: LAB + CLAHE ===
        lab = cv2.cvtColor(frame, cv2.COLOR_BGR2LAB)
        l, a, b = cv2.split(lab)
        
        clahe = cv2.createCLAHE(clipLimit=2.5, tileGridSize=(8, 8))
        lEnhanced = clahe.apply(l)
        labEnhanced = cv2.merge((lEnhanced, a, b))
        enhanced = cv2.cvtColor(labEnhanced, cv2.COLOR_LAB2BGR)
        
        enhanced = cv2.convertScaleAbs(enhanced, alpha=1.05, beta=5)
        blurred = cv2.medianBlur(enhanced, 5)
        
        # === 2. Background Subtraction ===
        fg_mog2 = self.bg_mog2.apply(blurred)
        fg_knn = self.bg_knn.apply(blurred)
        
        # MOG2 is better for shadows (road lights), KNN for movement
        _, fg_mog2 = cv2.threshold(fg_mog2, 150, 255, cv2.THRESH_BINARY)
        _, fg_knn = cv2.threshold(fg_knn, 180, 255, cv2.THRESH_BINARY)
        
        # AND = both must agree (less road light false positives)
        fg_mask = cv2.bitwise_and(fg_mog2, fg_knn)
        
        # === 3. BALANCED CLOSE TO MERGE HEADLIGHTS (But not adjacent vehicles!) ===
        # Smaller kernels = merges headlights of SAME car, not adjacent cars
        kernel_close = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (9, 9))
        kernel_dilate = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7))   
        kernel_open = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))    
        kernel_erode = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (1, 1))   
        
        # Step 1: CLOSE (big) = merges headlights + car body
        fg_mask = cv2.morphologyEx(fg_mask, cv2.MORPH_CLOSE, kernel_close, iterations=self.morphology_closed_iter)
        
        # Step 2: Extra DILATE = ensure all connectivity
        fg_mask = cv2.dilate(fg_mask, kernel_dilate, iterations=self.morphology_dilate_iter)
        
        # Step 3: OPEN = remove road lights (small objects)
        fg_mask = cv2.morphologyEx(fg_mask, cv2.MORPH_OPEN, kernel_open, iterations=self.morphology_open_iter)
        
        # Step 4: Erode = clean edges, remove hanging noise
        fg_mask = cv2.erode(fg_mask, kernel_erode, iterations=self.morphology_erode_iter)
        
        # === 4. Contour Detection ===
        contours, _ = cv2.findContours(fg_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        vehicles = []
        for cnt in contours:
            area = cv2.contourArea(cnt)
            
            # Min area increased (small road lights removed by morphology)
            # Max area BIGGER for camions
            if area < self.min_area or area > self.max_area:
                continue
            
            x, y, w, h = cv2.boundingRect(cnt)
            
            # Minimum bounding box size
            if w < self.min_width or h < self.min_height:
                continue
            
            aspect_ratio = w / float(h)
            
            if not (self.min_aspect_ratio < aspect_ratio < self.max_aspect_ratio):
                continue
            
            # Fill ratio: cars with headlights now have better fill (merged)
            rect_area = w * h
            if rect_area == 0:
                continue
            
            fill_ratio = area / rect_area
            
            if fill_ratio < self.min_fill_ratio:
                continue
            
            
            # Solidity = area / convex hull area (real vehicles have high solidity)
            hull = cv2.convexHull(cnt)
            hull_area = cv2.contourArea(hull)
            if hull_area > 0:
                solidity = area / hull_area
                if solidity < self.min_solidity:  # Fragments have low solidity
                    continue
            
            vehicles.append((x, y, w, h, area))
        
        return vehicles, fg_mask

    def get_traffic_status(self, count):
        if count < self.low_traffic:
            return "LOW", (0, 255, 0)
        elif count < self.medium_traffic:
            return "MEDIUM", (0, 255, 255)
        elif count < self.high_traffic:
            return "HIGH", (0, 165, 255)
        else:
            return "VERY HIGH", (0, 0, 255)

    def draw_info(self, frame, left_count, right_count):
        total = left_count + right_count
        status, color = self.get_traffic_status(total)
        
        # Semi-transparent black bar at top
        overlay = frame.copy()
        cv2.rectangle(overlay, (0, 0), (frame.shape[1], 180), (0, 0, 0), -1)
        cv2.addWeighted(overlay, 0.6, frame, 0.4, 0, frame)
        
        # Text
        cv2.putText(frame, f"TOTAL VEHICLES: {total}", (5, 40),cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        cv2.putText(frame, f"TOWARDS CAMERA: {left_count}", (5, 70), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 1)
        cv2.putText(frame, f"AWAY FROM CAMERA: {right_count}", (5, 100),cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 0, 0), 1)
        cv2.putText(frame, f"TRAFFIC: {status}", (5, 130),cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1)
        
        # Timestamp bottom
        cv2.putText(frame, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), (10, frame.shape[0] - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (200, 200, 200), 1)
        
        return frame

# =============================================================
# STREAM CONFIGURATION
# =============================================================

M3U8_URL = "https://hls.media.verkeerscentrum.be/WEB_K_O5027_A11_ZELZATETNL__103.7_A.stream/chunklist.m3u8"
REFERER = "https://players.media.verkeerscentrum.be/"
ORIGIN = "https://players.media.verkeerscentrum.be"

WIDTH = 854
HEIGHT = 480
BASE_FPS = 15.0
MAX_FPS = 20.0
MIN_FPS = 12.0

frame_queue = deque(maxlen=120)
stop_flag = threading.Event()

def drain_stderr(pipe):
    for line in iter(pipe.readline, b''):
        if stop_flag.is_set():
            break

def create_ffmpeg_process():
    headers = f"Referer: {REFERER}\r\nOrigin: {ORIGIN}\r\n"
    command = [
        "ffmpeg", "-headers", headers,
        "-fflags", "nobuffer", "-flags", "low_delay",
        "-i", M3U8_URL,
        "-vf", f"scale={WIDTH}:{HEIGHT}",
        "-f", "rawvideo", "-pix_fmt", "bgr24",
        "-an", "-sn", "-"
    ]
    
    process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, bufsize=10**7)
    threading.Thread(target=drain_stderr, args=(process.stderr,), daemon=True).start()
    return process

def get_frame_size():
    return WIDTH * HEIGHT * 3

def get_adaptive_fps(buffer_size):
    if buffer_size < 25:
        return MIN_FPS
    elif buffer_size < 50:
        return BASE_FPS
    elif buffer_size > 100:
        return MAX_FPS
    else:
        return BASE_FPS + 2

def frame_reader(process, frame_size):
    buffer = b""
    while not stop_flag.is_set():
        chunk = process.stdout.read(frame_size * 6)
        if not chunk:
            break
        
        buffer += chunk
        
        while len(buffer) >= frame_size:
            raw = buffer[:frame_size]
            buffer = buffer[frame_size:]
            
            frame = np.frombuffer(raw, np.uint8).reshape((HEIGHT, WIDTH, 3))
            frame_queue.append((frame.copy(), time.time()))
    
    stop_flag.set()

# =============================================================
# MAIN LOOP
# =============================================================

def main():
    print("Belgian Highway Live - Direction Split (Yellow = Towards | Blue = Away)")
    print("Press 'q' to quit\n")
    
    monitor = TrafficMonitor()
    process = create_ffmpeg_process()
    frame_size = get_frame_size()
    
    threading.Thread(target=frame_reader, args=(process, frame_size), daemon=True).start()
    
    # Wait for first frames
    while len(frame_queue) < 5 and not stop_flag.is_set():
        time.sleep(0.1)
    
    current_fps = BASE_FPS
    next_frame_time = time.time()
    
    try:
        while not stop_flag.is_set():
            now = time.time()
            
            # Adaptive FPS
            if len(frame_queue) > 0:
                current_fps = get_adaptive_fps(len(frame_queue))
            
            if now >= next_frame_time and frame_queue:
                frame, _ = frame_queue.popleft()
                next_frame_time = now + (1.0 / current_fps)
                
                height, width = frame.shape[:2]
                mid_x = int(width * 0.42)
                
                # Detect vehicles
                vehicles, fg_mask = monitor.detect_vehicles(frame)
                
                # Split by direction
                left_vehicles = []
                right_vehicles = []
                
                for (x, y, w, h, area) in vehicles:
                    center_x = x + w // 2
                    if center_x < mid_x:
                        left_vehicles.append((x, y, w, h))
                        cv2.rectangle(frame, (x, y), (x+w, y+h), (0, 255, 255), 2)  # Yellow
                    else:
                        right_vehicles.append((x, y, w, h))
                        cv2.rectangle(frame, (x, y), (x+w, y+h), (255, 0, 0), 2)  # Blue
                
                # Draw middle line
                cv2.line(frame, (mid_x, 0), (mid_x, height), (255, 255, 255), 3)
                
                # Draw info overlay
                frame = monitor.draw_info(frame, len(left_vehicles), len(right_vehicles))
                
                # Show
                cv2.imshow("Belgian A11 Highway - Direction Split", frame)
                # cv2.imshow("Mask", fg_mask)  # Uncomment if you want to see mask
                
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    break
            
            time_to_wait = next_frame_time - time.time()
            if time_to_wait > 0:
                time.sleep(min(time_to_wait, 0.01))
    
    except KeyboardInterrupt:
        print("\nStopped by user")
    
    finally:
        stop_flag.set()
        process.terminate()
        cv2.destroyAllWindows()
        print("Stream stopped cleanly.")

if __name__ == "__main__":
    main()
