
# 📷 E2 Camera Module Guide (`Camera.py`)

This guide walks through how to use the PathfinderBot's camera module using the `Camera.py` class. It handles capturing frames, undistorting images using calibration data, and making live video streaming simple and threaded.

NOTE: Camera.py: This requires VNC connections to see the camera feed. see [Robot Capabilities page](README.md)

---

## 🛠️ Features Overview

| Feature | Description |
|--------|-------------|
| `camera_open()` | Starts the video stream with optional distortion correction |
| `camera_close()` | Stops and releases the video stream |
| `frame` | Latest frame captured from the camera (undistorted) |
| `camera_task()` | Threaded loop that continuously captures video frames |

---

## 📦 Class Initialization

```python
from Camera import Camera

my_camera = Camera(resolution=(640, 480))  # Optional resolution
```

This also loads the camera calibration parameters from `CalibrationConfig.py`.

---

## 🎥 Start and Stop the Camera

```python
my_camera.camera_open()     # Start video stream
...
my_camera.camera_close()    # Stop and release camera
```

- `camera_open(correction=True)` will apply undistortion using calibration maps.

---

## 🧵 Threaded Frame Access

Once the camera is open, use:

```python
frame = my_camera.frame
```

This returns the **latest available frame**, which is continuously updated by an internal thread.

---

## 🔄 Undistortion and Calibration

The class loads camera calibration files (`.npz`) to remove lens distortion:

```python
self.mtx = self.param_data['mtx_array']
self.dist = self.param_data['dist_array']
```

Frames are remapped using `cv2.remap()` so your images appear corrected.

---

## 🧪 Example: Live Stream with ESC to Exit

```python
from Camera import Camera
import cv2

cam = Camera()
cam.camera_open()

while True:
    img = cam.frame
    if img is not None:
        cv2.imshow('Camera Feed', img)
        if cv2.waitKey(1) == 27:  # ESC key
            break

cam.camera_close()
cv2.destroyAllWindows()
```

---

## 🚫 Error Handling

The class automatically tries to reconnect if the camera fails mid-capture:

```python
if not ret:
    self.cap = cv2.VideoCapture(-1)
```

You may still want to wrap your code in try/except for robustness.

---

## ✅ Summary

| Method | Purpose |
|--------|---------|
| `Camera()` | Initialize and load calibration |
| `camera_open()` | Start the video stream |
| `camera_close()` | Stop the video stream |
| `frame` | Latest captured frame (numpy array) |

The `Camera.py` module makes it easy to grab frames with distortion correction, enabling better object detection and robot vision!

---
[Return to Robot Capabilities page](README.md)

[Return to PathfinderBot Workshop page](/README.md)


