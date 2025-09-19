import time, cv2
from flask import jsonify, Response
from detectors import AprilTagDetector, ObjectDetector, ColorDetector, BlockDetector
from detection_manager import DetectionManager
from overlay_utils import draw_overlay

def init_multidetector(cam, initial="apriltag", tag_size_m=0.045, frame_skip=1, conf=0.5, hsv_ranges=None):
    detectors = {
        "apriltag": AprilTagDetector(camera_obj=cam, frame_skip=frame_skip, estimate_pose=True, tag_size_m=tag_size_m),
        "object":   ObjectDetector(conf=conf, frame_skip=frame_skip),
        "color":    ColorDetector(hsv_ranges=hsv_ranges) if hsv_ranges is not None else ColorDetector(),
        "block":    BlockDetector(hsv_ranges=hsv_ranges) if hsv_ranges is not None else BlockDetector(),
    }
    return DetectionManager(cam, detectors, initial=initial)

def overlay_with_current_result(frame, manager):
    vis = frame.copy()
    return draw_overlay(vis, manager.get_latest())

def _mjpeg_generator(cam, manager):
    while True:
        frame = getattr(cam, "frame", None)
        if frame is None:
            time.sleep(0.01); continue
        vis = overlay_with_current_result(frame, manager)
        ok, jpg = cv2.imencode('.jpg', vis)
        if not ok: continue
        yield (b'--frame\r\nContent-Type: image/jpeg\r\n\r\n' + bytearray(jpg) + b'\r\n')

def register_multidetector_routes(app, cam, manager, prefix="/md"):
    @app.route(f"{prefix}/video_feed")
    def md_video_feed():
        return Response(_mjpeg_generator(cam, manager), mimetype='multipart/x-mixed-replace; boundary=frame')
    @app.route(f"{prefix}/mode/<name>", methods=["POST"])
    def md_set_mode(name):
        try:
            manager.set_mode(name)
            return jsonify({"ok": True, "mode": manager.get_mode()})
        except Exception as e:
            return jsonify({"ok": False, "error": str(e)}), 400
    @app.route(f"{prefix}/status")
    def md_status():
        latest = manager.get_latest() or {}
        return jsonify({
            "mode": manager.get_mode(),
            "debug": latest.get("debug", {}),
            "counts": len(latest.get("items", [])),
            "available_modes": list(manager.detectors.keys()),
        })
