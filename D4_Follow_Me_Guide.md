# D4 Follow‑Me AprilTag Guide

This guide explains how the **Follow‑Me** behavior works, how to run it, and how to tune it. The program makes a robot **follow the closest AprilTag** and maintain a target standoff distance (default **18 inches / 0.4572 m**). It’s designed so a line of robots can trail a driver‑controlled lead robot.

---

## 1) Quick Start

### Run
```bash
sudo python pf_follow_me.py
```
The robot will:
1. Initialize posture via `pf_start_robot.initialize_robot()` (sets camera/arm, motors idle).
2. Open the calibrated camera from `pf_AprilCamera.Camera(...)`.
3. Detect AprilTags with pose estimation and pick the **closest** one (minimum Z distance).
4. **Strafe** to center on the tag and **drive forward/back** to hold the target distance.
5. **Stop** if within tolerances or if no tag is seen for ~1 second.

> Tip: Place a printed AprilTag on the back of the lead robot.

---

## 2) File & Module Layout

- **pf_follow_me.py** — this program (follow‑me controller).
- **pf_start_robot.py** — startup posture & safety (called at launch).
- **pf_AprilCamera.py** — camera class, calibration, undistortion, intrinsics.
- **mecanum.py** — `MecanumChassis` interface (`translation(...)`, `reset_motors()`).
- **pupil_apriltags** — external library for AprilTag detection & pose estimation.

---

## 3) How It Works (Control Loop)

1. **Initialization**
   - Calls `pf_start_robot.initialize_robot()` to set a safe posture (arm & LEDs), and ensure motors are stopped.
   - Opens the camera (e.g., 640×480) and loads intrinsics (`fx, fy, cx, cy`).
   - Creates a `Detector(families="tag36h11")` with pose estimation enabled.

2. **Per‑Frame Steps**
   - Grab a frame, convert to grayscale.
   - Run `detector.detect(..., estimate_tag_pose=True, camera_params=(fx,fy,cx,cy), tag_size=TAG_SIZE_M)`.
   - Select the **closest** tag:
     ```python
     tag = min(tags, key=lambda t: float(t.pose_t[2].item()))
     ```
     Here `pose_t` is the tag translation (x, y, z) in **meters** relative to the camera (x: right +, y: down +, z: forward +).
   - Compute errors:
     - **Lateral** error: `error_x = x` → strafe left/right to center the tag.
     - **Distance** error: `error_z = z - TARGET_DISTANCE_M` → forward/back to reach target standoff.
   - Convert errors to **mm/s** with proportional control and deadbands:
     ```python
     vx_mm = P(error_x, Kx) if |error_x| > CENTER_TOLERANCE_M else 0
     vy_mm = P(error_z, Kz) if |error_z| > DIST_TOLERANCE_M else 0
     ```
     and clamp to `[MIN_SPEED_MM_S, MAX_SPEED_MM_S]`.
   - Drive with `MecanumChassis.translation(vx_mm, vy_mm)` or `reset_motors()` if within both tolerances.

3. **Loss‑of‑Sight**
   - If no tag is detected for `NO_TAG_TIMEOUT_S` (default 1.0s), **stop** the chassis.

4. **Debug View (Optional)**
   - Set `SHOW_WINDOW = True` to draw tag outlines and telemetry for tuning.

---

## 4) Key Tunables (top of file)

| Constant | Default | Meaning |
|---|---:|---|
| `TAG_FAMILY` | `"tag36h11"` | AprilTag family to detect |
| `TAG_SIZE_M` | `0.045` | Size of the **black square** in meters (match your print size) |
| `TARGET_DISTANCE_M` | `0.4572` | **Target standoff** to the tag (18 inches) |
| `CENTER_TOLERANCE_M` | `0.02` | Deadband for lateral centering (m) |
| `DIST_TOLERANCE_M` | `0.05` | Deadband for distance (m) |
| `Kx` | `600` | Proportional gain for **strafe** (mm/s per m error) |
| `Kz` | `800` | Proportional gain for **forward/back** (mm/s per m error) |
| `MAX_SPEED_MM_S` | `350` | Max speed clamp |
| `MIN_SPEED_MM_S` | `80` | Min speed clamp (prevents “stiction”) |
| `NO_TAG_TIMEOUT_S` | `1.0` | Stop if tag unseen for this long (s) |
| `SHOW_WINDOW` | `False` | Enable OpenCV preview with overlays |

> **Important:** Measure your printed tag’s square size and update `TAG_SIZE_M` accordingly for accurate distance (Z) estimates.

---

## 5) Safety & Good Practices

