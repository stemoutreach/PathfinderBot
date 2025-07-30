#!/usr/bin/env python3
import time
import cv2
from flask import Flask, render_template_string, request, jsonify

from pf_AprilCamera import cam, detector, camera_params, TAG_SIZE_M, TAG_TABLE
from pf_April_nav_web_drive_store import bot, nav, PickupBlock

app = Flask(__name__)

# HTML template with new Continue Nav button
HTML = """
<!DOCTYPE html>
<html>
<head>
  <title>Robot Control</title>
  <script>
    function cmd(action) {
      fetch('/cmd', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ action: action })
      }).then(r => r.json()).then(data => {
        console.log(data);
        document.getElementById('status').innerText = data.status;
      });
    }
  </script>
</head>
<body>
  <h1>Robot Navigation Control</h1>
  <div>
    <button onclick="cmd('start_nav')">Start Nav</button>
    <button onclick="cmd('stop_nav')">Stop Nav</button>
    <button onclick="cmd('continue_nav')">Continue Nav</button>
  </div>
  <div id="status" style="margin-top:16px;color:green;">Ready.</div>
</body>
</html>
"""

@app.route('/')
def index():
    return render_template_string(HTML)

# Wrapper functions from original code
@app.route('/cmd', methods=['POST'])
def handle_cmd():
    data = request.get_json()
    action = data.get('action', '')

    if action == 'start_nav':
        nav.start()
        return jsonify(status="Started navigation")
    elif action == 'stop_nav':
        nav.stop()
        return jsonify(status="Navigation stopped")
    elif action == 'continue_nav':
        status = continue_nav()
        return jsonify(status=status)
    else:
        return jsonify(status=f"Unknown action '{action}'")

def continue_nav():
    frame = cam.frame
    if frame is None:
        return "No camera frame available."

    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    tags = detector.detect(gray, estimate_tag_pose=True,
                           camera_params=camera_params, tag_size=TAG_SIZE_M)

    if not tags:
        return "No AprilTag detected."

    tag = min(tags, key=lambda t: t.pose_t[2])
    action_name = TAG_TABLE.get(tag.tag_id)
    status_msg = f"Tag {tag.tag_id} detected → action: {action_name}"

    # Map actions to movement
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
        bot.set_velocity(0, 0, 30); time.sleep(1.0)
        bot.set_velocity(0, 0, 30); time.sleep(1.0)
        bot.translation(40, 0); time.sleep(1.0)
    elif action_name == "TURN_AROUND_STRAFE_LEFT":
        bot.set_velocity(0, 0, -30); time.sleep(1.0)
        bot.set_velocity(0, 0, -30); time.sleep(1.0)
        bot.translation(-40, 0); time.sleep(1.0)
    elif action_name == "FINISH":
        status_msg += " — FINISH tag reached."
    else:
        status_msg += " — Unknown tag action."

    bot.reset_motors()
    return status_msg

if __name__ == '__main__':
    print("Launching web controller with Continue Nav support...")
    app.run(host='0.0.0.0', port=5000)
