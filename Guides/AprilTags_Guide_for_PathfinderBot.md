# AprilTags Guide for PathfinderBot

AprilTags are high-contrast, square fiducial markers used in robotics and computer vision for reliable detection and pose estimation. They are especially useful in robotics workshops like PathfinderBot for navigating and interacting with the environment.

---

## What Are AprilTags?

AprilTags are similar to QR codes but optimized for speed, accuracy, and 3D localization. Each tag has a unique ID and can be used to determine its position and orientation relative to the robot’s camera.

* **High contrast**: Works well in various lighting conditions
* **Unique ID**: Each tag has a unique binary code
* **Pose estimation**: Provides 3D position and rotation from a single camera view

**Use Cases**:

* Navigation
* Object tracking
* SLAM (Simultaneous Localization and Mapping)
* AR and Mixed Reality

---

## How Are AprilTags Used in PathfinderBot?

1. **Camera View**: The robot’s USB camera scans for AprilTags.
2. **Detection**: `pupil-apriltags` library detects tags in real-time.
3. **Tag ID Logic**: Each tag triggers a behavior (e.g., turn left, stop, pick up block).
4. **Pose Estimation**: Robot calculates distance and angle to center itself in front of the tag.

---

## Python Code Example

```python
from pupil_apriltags import Detector
import cv2

# Initialize camera
cap = cv2.VideoCapture(0)
detector = Detector(families='tag36h11')

while True:
    ret, frame = cap.read()
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    tags = detector.detect(gray)

    for tag in tags:
        cv2.circle(frame, tuple(map(int, tag.center)), 5, (0,255,0), -1)
        cv2.putText(frame, f"ID: {tag.tag_id}", (int(tag.center[0])+10, int(tag.center[1])),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0,255,0), 2)

    cv2.imshow('AprilTags', frame)
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()
```

---

## Resources and Links

* **AprilTag GitHub (C library)**: [https://github.com/AprilRobotics/apriltag](https://github.com/AprilRobotics/apriltag)
* **pupil-apriltags Python wrapper**: [https://github.com/pupil-labs/apriltags](https://github.com/pupil-labs/apriltags)
* **MIT Research Paper**: [https://april.eecs.umich.edu/media/papers/olson2011tags.pdf](https://april.eecs.umich.edu/media/papers/olson2011tags.pdf)
* **Printable Tags (tag36h11 recommended)**:

  * [https://apriltag.dev/](https://apriltag.dev/)
  * [https://april.eecs.umich.edu/wiki/index.php/AprilTags#Tag\_Families](https://april.eecs.umich.edu/wiki/index.php/AprilTags#Tag_Families)
* **Wikipedia on Fiducial Markers**: [https://en.wikipedia.org/wiki/Fiducial\_marker](https://en.wikipedia.org/wiki/Fiducial_marker)

---

## Best Practices

* Use `tag36h11` family for best balance of detection and ID count
* Print tags at least 10 cm (4 in) across for reliable detection at moderate distances
* Mount tags perpendicular to the camera view for best pose estimation
* Adjust lighting or exposure if detection is inconsistent

---

Happy tagging! These markers will guide your robot through its obstacle course and bring the PathfinderBot to life.