- **Start clear:** Power on with clear space in front; the robot may move immediately once it sees a tag.
- **Emergency stop:** Keep a hand near the power switch or your UI’s stop button.
- **Speed bounds:** Tune `MAX_SPEED_MM_S` conservatively in crowded spaces.
- **Stable tags:** Use sturdy prints; flimsy paper can warp and affect pose.
- **Lighting:** Avoid glare and low‑light; consistent lighting improves detection stability.

---

## 6) Tuning Workflow

1. **Verify distance estimate:** Place the tag at a known distance (e.g., 0.5 m). Check logs/telemetry with `SHOW_WINDOW=True`. Adjust `TAG_SIZE_M` if Z is biased.
2. **Centering feel:** Increase `Kx` if the robot drifts or is slow to center; decrease if it oscillates.
3. **Distance feel:** Increase `Kz` if the robot is slow to approach or retreat; decrease if it overshoots.
4. **Deadbands:** Widen `CENTER_TOLERANCE_M`/`DIST_TOLERANCE_M` to reduce micro‑twitching when “close enough.”
5. **Speed clamps:** Raise `MAX_SPEED_MM_S` carefully for bigger spaces; increase `MIN_SPEED_MM_S` if the robot struggles to start moving.

---

## 7) Troubleshooting

- **DeprecationWarning about NumPy scalar conversion**  
  Fixed by extracting scalar with `.item()`:
  ```python
  float(t.pose_t[2].item())
  ```

- **Robot creeps forward/back even when close**  
  Increase `DIST_TOLERANCE_M` a bit (e.g., 0.07) or lower `Kz`.

- **Robot wiggles side‑to‑side**  
  Lower `Kx` or increase `CENTER_TOLERANCE_M` (e.g., 0.03–0.04).

- **Distance seems wrong**  
  Ensure `TAG_SIZE_M` matches your printed tag’s black square; confirm camera intrinsics are correct.

- **Stops randomly**  
  Increase `NO_TAG_TIMEOUT_S` slightly or improve lighting/contrast.

- **Preview window needed**  
  Set `SHOW_WINDOW=True` to draw tag corners, ID, and error values on the frame for live tuning.

---

## 8) Integration Notes

- **Web UI Button/Endpoint**  
  Add a Flask endpoint (e.g., `/follow_me/start` & `/follow_me/stop`) that launches/terminates this script or toggles a follow‑me task/thread in your existing server. Ensure **exclusive motor control** (don’t run other motion loops simultaneously).

- **Startup Posture**  
  Modify `pf_start_robot.initialize_robot()` if you want different arm/LED behavior when entering follow‑me.

- **Chaining Behaviors**  
  From follow‑me, you can transition to other tasks (e.g., “pick up” routine) once within tolerance—just ensure you **stop** the chassis first.

---

## 9) Minimal Code Skeleton (annotated)

```python
# 1) Startup posture
pf_start_robot.initialize_robot()

# 2) Camera & detector
cam = Camera(resolution=(640, 480))
cam.camera_open(correction=True)
fx, fy = cam.mtx[0,0], cam.mtx[1,1]
cx, cy = cam.mtx[0,2], cam.mtx[1,2]
detector = Detector(families='tag36h11')

# 3) Main loop
while True:
    frame = cam.frame
    tags = detector.detect(
        cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY),
        estimate_tag_pose=True,
        camera_params=(fx,fy,cx,cy),
        tag_size=TAG_SIZE_M
    )
    if not tags:
        bot.reset_motors()
        continue

    tag = min(tags, key=lambda t: float(t.pose_t[2].item()))
    x, y, z = tag.pose_t.flatten().astype(float)

    error_x = x
    error_z = z - TARGET_DISTANCE_M

    vx_mm = P(error_x, Kx) if abs(error_x) > CENTER_TOLERANCE_M else 0
    vy_mm = P(error_z, Kz) if abs(error_z) > DIST_TOLERANCE_M else 0

    if vx_mm == 0 and vy_mm == 0:
        bot.reset_motors()
    else:
        bot.translation(vx_mm, vy_mm)
```

---

## 10) Change Log

- **Aug 15, 2025** — Default distance changed from **2 ft (0.61 m)** to **18 in (0.4572 m)**. Fixed NumPy deprecation with `.item()` extraction.

---

## 11) FAQs

**Q: How big should the tag be?**  
A: Any size works, but set `TAG_SIZE_M` to the printed **black square** size. Bigger tags are more stable at distance.

**Q: Can multiple followers trail one leader?**  
A: Yes. Give each follower the same program; they’ll each track the closest visible tag (ideally the tag on the bot ahead).

**Q: What happens if two tags are in view?**  
A: The script follows the one with the **smallest Z** (closest). If you need specific IDs, add a filter step before `min(...)`.

---

## 12) License / Notice

Use at your own risk in controlled environments. Ensure human supervision and physical safety measures.
