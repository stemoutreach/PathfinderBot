# D6 Gamepad Remote Control Guide

This guide explains how to drive PathfinderBot with a Logitech F710 wireless gamepad using:

- `pf_mecanum_gamepad_drive.py` (mecanum drive + triggers/bumpers + arm presets)
- Optional **Sonar “proximity alerts” mode** (LEDs + rumble + beeps)

[**Mecanum Gamepad Drive Python script**](/code/pf_mecanum_gamepad_drive.py)

---

## Prerequisites

- PathfinderBot fully assembled and tested  
  - Completed: **B1 Robot Assembly**, **C1/C2/C3 Setup & Connect**, **D1 Basic Drive**, **E5 Mecanum Drive**
- `pf_mecanum_gamepad_drive.py` copied into `/home/robot/code` on the robot
- Pygame installed on the RobotPi:

```bash
sudo apt-get update
sudo apt-get install python3-pygame joystick
lsusb | grep -i logitech
```

- Logitech Gamepad F710:
  - Wireless USB receiver plugged into the **RobotPi**
  - Gamepad switched **ON**
  - Back switch set to **X** (XInput), not **D**
- Optional (recommended): **Sonar sensor** connected
  - If the Sonar module isn’t installed, the script will print a warning and Sonar mode won’t enable.

---

## Step 1 – SSH into the Robot

From your Pi500 (or laptop), open a terminal and SSH into the RobotPi:

```bash
ssh robot@ROBOT_IP_ADDRESS
```

Replace `ROBOT_IP_ADDRESS` with the IP you used in **C2 RobotPi WiFi Setup** (for example `10.0.0.51`).

Change to the code folder:

```bash
cd /home/robot/code
```

---

## Step 2 – Start Gamepad Drive

Run the gamepad script with sudo so it can access the hardware:

```bash
sudo python pf_mecanum_gamepad_drive.py
```

You should see messages like:

```text
Initializing PathfinderBot hardware...
Initializing Logitech F710 gamepad...
Using gamepad: Logitech Gamepad F710 with X axes and Y buttons.
Gamepad control ready...
```

If you see **“No gamepads detected…”**, check the dongle, batteries, and X-mode, then run the script again.

---

## Step 3 – Driving with the Sticks

The script uses tank-style control plus mecanum strafing:

- **Left stick – Y axis**: controls the **left/right drive mix** (tank-style)
- **Right stick – Y axis**: controls the **other side** (tank-style)
- **Left / Right stick – X axis**: contributes to left/right **strafe** (the script averages both X axes)

Small joystick movements near center are ignored by a **deadzone** so the robot doesn’t creep when the sticks are centered.

---

## Step 4 – Triggers & Bumpers (Precision Driving)

The triggers give you **analog speed control**:

| Control           | Action                                               |
|-------------------|------------------------------------------------------|
| **Right trigger** | Drive **forward** (both sides) – more pull = faster |
| **Left trigger**  | Drive **backward** (both sides) – more pull = faster |

- If **only** the right trigger is pressed, it overrides the sticks and drives forward.
- If **only** the left trigger is pressed, it overrides the sticks and drives backward.
- If both are pressed or neither is pressed, the script uses the stick commands.

The bumpers give **digital in-place turns**:

| Control           | Action                  |
|-------------------|-------------------------|
| **Right bumper**  | Turn **right** in place |
| **Left bumper**   | Turn **left** in place  |

Use triggers for smooth approach/retreat and bumpers for quick orientation changes.

---

## Step 5 – Face Buttons (Arm & Camera Actions)

The script maps F710 buttons to arm/camera motions:

| Button | Action |
|--------|--------|
| **A**  | `look_forward` – standard forward-looking pose |
| **B**  | `look_sad` – “sad” motion/pose |
| **Y**  | `say_yes` – nodding motion |
| **X**  | `say_no` – side-to-side motion |

Suggested use:
- Press **A** at the start of a run to reset the arm to a known pose.
- Use **Y** / **X** as “feedback” motions during challenges.

---

## Step 6 – D-Pad Actions

