import cv2
import numpy as np
import matplotlib.pyplot as plt


cap = cv2.VideoCapture(vid_path)
backSub = cv2.createBackgroundSubtractorMOG2()
if not cap.isOpened():
    print("Error opening video file")
    while cap.isOpened():
        # Capture frame-by-frame
        ret, frame = cap.read()
        if ret:
            #apply background subtracton
            fg_mask = backSub.apply(frame)

# Find contours
contours, hierarchy = cv2.findContours(fg_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
# Print (contours)
frame_ct = cv2.drawContours(frame, contours, -1, (0, 255, 0), 2)
# Display the resulting frame
cv2.imshow('Frame_finl', frame_ct)

# Apply global threshold to remove shadows
# We set the threshold value to 180 and the max value to 255,
# and it will simply replace all the values under 180 with 0 and remove all the shadows. 
retval, mask_thresh = cv2.threshold( fg_mask, 180, 255, cv2.THRESH_BINARY)


# Set the kernel
kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
# Apply erosion  to remobve the small white dots in the picture
mask_eroded = cv2.morphologyEx(mask_thresh, cv2.MORPH_OPEN, kernel)

# Filtering contours
min_contour_area = 500 # Define your minimum area threshold. 
large_contours = [cnt for cnt in contours if cv2.contourArea(cnt) > min_contour_area]

# Draw bounding boxes
frame_out = frame.copy()
for cnt in large_contours: 
    x, y, w, h = cv2.boundingRect( cnt )
    frame_out = cv2.rectangle(frame, (x,y), (x+w, y+h), (0, 0, 200), 3)

# Display the resulting frame
cv2.imshow('Frame_final', frame_out)




