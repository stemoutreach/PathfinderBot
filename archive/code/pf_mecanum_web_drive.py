#!/usr/bin/env python3
"""
pf_mecanum_web_drive.py – PathfinderBot web control with diagonal drive, rotation, and speed sliders
"""

import time
import math
import cv2
from flask import Flask, Response, request, jsonify, render_template_string

from Camera import Camera
from mecanum import MecanumChassis as Mecanum
from pf_start_robot import initialize_robot

initialize_robot()

cam = Camera(resolution=(640, 480))
cam.camera_open()
bot = Mecanum()

speed_move = 40
speed_rot = 35
ROT_SCALE = 0.008
_DIAG_RATIO = 1 / math.sqrt(2)

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

app = Flask(__name__)

def gen_frames():
    boundary = b'--frame\r\n'
    while True:
        frame = cam.frame
        if frame is None:
            time.sleep(0.01); continue
        ok, buf = cv2.imencode('.jpg', frame)
        if ok:
            yield boundary + b'Content-Type: image/jpeg\r\n\r\n' + buf.tobytes() + b'\r\n'

HTML_PAGE = """<!doctype html>
<html lang='en'><head><meta charset='utf-8'>
<title>PathfinderBot Control</title>
<style>
 body{font-family:sans-serif;text-align:center;background:#111;color:#eee;margin:0}
 h1{margin-top:10px}
 #vid{border:4px solid #555;border-radius:8px}
 .pad button{margin:4px;padding:16px 24px;font-size:1.2rem;border-radius:8px;width:64px}
 .slider{width:240px}
 label{margin-right:6px}
</style></head><body>
<h1>PathfinderBot Remote Control</h1>

<img id='vid' src='{{ url_for("video_feed") }}' width='640' height='480'><br>

<div class="pad" style="display:inline-block">
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
  fetch('/cmd',{method:'POST',
               headers:{'Content-Type':'application/json'},
               body:JSON.stringify({action:c})});
}
function setSpeed(type,val){
  if(type==='move') document.getElementById('moveVal').textContent=val;
  else              document.getElementById('rotVal').textContent=val;
  fetch('/speed',{method:'POST',
                  headers:{'Content-Type':'application/json'},
                  body:JSON.stringify({type:type,value:parseInt(val)})});
}
</script></body></html>"""

@app.route('/')
def index():
    return render_template_string(HTML_PAGE, move=speed_move, rot=speed_rot)

@app.route('/video_feed')
def video_feed():
    return Response(gen_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/cmd', methods=['POST'])
def command():
    act = request.json.get('action','')
    actions = {
        'forward': forward, 'backward': backward,
        'left': left, 'right': right,
        'turn_left': turn_left, 'turn_right': turn_right,
        'diag_nw': diag_nw, 'diag_ne': diag_ne,
        'diag_sw': diag_sw, 'diag_se': diag_se,
        'stop': stop
    }
    func = actions.get(act)
    if not func:
        return jsonify(error=f'unknown action {act}'), 400
    func()
    return jsonify(status='ok')

@app.route('/speed', methods=['POST'])
def set_speed():
    global speed_move, speed_rot
    typ   = request.json.get('type')
    value = int(request.json.get('value', 0))
    value = max(10, min(100, value))
    if typ == 'move':
        speed_move = value
    elif typ == 'rot':
        speed_rot = value
    else:
        return jsonify(error='invalid speed type'), 400
    return jsonify(status='ok', move=speed_move, rot=speed_rot)

if __name__ == '__main__':
    try:
        app.run(host='0.0.0.0', port=5000, threaded=True)
    finally:
        cam.camera_close()
