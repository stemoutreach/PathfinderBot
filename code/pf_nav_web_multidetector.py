#!/usr/bin/env python3
import time, cv2
from flask import Flask, jsonify, Response
from pf_AprilCamera import Camera, TAG_TABLE
from detectors import AprilTagDetector, ObjectDetector, ColorDetector, BlockDetector
from detection_manager import DetectionManager
from overlay_utils import draw_overlay

app = Flask(__name__)
cam = Camera(resolution=(640,480)); cam.camera_open()

detectors = {
    "apriltag": AprilTagDetector(camera_obj=cam, frame_skip=1, estimate_pose=True, tag_size_m=0.045),
    "object":   ObjectDetector(conf=0.5, frame_skip=1),
    "color":    ColorDetector(),
    "block":    BlockDetector(),
}
manager = DetectionManager(cam, detectors, initial="apriltag")

def mjpeg():
    while True:
        frame = cam.frame
        if frame is None: time.sleep(0.01); continue
        vis = draw_overlay(frame.copy(), manager.get_latest())
        ok, jpg = cv2.imencode('.jpg', vis)
        if ok:
            yield (b'--frame\r\nContent-Type: image/jpeg\r\n\r\n' + bytearray(jpg) + b'\r\n')

@app.route("/video_feed")
def video_feed():
    return Response(mjpeg(), mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route("/mode/<name>", methods=["POST"])
def set_mode(name):
    try:
        manager.set_mode(name)
        return jsonify({"ok":True,"mode":manager.get_mode()})
    except Exception as e:
        return jsonify({"ok":False,"error":str(e)}), 400

@app.route("/status")
def status():
    latest = manager.get_latest() or {}
    return jsonify({"mode":manager.get_mode(),"debug":latest.get("debug",{}),"counts":len(latest.get("items",[]))})

@app.route("/")
def index():
    return """<html><body>
    <button onclick=fetch('/mode/apriltag',{method:'POST'}).then(()=>load())>Tags</button>
    <button onclick=fetch('/mode/object',{method:'POST'}).then(()=>load())>Objects</button>
    <button onclick=fetch('/mode/color',{method:'POST'}).then(()=>load())>Color</button>
    <button onclick=fetch('/mode/block',{method:'POST'}).then(()=>load())>Block</button>
    <span id=s></span><br><img src='/video_feed' style='max-width:640px'>
    <script>
    function load(){fetch('/status').then(r=>r.json()).then(j=>{s.innerText=' mode: '+j.mode+' items:'+j.counts})}
    setInterval(load,1000); load();
    </script></body></html>"""

if __name__ == "__main__":
    try:
        cv2.setNumThreads(1)
    except Exception: pass
    app.run(host="0.0.0.0", port=5001, threaded=True)
