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

### Why Are They Called AprilTags?

AprilTags were developed by the **APRIL Lab** at the University of Michigan. **APRIL** stands for **A**dvanced **P**erceptual **R**obotics **I**nterface **L**aboratory. The name "AprilTag" combines the lab's acronym with the concept of a visual tag used for detection and localization.

More info: [https://april.eecs.umich.edu/](https://april.eecs.umich.edu/)

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
cap = cv
```
