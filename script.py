import cv2
import numpy as np
from datetime import datetime
import yt_dlp

class TrafficMonitor:
    def __init__(self, video_source=0):
        """
        Initialize traffic monitoring system
        video_source: 0 for webcam, YouTube URL, or path to video file
        """
        # Handle YouTube URLs
        if isinstance(video_source, str) and ('youtube.com' in video_source or 'youtu.be' in video_source):
            print("Extracting YouTube stream URL...")
            video_source = self.get_youtube_stream(video_source)
            print(f"Stream URL obtained successfully!")
        
        self.cap = cv2.VideoCapture(video_source)
        
        # Background subtractor for motion detection
        self.bg_mog2 = cv2.createBackgroundSubtractorMOG2(
            history=500, 
            varThreshold=50,
            detectShadows=True
        )

        self.bg_knn = cv2.createBackgroundSubtractorKNN(
            history=500,
            dist2Threshold=400,
            detectShadows=True
        )
        
        # Minimum area for vehicle detection (adjust based on your camera distance)
        self.min_area = 100
        self.max_area = 2500
        
        # Traffic density thresholds
        self.low_traffic = 1
        self.medium_traffic = 5
        self.high_traffic = 25
        
        # Vehicle counter
        self.vehicle_count = 0
    
    def get_youtube_stream(self, url):
        """Extract direct stream URL from YouTube"""
        ydl_opts = {
            'format': 'best[ext=mp4]/best',
            'quiet': True,
            'no_warnings': True,
        }
        
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                return info['url']
        except Exception as e:
            print(f"Error extracting YouTube URL: {e}")
            print("Trying alternative method...")
            # Alternative: try to get the direct URL
            ydl_opts['format'] = 'worst[ext=mp4]/worst'
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                return info['url']
        
    def detect_vehicles(self, frame):
        """Detect vehicles using background subtraction and contour detection"""
        
        # Apply  median blur to reduce noise  (best out the tests)
        blurred = cv2.medianBlur(frame, 5)
        
        # Apply background subtraction (combined, tests had noticed use both combnined is better performance)
        fg_mog2 = self.bg_mog2.apply(blurred)
        fg_knn = self.bg_knn.apply(blurred)


        # Remove shadows (they appear as gray in the mask)
        _, fg_mog2 = cv2.threshold(fg_mog2, 200, 255, cv2.THRESH_BINARY)
        _, fg_knn = cv2.threshold(fg_knn, 200, 255, cv2.THRESH_BINARY)

        # combine these 2 methods 
        fg_mask = cv2.addWeighted(fg_mog2, 0.6, fg_knn, 0.4, 0)
        # fg_mask = self.bg_subtractor.apply(blurred)
        
       
       #  _, fg_mask = cv2.threshold(fg_mask, 250, 255, cv2.THRESH_BINARY)
        
        # Morphological operations to remove noise and fill gaps
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
        fg_mask = cv2.morphologyEx(fg_mask, cv2.MORPH_CLOSE, kernel)
        fg_mask = cv2.morphologyEx(fg_mask, cv2.MORPH_OPEN, kernel)
        
        # Find contours (vehicles)
        contours, _ = cv2.findContours(
            fg_mask, 
            cv2.RETR_EXTERNAL, 
            cv2.CHAIN_APPROX_SIMPLE
        )
        
        vehicles = []
        for contour in contours:
            area = cv2.contourArea(contour)
            
            # Filter by area to detect only vehicles
            if self.min_area < area < self.max_area:
                x, y, w, h = cv2.boundingRect(contour)
                
                # Additional filter: aspect ratio (vehicles are typically wider/taller)
                aspect_ratio = w / float(h) if h > 0 else 0
                if 0.2 < aspect_ratio < 5.0:
                    vehicles.append((x, y, w, h, area))
        
        return vehicles, fg_mask
    
    def get_traffic_status(self, vehicle_count):
        """Determine traffic density status"""
        if vehicle_count < self.low_traffic:
            return "LOW", (0, 255, 0)  # Green
        elif vehicle_count < self.medium_traffic:
            return "MEDIUM", (0, 255, 255)  # Yellow
        elif vehicle_count < self.high_traffic:
            return "HIGH", (0, 165, 255)  # Orange
        else:
            return "VERY HIGH", (0, 0, 255)  # Red
    
    def draw_info(self, frame, vehicles):
        """Draw bounding boxes and information on frame"""
        self.vehicle_count = len(vehicles)
        
        # Draw bounding boxes
        for (x, y, w, h, area) in vehicles:
            cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)
            # Draw vehicle size info
            cv2.putText(
                frame, 
                f"Area: {int(area)}", 
                (x, y - 5), 
                cv2.FONT_HERSHEY_SIMPLEX, 
                0.4, 
                (0, 255, 0), 
                1
            )
        
        # Get traffic status
        status, color = self.get_traffic_status(self.vehicle_count)
        
        # Draw info panel
        info_height = 120
        overlay = frame.copy()
        cv2.rectangle(overlay, (0, 0), (frame.shape[1], info_height), (0, 0, 0), -1)
        cv2.addWeighted(overlay, 0.6, frame, 0.4, 0, frame)
        
        # Display information
        cv2.putText(
            frame, 
            f"Vehicles Detected: {self.vehicle_count}", 
            (10, 30), 
            cv2.FONT_HERSHEY_SIMPLEX, 
            0.8, 
            (255, 255, 255), 
            2
        )
        
        cv2.putText(
            frame, 
            f"Traffic Status: {status}", 
            (10, 65), 
            cv2.FONT_HERSHEY_SIMPLEX, 
            0.8, 
            color, 
            2
        )
        
        cv2.putText(
            frame, 
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"), 
            (10, 100), 
            cv2.FONT_HERSHEY_SIMPLEX, 
            0.6, 
            (255, 255, 255), 
            1
        )
        
        return frame
    
    def run(self):
        """Main loop to process video stream"""
        print("Traffic Monitoring System Started")
        print("Press 'q' to quit")
        print("Press 's' to save screenshot")
        
        while True:
            ret, frame = self.cap.read()
            if not ret:
                print("Failed to grab frame or video ended")
                break
            
            # Resize for better performance (optional)
            frame = cv2.resize(frame, (800, 600))
            
            # Detect vehicles
            vehicles, fg_mask = self.detect_vehicles(frame)
            
            # Draw information on frame
            output_frame = self.draw_info(frame, vehicles)
            
            # Display frames
            cv2.imshow('Traffic Monitor', output_frame)
            cv2.imshow('Detection Mask', fg_mask)
            
            # Keyboard controls
            key = cv2.waitKey(30) & 0xFF
            if key == ord('q'):
                break
            elif key == ord('s'):
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                cv2.imwrite(f'traffic_screenshot_{timestamp}.jpg', output_frame)
                print(f"Screenshot saved: traffic_screenshot_{timestamp}.jpg")
        
        self.cap.release()
        cv2.destroyAllWindows()

# Example usage
if __name__ == "__main__":
    # YouTube live stream
    youtube_url = "https://www.youtube.com/watch?v=JACr5CpjS_Q"
    monitor = TrafficMonitor(youtube_url)
    
    # Or use webcam: monitor = TrafficMonitor(0)
    # Or video file: monitor = TrafficMonitor('traffic_video.mp4')
    
    monitor.run()