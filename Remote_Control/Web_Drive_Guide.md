# PathfinderBot Remote Control Guide

This guide explains how to control the PathfinderBot remotely using a web interface. Two versions are provided:

- **Simple Web Drive** (`pf_simple_web_drive.py`) – Basic forward/back/turn controls
- **Mecanum Web Drive** (`pf_mecanum_web_drive.py`) – Adds diagonal movement and speed control sliders

---

## 🧰 Prerequisites

- Raspberry Pi running PathfinderBot code
- Camera and Mecanum wheels properly set up
- Python dependencies installed (e.g., Flask, OpenCV)
- Modules: `Camera`, `MecanumChassis`, `pf_StartRobot`

---

## 🚀 Starting the Web Server

Run either script:

```bash
python3 pf_simple_web_drive.py
# or
python3 pf_mecanum_web_drive.py
```

Then open your browser to:

```
http://<your-pi-ip>:5000
```

You’ll see live video from the camera and control buttons.

---

## 🕹️ Control Interface

### Shared Controls (Both Scripts)

| Button         | Action               |
|----------------|----------------------|
| ▲              | Move forward         |
| ▼              | Move backward        |
| ◀              | Strafe left          |
| ▶              | Strafe right         |
| ⟲              | Turn left            |
| ⟳              | Turn right           |
| ■              | Stop all movement    |

### Extra Controls in Mecanum Version

| Button         | Action                   |
|----------------|--------------------------|
| ↖, ↗, ↙, ↘     | Diagonal movement (NW, NE, SW, SE) |

---

## 🌀 Speed Sliders

Both versions support speed control via sliders.

- **Move Speed** – Forward/backward/strafe (10–100 mm/s)
- **Turn Speed** – Rotational speed (mapped to radians/sec using a scaling factor)

Changes are applied instantly via JavaScript fetch calls.

---

## 🧠 How It Works

- `Camera` provides live MJPEG video
- Flask routes serve:
  - `/` – HTML with control panel
  - `/video_feed` – Camera feed
  - `/cmd` – JSON endpoint to issue movement commands
  - `/speed` – JSON endpoint to set speeds

---

## 🧪 Customization

- Adjust `ROT_SCALE` if rotation is too fast or too slow
- Tweak `speed_move` and `speed_rot` defaults to suit your robot
- Add new buttons and corresponding functions for more features

---

## 🛑 Shutting Down

Press `CTRL+C` to stop the Flask server.

The camera will be properly closed on exit.

---

## 📁 Files

- `pf_simple_web_drive.py` – Basic drive with turn and speed sliders
- `pf_mecanum_web_drive.py` – Full Mecanum control with diagonals and sliders
