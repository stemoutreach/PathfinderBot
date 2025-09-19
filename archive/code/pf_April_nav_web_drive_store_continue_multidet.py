#!/usr/bin/env python3
import time, math, cv2
from flask import Flask, Response, request, jsonify, render_template_string
import threading
import Board

from pf_AprilCamera import Camera, TAG_TABLE
from pupil_apriltags import Detector
from mecanum import MecanumChassis as Mecanum
from pf_AprilTagNavigator import AprilTagNavigator
from multidetector_integration import init_multidetector, register_multidetector_routes, overlay_with_current_result
from pf_start_robot import initialize_robot

initialize_robot()
voltage = 0.0

def voltageDetection():
    global voltage
    vi = 0
    dat = []
    previous_time = 0.00
    try:
        while True:
            if time.time() >= previous_time + 1.00:
                previous_time = time.time()
                volt = Board.getBattery() / 1000.0
                if 5.0 < volt < 8.5:
                    dat.insert(vi, volt)
                    vi += 1
                if vi >= 3:
                    vi = 0
                    voltage = sum(dat[:3]) / 3.0
            else:
                time.sleep(0.01)
    except Exception as e:
        print('Voltage error:', e)

threading.Thread(target=voltageDetection, daemon=True).start()

cam = Camera(resolution=(640, 480))
detector = Detector(families='tag36h11')
camera_params = (
    cam.mtx[0, 0],
    cam.mtx[1, 1],
    cam.mtx[0, 2],
    cam.mtx[1, 2]
)
TAG_SIZE_M = 0.045

cam.camera_open()
# --- Multi-detector manager (initial apriltag) ---
manager = init_multidetector(cam, initial="apriltag", tag_size_m=0.045, frame_skip=1, conf=0.5)

bot = Mecanum()
nav = AprilTagNavigator(cam)

speed_move = 40
speed_rot = 35
ROT_SCALE = 0.008
_DIAG_RATIO = 1 / math.sqrt(2)
current_tag_name = None

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
    time.sleep(1)

def LookDown():
    Board.setPWMServoPulse(1, 1500, 500)
    Board.setPWMServoPulse(3, 500, 1000)
    Board.setPWMServoPulse(4, 2500, 1000)
    Board.setPWMServoPulse(5, 1500, 500)
    Board.setPWMServoPulse(6, 1500, 1000)
    time.sleep(1)

def PickupBlock():

    Board.setPWMServoPulse(1, 1500, 2000)
    Board.setPWMServoPulse(3, 590, 2000)
    Board.setPWMServoPulse(4, 2500, 2000)
    Board.setPWMServoPulse(5, 700, 2000)
    Board.setPWMServoPulse(6, 1500, 2000)

    Board.setPWMServoPulse(5, 1818, 1000)
    time.sleep(1)
    Board.setPWMServoPulse(4, 2023, 300)
    Board.setPWMServoPulse(5, 2091, 300)
    time.sleep(.3)
    Board.setPWMServoPulse(1, 1932, 400)
    time.sleep(.4)
    Board.setPWMServoPulse(3, 750, 800)
    Board.setPWMServoPulse(5, 2364, 800)
    time.sleep(.8)
    Board.setPWMServoPulse(1, 1455, 300)
    Board.setPWMServoPulse(5, 2318, 300)
    time.sleep(.3)
    Board.setPWMServoPulse(5, 1841, 1000)
    time.sleep(1)
    Board.setPWMServoPulse(1, 1500, 2000)
    Board.setPWMServoPulse(3, 2500, 2000)
    Board.setPWMServoPulse(4, 500, 2000)
    Board.setPWMServoPulse(5, 1636, 2000)
    time.sleep(2)
    Board.setPWMServoPulse(1, 1932, 2000)
    time.sleep(1)
    Board.setPWMServoPulse(1, 1500, 2000)
    Board.setPWMServoPulse(3, 590, 2000)
    Board.setPWMServoPulse(4, 2500, 2000)
    Board.setPWMServoPulse(5, 700, 2000)
    Board.setPWMServoPulse(6, 1500, 2000)
    time.sleep(2)

app = Flask(__name__)
# Register multi-detector endpoints under /md (separate stream)
register_multidetector_routes(app, cam, manager, prefix="/md")

# Put these at the top, outside the function or as globals
last_box_pts = None
box_lost_counter = 0
BOX_PERSISTENCE = 5

def gen_frames():
    global current_tag_name, last_box_pts, box_lost_counter
    boundary = b'--frame\r\n'
    while True:
        frame = nav.get_frame() if nav.is_running() else cam.frame
        if frame is None:
            time.sleep(0.01)
            continue

        if not nav.is_running():
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            tags = detector.detect(gray, estimate_tag_pose=True,
                                   camera_params=camera_params, tag_size=TAG_SIZE_M)
            if tags:
                tag = min(tags, key=lambda t: t.pose_t[2])
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

            # Draw the last box if available
            if last_box_pts is not None:
                for i in range(4):
                    pt1 = tuple(last_box_pts[i])
                    pt2 = tuple(last_box_pts[(i + 1) % 4])
                    cv2.line(frame, pt1, pt2, (0, 255, 0), 1)  # Thin green line

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
<div style='font-size:1.2rem;margin:10px;'>
    Voltage: <span id='voltageValue' style='color:gray;'>--</span> V<br>
    Tag: <span id='tagValue'>--</span>
