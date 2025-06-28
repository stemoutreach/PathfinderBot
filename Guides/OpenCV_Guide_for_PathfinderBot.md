# OpenCV Guide for PathfinderBot

OpenCV (Open Source Computer Vision Library) is a powerful open-source library used for real-time computer vision tasks. It enables PathfinderBot to process images from the camera, detect AprilTags, track colors, identify objects, and guide autonomous behavior.

---

## What Is OpenCV?

OpenCV is a Python-compatible library for processing images and video. It allows robots to interpret the environment visually—making decisions based on visual input.

### Key Features:

* Image processing (e.g., grayscale, blur, threshold)
* Shape and color detection
* Feature detection (e.g., corners, edges)
* Camera stream capture and manipulation
* Integration with hardware (e.g., USB cameras on Raspberry Pi)

---

## Why Use OpenCV in PathfinderBot?

OpenCV is used to:

* Read and process real-time video from the USB camera
* Detect AprilTags with `pupil-apriltags`
* Calculate distances and angles
* Display visual feedback on screen
* Implement autonomous navigation logic

---

## Basic OpenCV Workflow

```python
import cv2

# Start video capture from the first camera (index 0)
cap = cv2.VideoCapture(0)

while True:
    ret, frame = cap.read()
    if not ret:
        break

    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)  # Convert to grayscale
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)     # Apply blur

    cv2.imshow("Camera Feed", frame)  # Display the original frame

    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()
```

---

## Common Tasks with OpenCV

| Task                 | OpenCV Function                         |
| -------------------- | --------------------------------------- |
| Convert to grayscale | `cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)` |
| Blur image           | `cv2.GaussianBlur(img, (5,5), 0)`       |
| Draw shapes          | `cv2.rectangle()`, `cv2.circle()`       |
| Put text on image    | `cv2.putText()`                         |
| Show image window    | `cv2.imshow()`                          |
| Read from camera     | `cv2.VideoCapture()`                    |
| Detect edges         | `cv2.Canny()`                           |

---

## Resources and Links

* **OpenCV-Python Docs**: [https://docs.opencv.org/4.x/d6/d00/tutorial\_py\_root.html](https://docs.opencv.org/4.x/d6/d00/tutorial_py_root.html)
* **Installation**: `pip install opencv-python`
* **Beginner Tutorial (OpenCV site)**: [https://docs.opencv.org/4.x/d9/df8/tutorial\_root.html](https://docs.opencv.org/4.x/d9/df8/tutorial_root.html)
* **OpenCV GitHub**: [https://github.com/opencv/opencv](https://github.com/opencv/opencv)
* **FreeCodeCamp YouTube Tutorial**: [OpenCV Course](https://www.youtube.com/watch?v=oXlwWbU8l2o)

---

## Tips for Using OpenCV on Raspberry Pi

* Use lower resolutions (e.g., 640x480) for better performance
* Use grayscale images when possible to reduce processing time
* Avoid `cv2.imshow()` if running headless—save or stream frames instead
* Make sure your camera is detected with `cv2.VideoCapture(0)`

---

OpenCV is the vision engine of PathfinderBot—powering all camera-based decisions and visual detection tasks!
