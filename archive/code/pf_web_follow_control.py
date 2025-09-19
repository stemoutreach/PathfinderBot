#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
pf_web_follow_control.py (hardened)
Flask UI for manual drive + AprilTag follow. This version adds:
- A global lock around AprilTag detection (Detector is not guaranteed thread-safe)
- Single-thread OpenMP (`OMP_NUM_THREADS=1`) to reduce native race conditions
- Extra try/except around JPEG encoding

UI shows Voltage / Follow state / Tag above the stream.
"""

import os
os.environ.setdefault("OMP_NUM_THREADS", "1")  # reduce native thread races in pupil_apriltags/OpenCV

import time
import math
import threading
import cv2
from flask import Flask, Response, request, jsonify, render_template_string

import Board
from pupil_apriltags import Detector

# Local modules
from pf_AprilCamera import Camera, TAG_TABLE
from mecanum import MecanumChassis as Mecanum
from pf_start_robot import initialize_robot

# --------------------------- Global setup ---------------------------
initialize_robot()

# Voltage sampling thread (3-sample rolling average, ~1Hz)
voltage = 0.0
def voltage_task():
    global voltage
    vi = 0
    dat = []
    previous_time = 0.0
    while True:
        try:
            if time.time() >= previous_time + 1.0:
                previous_time = time.time()
                volt = Board.getBattery() / 1000.0
                if 5.0 < volt < 8.5:
                    if len(dat) < 3:
                        dat.append(volt)
                    else:
                        dat[vi % 3] = volt
                    vi += 1
                    voltage = sum(dat) / len(dat)
            else:
                time.sleep(0.01)
        except Exception as e:
            print('Voltage error:', e)
            time.sleep(0.1)

threading.Thread(target=voltage_task, daemon=True).start()

# Camera & detector
cam = Camera(resolution=(640, 480))
cam.camera_open(correction=True)

detector = Detector(families='tag36h11')
detector_lock = threading.Lock()   # <— guard all calls into detector.detect

camera_params = (
    cam.mtx[0, 0],
    cam.mtx[1, 1],
    cam.mtx[0, 2],
    cam.mtx[1, 2]
)

TAG_SIZE_M = 0.045
TARGET_DISTANCE_M = 0.4572 # 18 inches
CENTER_TOLERANCE_M = 0.02
DIST_TOLERANCE_M = 0.05
Kx = 600
Kz = 800
MAX_SPEED_MM_S = 350
MIN_SPEED_MM_S = 80
NO_TAG_TIMEOUT_S = 1.0

# Chassis
bot = Mecanum()

# Manual speed knobs
speed_move = 40
speed_rot = 35
ROT_SCALE = 0.008
_DIAG_RATIO = 1 / math.sqrt(2)

# Tag HUD state
current_tag_name = None
last_box_pts = None
box_lost_counter = 0
BOX_PERSISTENCE = 5

# --------------------------- Follow controller ---------------------------
class FollowController:
    def __init__(self):
        self._running = False
        self._th = None
        self._lock = threading.Lock()

    def _proportional_speed(self, err_m: float, gain: float) -> float:
        if abs(err_m) < 1e-6:
            return 0.0
        raw_mm_s = gain * err_m * 1000.0
        sgn = 1 if raw_mm_s > 0 else -1
        mag = abs(raw_mm_s)
        mag = max(MIN_SPEED_MM_S, min(MAX_SPEED_MM_S, mag))
        return sgn * mag

    def start(self):
        with self._lock:
            if self._running:
                return
            self._running = True
            self._th = threading.Thread(target=self._loop, daemon=True)
            self._th.start()

    def stop(self):
        with self._lock:
            self._running = False
        time.sleep(0.05)
        try:
            bot.reset_motors()
        except Exception:
            pass

    def is_running(self):
        with self._lock:
            return self._running

    def _loop(self):
        print("[follow] started")
        last_seen_ts = time.time()
        try:
            while self.is_running():
                frame = cam.frame
                if frame is None:
                    time.sleep(0.01)
                    continue
                try:
                    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                except Exception:
                    time.sleep(0.01)
                    continue

                # AprilTag detection guarded by lock
                with detector_lock:
                    try:
                        tags = detector.detect(gray, estimate_tag_pose=True,
                                               camera_params=camera_params, tag_size=TAG_SIZE_M)
                    except Exception as e:
                        print("Detector error:", e)
                        tags = []

                if not tags:
                    if (time.time() - last_seen_ts) > NO_TAG_TIMEOUT_S:
                        bot.reset_motors()
                    time.sleep(0.01)
                    continue

                try:
                    tag = min(tags, key=lambda t: float(getattr(t.pose_t[2], "item", lambda: t.pose_t[2])()))
                except Exception:
                    tag = min(tags, key=lambda t: float(t.pose_t[2]))

                x, y, z = map(float, tag.pose_t.flatten())
                err_x = x
                err_z = z - TARGET_DISTANCE_M

                vx_mm = self._proportional_speed(err_x, Kx) if abs(err_x) > CENTER_TOLERANCE_M else 0.0
                vy_mm = self._proportional_speed(err_z, Kz) if abs(err_z) > DIST_TOLERANCE_M else 0.0

                last_seen_ts = time.time()

                if vx_mm == 0.0 and vy_mm == 0.0:
                    bot.reset_motors()
                else:
                    bot.translation(vx_mm, vy_mm)

                time.sleep(0.01)
        finally:
            try:
                bot.reset_motors()
            except Exception:
                pass
            print("[follow] stopped")

follow = FollowController()

# --------------------------- Manual motion helpers ---------------------------
def forward():     bot.translation(0,  speed_move)
def backward():    bot.translation(0, -speed_move)
def left():        bot.translation(-speed_move, 0)
def right():       bot.translation( speed_move, 0)
def turn_left():   bot.set_velocity(0, 0, -speed_rot * ROT_SCALE)
def turn_right():  bot.set_velocity(0, 0,  speed_rot * ROT_SCALE)
def diag_nw():     c = speed_move * _DIAG_RATIO; bot.translation(-c,  c)
def diag_ne():     c = speed_move * _DIAG_RATIO; bot.translation( c,  c)
def diag_sw():     c = speed_move * _DIAG_RATIO; bot.translation(-c, -c)
def diag_se():     c = speed_move * _DIAG_RATIO; bot.translation( c, -c)
def stop():        bot.reset_motors()

def LookForward():
    Board.setPWMServoPulse(1, 1500, 500)
    Board.setPWMServoPulse(3, 700, 1000)
    Board.setPWMServoPulse(4, 2425, 1000)
    Board.setPWMServoPulse(5, 790, 1000)
    Board.setPWMServoPulse(6, 1500, 1000)

# --------------------------- Video feed ---------------------------
def gen_frames():
    global current_tag_name, last_box_pts, box_lost_counter
    boundary = b'--frame\r\n'
    while True:
        frame = cam.frame
        if frame is None:
            time.sleep(0.01)
            continue

        # When NOT following, update HUD and tag name (guarded)
        if not follow.is_running():
            try:
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                with detector_lock:
                    tags = detector.detect(gray, estimate_tag_pose=True,
                                           camera_params=camera_params, tag_size=TAG_SIZE_M)
                if tags:
                    try:
                        tag = min(tags, key=lambda t: float(getattr(t.pose_t[2], "item", lambda: t.pose_t[2])()))
                    except Exception:
                        tag = min(tags, key=lambda t: float(t.pose_t[2]))
                    current_tag_name = TAG_TABLE.get(tag.tag_id, str(tag.tag_id))
                    pts = tag.corners.astype(int)
                    last_box_pts = pts
                    box_lost_counter = BOX_PERSISTENCE
                else:
                    current_tag_name = None
                    if box_lost_counter > 0:
                        box_lost_counter -= 1
                    else:
                        last_box_pts = None

                if last_box_pts is not None:
                    for i in range(4):
                        pt1 = tuple(last_box_pts[i])
                        pt2 = tuple(last_box_pts[(i + 1) % 4])
                        cv2.line(frame, pt1, pt2, (0, 255, 0), 1)
            except Exception as e:
                print("HUD error:", e)

        try:
            ok, buf = cv2.imencode('.jpg', frame)
            if ok:
                yield boundary + b'Content-Type: image/jpeg\r\n\r\n' + buf.tobytes() + b'\r\n'
            else:
                time.sleep(0.01)
        except Exception as e:
            print("imencode error:", e)
            time.sleep(0.02)

# --------------------------- Web UI ---------------------------
app = Flask(__name__)

HTML = """<!doctype html>
<html lang='en'><head><meta charset='utf-8'>
<title>PathfinderBot — Drive & Follow</title>
<style>
 body{font-family:sans-serif;text-align:center;background:#111;color:#eee;margin:0}
 h1{margin-top:10px}
 #vid{border:4px solid #555;border-radius:8px}
 .pad button{margin:4px;padding:16px 24px;font-size:1.2rem;border-radius:8px;width:64px}
 .wide button{margin:4px;padding:12px 18px;font-size:1.0rem;border-radius:8px}
 .slider{width:240px}
 label{margin-right:6px}
 .status{margin-top:10px;font-size:1.1rem}
 .pill{display:inline-block;padding:4px 10px;border-radius:999px;background:#333;margin-left:8px}
</style></head><body>
<h1>PathfinderBot — Drive & Follow</h1>
<div class='status'>
  Voltage: <span id='voltageValue' style='color:gray;'>--</span> V
  <span class='pill'>Follow: <span id='followState'>off</span></span>
  <span class='pill'>Tag: <span id='tagValue'>--</span></span>
</div>
<img id='vid' src='{{ url_for("video_feed") }}' width='640' height='480'><br>

<div class="pad" style="display:inline-block;margin-top:8px">
  <button onclick="cmd('diag_nw')">↖</button>
  <button onclick="cmd('forward')">▲</button>
  <button onclick="cmd('diag_ne')">↗</button><br>
  <button onclick="cmd('left')">◀</button>
  <button onclick="cmd('stop')">■</button>
  <button onclick="cmd('right')">▶</button><br>
  <button onclick="cmd('diag_sw')">↙</button>
  <button onclick="cmd('backward')">▼</button>
  <button onclick="cmd('diag_se')">↘</button><br>
  <button onclick="cmd('turn_left')">⟲</button>
  <button onclick="cmd('turn_right')">⟳</button>
</div>

<div class="wide" style="margin-top:14px">
  <button onclick="followCmd('start')">Follow</button>
  <button onclick="followCmd('stop')">Unfollow</button>
  <button onclick="cmd('look_forward')">Look Forward</button>
</div>

<div style="margin-top:12px">
  <label>Move speed: <span id="moveVal">{{ move }}</span></label><br>
  <input class="slider" type="range" id="moveSpeed" min="10" max="100" step="5" value="{{ move }}"
         oninput="setSpeed('move', this.value)">
</div>
<div style="margin-top:8px">
  <label>Turn speed: <span id="rotVal">{{ rot }}</span></label><br>
  <input class="slider" type="range" id="rotSpeed" min="10" max="100" step="5" value="{{ rot }}"
         oninput="setSpeed('rot', this.value)">
</div>

<script>
function cmd(c){
  fetch('/cmd',{method:'POST', headers:{'Content-Type':'application/json'},
               body:JSON.stringify({action:c})});
}
function followCmd(action){
  fetch('/follow',{method:'POST', headers:{'Content-Type':'application/json'},
                   body:JSON.stringify({action})}).then(r=>r.json())
                   .then(s=>{document.getElementById('followState').textContent = s.running ? 'on' : 'off';});
}
function setSpeed(type,val){
  if(type==='move') document.getElementById('moveVal').textContent=val;
  else              document.getElementById('rotVal').textContent=val;
  fetch('/speed',{method:'POST', headers:{'Content-Type':'application/json'},
                  body:JSON.stringify({type:type,value:parseInt(val)})});
}
setInterval(() => {
  fetch('/voltage').then(res => res.json()).then(data => {
    const el = document.getElementById('voltageValue');
    el.textContent = data.voltage.toFixed(2);
    el.style.color = (data.voltage <= 7.2) ? 'red' : 'limegreen';
  });
  fetch('/tag_name').then(res => res.json()).then(data => {
    document.getElementById('tagValue').textContent = data.tag || '--';
  });
  fetch('/follow_state').then(res => res.json()).then(data => {
    document.getElementById('followState').textContent = data.running ? 'on' : 'off';
  });
}, 1000);
</script>
</body></html>"""

app = Flask(__name__)

@app.route('/')
def index():
    return render_template_string(HTML, move=speed_move, rot=speed_rot)

@app.route('/video_feed')
def video_feed():
    return Response(gen_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/cmd', methods=['POST'])
def command():
    act = request.json.get('action', '')
    # Prioritize manual control: stop follow when a manual move is issued
    if follow.is_running() and act not in ('stop', 'look_forward'):
        follow.stop()
    actions = {
        'forward': forward, 'backward': backward,
        'left': left, 'right': right,
        'turn_left': turn_left, 'turn_right': turn_right,
        'diag_nw': diag_nw, 'diag_ne': diag_ne,
        'diag_sw': diag_sw, 'diag_se': diag_se,
        'stop': stop,
        'look_forward': LookForward
    }
    func = actions.get(act)
    if not func:
        return jsonify(error=f'unknown action {act}'), 400
    func()
    return jsonify(status='ok')

@app.route('/follow', methods=['POST'])
def follow_toggle():
    act = request.json.get('action', '')
    if act == 'start':
        follow.start()
    elif act == 'stop':
        follow.stop()
    else:
        return jsonify(error='unknown follow action'), 400
    return jsonify(status='ok', running=follow.is_running())

@app.route('/follow_state')
def follow_state():
    return jsonify(running=follow.is_running())

@app.route('/speed', methods=['POST'])
def set_speed():
    global speed_move, speed_rot
    typ = request.json.get('type')
    try:
        value = int(request.json.get('value', 0))
    except Exception:
        return jsonify(error='value must be int'), 400
    value = max(10, min(100, value))
    if typ == 'move':
        speed_move = value
    elif typ == 'rot':
        speed_rot = value
    else:
        return jsonify(error='invalid speed type'), 400
    return jsonify(status='ok', move=speed_move, rot=speed_rot)

@app.route('/voltage')
def get_voltage():
    return jsonify(voltage=round(voltage, 2))

@app.route('/tag_name')
def get_tag_name():
    return jsonify(tag=current_tag_name)

if __name__ == '__main__':
    try:
        app.run(host='0.0.0.0', port=5000, threaded=True)
    finally:
        try:
            follow.stop()
        except Exception:
            pass
        cam.camera_close()