</div>
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
<div style="margin-top:16px">
  <button onclick="cmd('start_nav')">Start Nav</button>
  <button onclick="cmd('stop_nav')">Stop Nav</button>
  <button onclick="cmd('continue_nav')">Continue Nav</button>
</div>
<div style="margin-top:16px">
  <button onclick="cmd('look_forward')">Look Forward</button>
  <button onclick="cmd('look_down')">Look Down</button>
  <button onclick="cmd('pickup_block')">Pick Up Store</button>
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
<hr style='margin:20px 0;border:0;border-top:1px solid #444'>
<div>
  <h3>Detector Modes (separate stream)</h3>
  <button onclick="fetch('/md/mode/apriltag',{method:'POST'}).then(()=>mdRefresh())">Tags</button>
  <button onclick="fetch('/md/mode/object',{method:'POST'}).then(()=>mdRefresh())">Objects</button>
  <button onclick="fetch('/md/mode/color',{method:'POST'}).then(()=>mdRefresh())">Color</button>
  <button onclick="fetch('/md/mode/block',{method:'POST'}).then(()=>mdRefresh())">Block</button>
  <span id='mdStatus' style='margin-left:12px;color:gray'>mode: --, items: 0</span>
</div>
<img src="/md/video_feed" style="max-width:640px" />
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
function mdRefresh(){
  fetch('/md/status').then(r=>r.json()).then(j=>{
    document.getElementById('mdStatus').innerText = `mode: ${j.mode}, items: ${j.counts}`;
  }).catch(()=>{});
}
setInterval(() => {
  fetch('/voltage').then(res => res.json()).then(data => {
    const voltageEl = document.getElementById('voltageValue');
    voltageEl.textContent = data.voltage.toFixed(2);
    voltageEl.style.color = (data.voltage <= 7.2) ? 'red' : 'limegreen';
  });
  fetch('/tag_name').then(res => res.json()).then(data => {
    document.getElementById('tagValue').textContent = data.tag || '--';
  });
  mdRefresh();
}, 1000);
</script></body></html>"""

@app.route('/')
def index():
    return render_template_string(HTML_PAGE, move=speed_move, rot=speed_rot)

@app.route('/video_feed')
def video_feed():
    return Response(gen_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')


def continue_nav():
    global bot, cam, detector, camera_params, TAG_SIZE_M, TAG_TABLE
    frame = cam.frame
    if frame is None:
        return "No camera frame available."
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    tags = detector.detect(gray, estimate_tag_pose=True, camera_params=camera_params, tag_size=TAG_SIZE_M)
    if not tags:
        return "No AprilTag detected."
    tag = min(tags, key=lambda t: t.pose_t[2])
    action_name = TAG_TABLE.get(tag.tag_id)
    status_msg = f"Tag {tag.tag_id} detected → action: {action_name}"
    if action_name == "TURN_LEFT":
        bot.set_velocity(0, 0, -30); time.sleep(1.0)
    elif action_name == "TURN_RIGHT":
        bot.set_velocity(0, 0, 30); time.sleep(1.0)
    elif action_name == "STRAFE_LEFT":
        bot.translation(-40, 0); time.sleep(1.0)
    elif action_name == "STRAFE_RIGHT":
        bot.translation(40, 0); time.sleep(1.0)
    elif action_name == "BACKWARD_TURN_LEFT":
        bot.translation(0, -40); time.sleep(1.0)
        bot.set_velocity(0, 0, -30); time.sleep(1.0)
    elif action_name == "BACKWARD_TURN_RIGHT":
        bot.translation(0, -40); time.sleep(1.0)
        bot.set_velocity(0, 0, 30); time.sleep(1.0)
    elif action_name == "TURN_AROUND_STRAFE_RIGHT":
        bot.set_velocity(0, 0, 30); time.sleep(2.0)
        bot.translation(40, 0); time.sleep(1.0)
    elif action_name == "TURN_AROUND_STRAFE_LEFT":
        bot.set_velocity(0, 0, -30); time.sleep(2.0)
        bot.translation(-40, 0); time.sleep(1.0)
    elif action_name == "FINISH":
        status_msg += " — FINISH tag reached."
    else:
        status_msg += " — Unknown tag action."
    bot.reset_motors()
    return status_msg

@app.route('/cmd', methods=['POST'])
def command():
    act = request.json.get('action','')
    if act == 'start_nav':
        nav.start()
    elif act == 'stop_nav':
        nav.stop()
    elif act == 'continue_nav':
        return jsonify(status=continue_nav())
    else:
        actions = {
            'forward': forward, 'backward': backward,
            'left': left, 'right': right,
            'turn_left': turn_left, 'turn_right': turn_right,
            'diag_nw': diag_nw, 'diag_ne': diag_ne,
            'diag_sw': diag_sw, 'diag_se': diag_se,
            'stop': stop,
            'look_forward': LookForward,
            'look_down': LookDown,
            'pickup_block': PickupBlock
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
        nav.stop()
        cam.camera_close()
