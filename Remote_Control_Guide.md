# PathfinderBot Remote Control Guide

This guide explains how to control the PathfinderBot remotely using a web interface. Multiple versions are available:

- **Simple Web Drive** (`pf_simple_web_drive.py`) – Basic forward/back/turn controls
- **Mecanum Web Drive** (`pf_mecanum_web_drive.py`) – Adds diagonal movement and speed control sliders
- **AprilTag Navigation Web Drive** (`pf_April_nav_web_drive.py`) – Enables tag-based autonomous navigation and arm control
- **AprilTag Navigation + Store Mode** (`pf_April_nav_web_drive_store.py`) – Adds advanced pickup sequence for storing blocks

---

## 🧰 Prerequisites

- Raspberry Pi running PathfinderBot code
- Camera and Mecanum wheels properly set up
- Python dependencies installed (e.g., Flask, OpenCV, pupil_apriltags)
- Modules: `Camera`, `MecanumChassis`, `pf_StartRobot`, `AprilTagNavigator`, etc.

---

## 🚀 Starting the Web Server

1. **SSH Connection**

   Open a terminal and enter the following command, replacing the `XXX.XXX.XXX.XXX` with the robot's IP address:
   ```bash
   ssh robot@XXX.XXX.XXX.XXX
   ```

2. **Test drive each of the control scripts one at a time.  use Ctrl+C to stop a running script**
   ```bash
   cd /home/robot/code
   sudo python pf_simple_web_drive.py
   ```
   
   
   ```bash
   cd /home/robot/code
   sudo python pf_mecanum_web_drive.py
   ```
   
   
   ```bash
   cd /home/robot/code
   sudo python pf_April_nav_web_drive.py
   ```
   
   
   ```bash
   cd /home/robot/code
   sudo python pf_April_nav_web_drive_store.py
   ```

Then open your browser to:

```
http://<your-pi-ip>:5000
```

You’ll see live video from the camera and control buttons.

---

## 🕹️ Control Interface

  <img src="/zzimages/pf_simple_web_drive.jpg" width="200" >   <img src="/zzimages/pf_mecanum_web_drive.jpg" width="200" >   <img src="/zzimages/pf_April_nav_web_drive.jpg" width="200" >   <img src="/zzimages/pf_April_nav_web_drive_store.jpg" width="200" > 


### Shared Controls (All Scripts)

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

| Button         | Action                          |
|----------------|----------------------------------|
| ↖, ↗, ↙, ↘     | Diagonal movement               |

### Additional in AprilTag Versions

| Button         | Action                          |
|----------------|----------------------------------|
| Start Nav      | Begin tag-based navigation       |
| Stop Nav       | End tag-based navigation         |
| Look Forward   | Adjust arm to look forward       |
| Look Down      | Adjust arm to look down          |
| Pick Up        | Pick up a object        |
| Pick Up Store  | Extended pickup and place action |

---

## 🌀 Speed Sliders

All versions support speed control via sliders.

- **Move Speed** – Forward/backward/strafe (10–100 mm/s)
- **Turn Speed** – Rotational speed (mapped to radians/sec using a scaling factor)

Changes are applied via JavaScript fetch calls next time the button is pressed.

⚠️ Note: Setting movement or turn speed to high values (near 100) may cause the robot to respond sluggishly or make the web interface temporarily unresponsive to commands like Stop. Reduce speeds for better responsiveness and control during testing. 



---

## 📹 Camera + Tag Info

In AprilTag versions:

- Live camera feed shows detected tags
- Display includes:
  - Voltage (color-coded)
  - Currently visible AprilTag name (or ID)

---

## 🧠 How It Works

- `Camera` provides live MJPEG video
- Flask routes serve:
  - `/` – HTML with control panel
  - `/video_feed` – Camera feed
  - `/cmd` – JSON endpoint to issue movement commands
  - `/speed` – JSON endpoint to set speeds
  - `/voltage` – Battery voltage status (AprilTag versions)
  - `/tag_name` – Current visible tag name (AprilTag versions)

---

## 🧪 Customization

- Adjust `ROT_SCALE` if rotation is too fast or too slow
- Tweak `speed_move` and `speed_rot` defaults to suit your robot
- Modify servo sequences for arm movement in AprilTag versions
- Add new commands and HTML buttons as needed

---

## 🛑 Shutting Down

Press `CTRL+C` to stop the Flask server. The camera and navigation services will shut down automatically.

---

## 📁 Files

- `pf_simple_web_drive.py` – Basic drive with turn and speed sliders
- `pf_mecanum_web_drive.py` – Full Mecanum control with diagonals and sliders
- `pf_April_nav_web_drive.py` – Autonomous AprilTag navigation with basic arm control
- `pf_April_nav_web_drive_store.py` – Extended navigation and object pickup sequence