The D-Pad triggers quick sequences (useful for demos and student driving):

| D-Pad Direction | Action |
|-----------------|--------|
| **Up**          | `pickup_block()` |
| **Down**        | `backward_drop_block()` |
| **Left**        | `left_pickup_block()` |
| **Right**       | `right_pickup_block()` |

> Tip: These are “one-press” sequences. Keep people clear of the arm while they run.

---

## Step 7 – Sonar Proximity Alerts Mode (R3 ON / L3 OFF)

Sonar mode is designed for **workshop driving**: it adds *visual + haptic + audio* feedback when the robot gets close to obstacles.

| Control | Action |
|---------|--------|
| **R3** (Right stick click) | Turn **Sonar mode ON** |
| **L3** (Left stick click)  | Turn **Sonar mode OFF** |

### What you’ll see/hear/feel when Sonar is ON

**Robot LEDs (distance color):**
- **Green** when farther than ~16 in (≥ 406 mm)
- **Yellow** when ~8–16 in (203–406 mm)
- **Red** when closer than ~8 in (< 203 mm)

**Fun mode (sonar sensor LEDs):**
- When NOT critical, the **two LEDs on the sonar sensor change to random colors** every ~0.5 seconds.

### Close / Critical alerts

**Close zone (red zone) — closer than ~8 in (< 203 mm):**
- Robot LEDs **flash red**
- Gamepad does a **soft rumble pulse**
- Robot does a **short beep**

**Critical zone — ~3 in or less (≤ 75 mm):**
- Robot LEDs **flash red fast**
- Sonar LEDs go **solid red**
- Gamepad does a **strong rumble pulse**
- Robot does **rapid beeps**
- When you back away (> ~3 in), it immediately returns to normal behavior.

---

## Step 8 – Safety Controls

Always keep a hand near the **Back** and **Start** buttons:

| Button   | Action                      |
|----------|-----------------------------|
| **Back** | **STOP** – reset all motors |
| **Start**| Quit the program            |

You can also press **Ctrl + C** in the terminal to stop the script. The program will reset the motors and then exit.

> **Safety Tip:**  
> Practice first at low speed in an open area. Increase speed only after drivers are comfortable with the controls.

---

## Optional – Tuning Sensitivity

At the top of `pf_mecanum_gamepad_drive.py` there are constants you can adjust:

```python
MAX_LINEAR_SPEED = 80.0
MAX_ROT_SPEED    = 50.0
ROT_SCALE        = 0.008
DEADZONE         = 0.15

SONAR_DISTANCE_THRESHOLD_MM = 203   # ~8 inches (red/close)
SONAR_CAUTION_THRESHOLD_MM  = 406   # ~16 inches (yellow/green boundary)
SONAR_CRITICAL_THRESHOLD_MM = 75   # ~3 inches (critical)
```

Make small changes, test briefly, and keep values conservative during workshops so teams can focus on driving and teamwork.

---

## Quick Reference – Gamepad Map

| Control           | Action |
|-------------------|--------|
| Left stick (Y)    | Tank drive (one side) |
| Right stick (Y)   | Tank drive (other side) |
| Sticks (X)        | Strafe left/right (mecanum) |
| Right trigger     | Analog forward (overrides sticks) |
| Left trigger      | Analog backward (overrides sticks) |
| Right bumper      | Turn right in place |
| Left bumper       | Turn left in place |
| A                 | Look forward pose |
| B                 | Sad pose |
| Y                 | Say yes |
| X                 | Say no |
| D-Pad Up          | Pickup block sequence |
| D-Pad Down        | Backward drop block |
| D-Pad Left        | Left pickup block |
| D-Pad Right       | Right pickup block |
| R3 (Right stick click) | Sonar mode ON |
| L3 (Left stick click)  | Sonar mode OFF |
| Back              | STOP – reset motors |
| Start             | Quit script |

---

## Setup AutoStart

Configure your PathfinderBot to automatically start the mecanum gamepad drive script after boot.

[**AutoStart Guide**](/Reference/PathfinderBot_Gamepad_AutoStart_Guide.md)
