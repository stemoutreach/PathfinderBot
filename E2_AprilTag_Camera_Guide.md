
# 🏷️ E2 AprilTag Camera Guide (`AprilCamera.py`)

This guide walks through how to use the PathfinderBot’s `AprilCamera.py` module to detect AprilTags in real time using your robot’s calibrated camera.

NOTE: Camera.py: This requires VNC connections to see the camera feed. see [Robot Capabilities page](README.md)

---

## 🧠 What Are AprilTags?

AprilTags are visual fiducial markers—like QR codes, but designed for robust pose estimation. They're perfect for robot navigation and object interaction.

---

## 🛠️ Features Overview

| Feature | Description |
|--------|-------------|
| `Camera.frame` | Live undistorted video frame |
| `pupil_apriltags.Detector` | Detects AprilTags from grayscale frames |
| `TAG_TABLE` | Maps tag IDs to human-readable labels |

---

## 🧰 Setup Requirements

- Python 3
- OpenCV (`cv2`)
- `pupil-apriltags` library (`pip install pupil-apriltags`)
- Calibration data (loaded from `.npz` via `CalibrationConfig`)

---

## 🎥 Camera Initialization

```python
from AprilCamera import Camera

cam = Camera()
cam.camera_open(correction=True)
```

This opens a threaded, undistorted video stream.

---

## 🧪 AprilTag Detection

Tags are detected in grayscale frames:

```python
gray = cv2.cvtColor(cam.frame, cv2.COLOR_BGR2GRAY)
tags = detector.detect(gray)
```

For each tag, the following is drawn:
- Green bounding box
- Label text (mapped from `TAG_TABLE`)

### Example `TAG_TABLE`

```python
TAG_TABLE = {
    583: "Turn-Left",
    584: "Turn-Right",
    585: "Go Forward",
    586: "Pick Up Block"
}
```

---

## 🖼️ Display Example

```python
cv2.imshow("AprilCam", frame)
if cv2.waitKey(1) & 0xFF == 27:   # ESC to quit
    break
```

---

## 🧵 Threaded Frame Access

All image updates happen in a thread. You access the current frame using:

```python
frame = cam.frame
```

This allows you to detect tags without blocking the main loop.

---

## ✅ Full Example

```python
from AprilCamera import Camera
from pupil_apriltags import Detector
import cv2, time

cam = Camera()
cam.camera_open(correction=True)
detector = Detector(families='tag36h11')
time.sleep(0.5)  # Let camera thread fill frames

while True:
    frame = cam.frame
    if frame is None:
        continue

    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    tags = detector.detect(gray)

    for tag in tags:
        # Draw box and label
        ...

    cv2.imshow("AprilCam", frame)
    if cv2.waitKey(1) & 0xFF == 27:
        break

cam.camera_close()
cv2.destroyAllWindows()
```

---

## 🛡️ Safety and Troubleshooting

| Issue | Solution |
|-------|----------|
| No frame shown | Wait for `cam.frame` to initialize |
| False IDs | Ensure tags match printed family (`tag36h11`) |
| Blurry video | Use better lighting and focus |

---

## ✅ Summary

| Task | Method/Code |
|------|-------------|
| Open camera | `camera_open(correction=True)` |
| Detect tags | `detector.detect(gray)` |
| Get frame | `cam.frame` |
| Map labels | `TAG_TABLE[tag.tag_id]` |
| Exit | ESC key (`cv2.waitKey()`) |

AprilTags let you build advanced navigation and interaction systems. Combine with robot movement for full autonomy!

---

[Return to PathfinderBot Workshop page](/README.md)
