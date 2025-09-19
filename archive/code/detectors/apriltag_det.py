import cv2
import numpy as np
try:
    from pupil_apriltags import Detector as AprilDetector
except Exception:
    AprilDetector = None
from .base import Detector

class AprilTagDetector(Detector):
    name = "apriltag"
    def __init__(self, camera_obj=None, families='tag36h11', frame_skip=1, estimate_pose=True, tag_size_m=0.045):
        self.camera_obj = camera_obj
        self.frame_skip = max(0, int(frame_skip))
        self._i = 0
        self.estimate_pose = bool(estimate_pose)
        self.tag_size = float(tag_size_m)
        self._det = None
        self._families = families
    def warmup(self):
        if AprilDetector is None:
            raise RuntimeError("pupil_apriltags not available")
        if self._det is None:
            self._det = AprilDetector(families=self._families)
    def _get_camera_params(self):
        if self.camera_obj is None: return None
        mtx = getattr(self.camera_obj, "mtx", None)
        if mtx is None: return None
        fx = float(mtx[0,0]); fy=float(mtx[1,1]); cx=float(mtx[0,2]); cy=float(mtx[1,2])
        return (fx,fy,cx,cy)
    def infer(self, frame_bgr):
        self._i = (self._i + 1) % (self.frame_skip + 1)
        if self._i: return {"type":"apriltag","items":[],"debug":{"skipped":True}}
        if self._det is None: self.warmup()
        gray = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2GRAY)
        params = self._get_camera_params() if self.estimate_pose else None
        if params:
            fx,fy,cx,cy = params
            res = self._det.detect(gray, estimate_tag_pose=True, camera_params=(fx,fy,cx,cy), tag_size=self.tag_size)
        else:
            res = self._det.detect(gray, estimate_tag_pose=False)
        items = []
        for d in res:
            it = {"id": int(d.tag_id), "corners": np.asarray(d.corners, float).tolist()}
            if hasattr(d, "pose_t") and d.pose_t is not None:
                it["pose_t"] = np.asarray(d.pose_t, float).reshape(-1).tolist()
            items.append(it)
        return {"type":"apriltag","items":items,"debug":{"count":len(items)}}
