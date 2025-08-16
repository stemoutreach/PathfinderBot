#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
pf_follow_me.py
Follow-me behavior: detect the closest AprilTag and maintain ~2 feet distance.
- Starts camera and initializes robot posture via pf_start_robot.initialize_robot().
- Drives toward the closest tag, centers on it, and keeps a target standoff (~0.61 m).
- Backs up if too close; stops if within tolerance; stops if no tag for a while.
"""
import time
import cv2
import numpy as np

from pupil_apriltags import Detector

# Local modules
from pf_AprilCamera import Camera
from mecanum import MecanumChassis
import pf_start_robot

# ---------------------------- Tunables ----------------------------
TAG_FAMILY = 'tag36h11'

# Physical size of the tag black square (meters). Keep aligned with your printed tags.
TAG_SIZE_M = 0.045      # If your tags are larger/smaller, update this.

# Desired following distance (meters) ~ 2 feet
TARGET_DISTANCE_M = 0.4572  # 18 inches

# Deadbands (meters)
CENTER_TOLERANCE_M = 0.02     # left/right centering tolerance
DIST_TOLERANCE_M   = 0.05     # forward/back distance tolerance

# Simple proportional gains (mm/s per meter error)
Kx = 600                      # strafing gain (left/right to center tag)
Kz = 800                      # forward/back gain to reach target distance

# Velocity clamps (mm/s)
MAX_SPEED_MM_S = 350
MIN_SPEED_MM_S = 80

# If no tag seen for this long, stop (seconds)
NO_TAG_TIMEOUT_S = 1.0

# Optional on-screen display
SHOW_WINDOW = False

# ---------------------------- Helpers ----------------------------
def proportional_speed(err_m: float, gain: float) -> float:
    """
    Convert positional error (meters) to chassis speed (mm/s) with min/max clamping.
    Sign of err_m controls direction.
    """
    if abs(err_m) < 1e-6:
        return 0.0
    raw_mm_s = gain * err_m * 1000.0
    direction = 1 if raw_mm_s > 0 else -1
    magnitude = abs(raw_mm_s)
    magnitude = max(MIN_SPEED_MM_S, magnitude)
    magnitude = min(MAX_SPEED_MM_S, magnitude)
    return direction * magnitude


def main():
    # Initialize robot posture (LEDs off, arm forward, motors stopped, startup beep)
    pf_start_robot.initialize_robot()

    # Set up camera and detector
    cam = Camera(resolution=(640, 480))
    cam.camera_open(correction=True)
    detector = Detector(families=TAG_FAMILY)

    # Grab intrinsics for pose estimation
    fx, fy = cam.mtx[0, 0], cam.mtx[1, 1]
    cx, cy = cam.mtx[0, 2], cam.mtx[1, 2]
    camera_params = (fx, fy, cx, cy)

    bot = MecanumChassis()
    last_seen_ts = time.time()

    print("[pf_follow_me] Running. Looking for AprilTags...")

    try:
        while True:
            frame = cam.frame
            if frame is None:
                time.sleep(0.01)
                continue

            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

            # Detect tags and estimate pose relative to camera
            tags = detector.detect(
                gray,
                estimate_tag_pose=True,
                camera_params=camera_params,
                tag_size=TAG_SIZE_M
            )

            if not tags:
                # If we've gone too long without seeing any tag, stop the robot.
                if (time.time() - last_seen_ts) > NO_TAG_TIMEOUT_S:
                    bot.reset_motors()
                if SHOW_WINDOW:
                    cv2.imshow("FollowMe", frame)
                    if cv2.waitKey(1) & 0xFF == 27:
                        break
                continue

            # Pick the closest tag (smallest z distance)
            tag = min(tags, key=lambda t: float(t.pose_t[2].item()))

            # Extract pose (x: right+, y: down+, z: forward+), meters
            x, y, z = tag.pose_t.flatten().astype(float)

            # Control errors
            error_x = x                            # center left/right -> strafe
            error_z = z - TARGET_DISTANCE_M        # positive if too far, negative if too close

            # Compute chassis velocities (mm/s). vx=left/right, vy=forward/back
            vx_mm = proportional_speed(error_x, Kx) if abs(error_x) > CENTER_TOLERANCE_M else 0.0
            vy_mm = proportional_speed(error_z, Kz) if abs(error_z) > DIST_TOLERANCE_M else 0.0

            # Update last seen time
            last_seen_ts = time.time()

            # Drive or stop inside deadbands
            if vx_mm == 0.0 and vy_mm == 0.0:
                bot.reset_motors()
            else:
                bot.translation(vx_mm, vy_mm)

            # Optional overlay for debugging
            if SHOW_WINDOW:
                # Draw tag outline
                pts = tag.corners.astype(int)
                for i in range(4):
                    p1, p2 = tuple(pts[i]), tuple(pts[(i + 1) % 4])
                    cv2.line(frame, p1, p2, (0, 255, 0), 2)
                # Telemetry
                cv2.putText(frame, f"Tag ID: {tag.tag_id}", (10, 25),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
                cv2.putText(frame, f"x_err={error_x:+.3f} m | z_err={error_z:+.3f} m",
                            (10, 50), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)
                cv2.imshow("FollowMe", frame)
                if cv2.waitKey(1) & 0xFF == 27:
                    break

            # Small loop delay to reduce CPU
            time.sleep(0.01)

    except KeyboardInterrupt:
        print("\n[pf_follow_me] Ctrl+C - stopping.")
    finally:
        # Always stop the robot and close resources
        try:
            bot.reset_motors()
        except Exception:
            pass
        cam.camera_close()
        if SHOW_WINDOW:
            cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
