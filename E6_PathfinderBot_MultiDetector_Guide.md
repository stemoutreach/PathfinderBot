# PathfinderBot Multi-Detector Integration Guide

This guide explains how to use the new **multi-detector system** for
PathfinderBot.\
With this setup, you can dynamically switch the camera between:

-   **AprilTag detection**
-   **Object detection (MobileNet SSD, default: COCO dataset)**
-   **Color detection (default: red, can be adjusted in code)**
-   **Block detection (red blocks for competition use)**

------------------------------------------------------------------------

## 1. Files Included

From the provided `pathfinderbot_multidet_bundle.zip` you will have:

-   `pf_April_nav_web_drive_store_continue_multidet.py`\
    Flask server with web controls and detector switching integrated.

-   `detectors/` folder

    -   `apriltag_det.py` -- AprilTag detection
    -   `object_det.py` -- Object detection
    -   `color_det.py` -- Color tracking (default red)
    -   `block_det.py` -- Block detector (specialized)

-   `detection_manager.py` -- runtime manager for switching

-   `overlay_utils.py` -- drawing overlays

-   `multidetector_integration.py` -- integration helper

-   `pf_nav_web_multidetector.py` -- standalone demo server

-   `README_MULTIDET.md` -- quick reference
--------------------------------------------------------------------------
3.  Make sure dependencies are installed (already present if AprilTags
    worked):

    ``` bash
    sudo pip install flask opencv-python pupil-apriltags imutils
    ```

------------------------------------------------------------------------

## 3. Running the Multi-Detector Server

Run the integrated server:

``` bash
cd /home/robot/code
sudo python pf_April_nav_web_drive_store_continue_multidet.py
```

Then open in your browser:

    http://<robot-ip>:5000

------------------------------------------------------------------------

## 4. Switching Detection Modes

In the web interface you will now see **buttons** to switch modes:

-   `AprilTags`
-   `Objects`
-   `Color`
-   `Blocks`

Alternatively, you can use API endpoints:

-   `GET /md/mode/apriltag`
-   `GET /md/mode/object`
-   `GET /md/mode/color`
-   `GET /md/mode/block`
-   `GET /md/status` → shows current mode
-   `GET /md/video_feed` → MJPEG video with overlay

------------------------------------------------------------------------

## 5. Notes on Detectors

-   **AprilTag** → Uses your existing `pf_AprilCamera` code and
    navigator.
-   **Object** → Default is COCO MobileNet SSD; can be changed in
    `object_det.py`.
-   **Color** → Looks for **red objects** by default; adjust HSV ranges
    in `color_det.py`.
-   **Block** → Simplified detector tuned for red blocks used in
    PathfinderBot workshop.

------------------------------------------------------------------------

## 6. Customization

-   To change color ranges: edit HSV thresholds in `color_det.py`.
-   To detect different objects: update the class IDs in
    `object_det.py`.
-   To integrate navigation logic with objects or color: extend
    `pf_AprilTagNavigator.py` patterns.

------------------------------------------------------------------------

## 7. Troubleshooting

-   **No video feed** → check `cv2.VideoCapture(0)` device index.
-   **High CPU** → reduce frame size in `detection_manager.py`.
-   **Detector not switching** → confirm API call works with
    `curl http://<ip>:5000/md/status`.

------------------------------------------------------------------------

## 8. Next Steps

-   Integrate **object or color detections** into robot navigation.\
-   Add **score-based decision logic** (e.g., follow block, ignore
    background).\
-   Extend `DetectionManager` with your own custom detectors.

------------------------------------------------------------------------
