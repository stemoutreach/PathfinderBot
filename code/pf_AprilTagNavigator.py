
import threading, time, cv2
import numpy as np
from pupil_apriltags import Detector
from mecanum import MecanumChassis

TAG_SIZE_M = 0.045
TARGET_DISTANCE_M = 0.2
Kx = 600
Kz = 800
MAX_SPEED_MM_S = 350
MIN_SPEED_MM_S = 80
CENTER_TOLERANCE_M = 0.02
DIST_TOLERANCE_M = 0.05
TARGET_TAG_ID = None

def proportional_speed(err_m, gain):
    if abs(err_m) < 1e-6:
        return 0.0
    raw_mm_s = gain * err_m * 1000
    direction = 1 if raw_mm_s > 0 else -1
    magnitude = abs(raw_mm_s)
    magnitude = max(MIN_SPEED_MM_S, magnitude)
    magnitude = min(MAX_SPEED_MM_S, magnitude)
    return direction * magnitude

class AprilTagNavigator:
    def __init__(self, cam):
        self.cam = cam
        self.running = False
        self.thread = None
        self.frame = None

    def start(self):
        if not self.running:
            self.running = True
            self.thread = threading.Thread(target=self._run, daemon=True)
            self.thread.start()

    def stop(self):
        self.running = False
        if self.thread:
            self.thread.join()
            self.thread = None

    def is_running(self):
        return self.running

    def get_frame(self):
        return self.frame

    def _run(self):
        bot = MecanumChassis()
        detector = Detector(families='tag36h11')
        fx, fy, cx, cy = self.cam.mtx[0, 0], self.cam.mtx[1, 1], self.cam.mtx[0, 2], self.cam.mtx[1, 2]
        camera_params = (fx, fy, cx, cy)

        try:
            while self.running:
                frame = self.cam.frame
                if frame is None:
                    continue
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                tags = detector.detect(gray, estimate_tag_pose=True,
                                       camera_params=camera_params, tag_size=TAG_SIZE_M)

                if not tags:
                    bot.reset_motors()
                    self.frame = frame
                    continue

                tag = min(tags, key=lambda t: t.pose_t[2]) if TARGET_TAG_ID is None else next((t for t in tags if t.tag_id == TARGET_TAG_ID), None)
                if tag is None:
                    bot.reset_motors()
                    self.frame = frame
                    continue

                x, y, z = tag.pose_t.flatten()
                error_x = x
                error_z = z - TARGET_DISTANCE_M
                vx_mm = proportional_speed(error_x, Kx) if abs(error_x) > CENTER_TOLERANCE_M else 0
                vy_mm = proportional_speed(error_z, Kz) if abs(error_z) > DIST_TOLERANCE_M else 0

                if vx_mm == 0 and vy_mm == 0:
                    bot.reset_motors()
                    self.running = False  # Auto-stop
                    break
                else:
                    bot.translation(vx_mm, vy_mm)

                cv2.putText(frame, f"Tag ID: {tag.tag_id}", (10, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
                cv2.putText(frame, f"x_err={error_x:+.3f}m | z_err={error_z:+.3f}m", (10, 50), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)
                pts = tag.corners.astype(int)
                for i in range(4):
                    p1, p2 = tuple(pts[i]), tuple(pts[(i + 1) % 4])
                    cv2.line(frame, p1, p2, (0, 255, 0), 2)

                self.frame = frame
        finally:
            bot.reset_motors()
            self.frame = None
