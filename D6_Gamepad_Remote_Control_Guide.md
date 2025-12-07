# D6 Gamepad Remote Control Guide

This guide explains how to drive PathfinderBot with a Logitech F710 wireless gamepad using the script `pf_mecanum_gamepad_drive.py`. It combines mecanum drive, analog triggers, bumpers, and arm presets so your team can practice smooth, precise driving.

[**Mecanum Gamepad Drive Python script**](/code/pf_mecanum_gamepad_drive.py)

---

## Prerequisites

- PathfinderBot fully assembled and tested  
  - Completed: **B1 Robot Assembly**, **C1/C2/C3 Setup & Connect**, **D1 Basic Drive**, **E5 Mecanum Drive**.
- `pf_mecanum_gamepad_drive.py` copied into `/home/robot/code` on the robot.
- Python 3 on the RobotPi.
- Pygame installed on the RobotPi:

```bash
sudo apt-get update
sudo apt-get install python3-pygame
```

- Logitech Gamepad F710:
  - Wireless USB receiver plugged into the **RobotPi**.
  - Gamepad switched **ON**.
  - **X** mode selected (switch on the back moved to **X**, not D).

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
sudo python3 pf_mecanum_gamepad_drive.py
```

You should see messages like:

```text
Initializing PathfinderBot hardware...
Initializing Logitech F710 gamepad...
Using gamepad: Logitech Gamepad F710 with X axes and Y buttons.
Gamepad control ready. Sticks = tank/strafe, triggers = analog forward/back, bumpers = turn, A = look_forward, B = pickup_block.
```

If you see **“No gamepads detected. Is the F710 receiver plugged in?”**, check the dongle, batteries, and X-mode, then run the script again.

---

## Step 3 – Driving with the Sticks

The script uses tank-style control plus mecanum strafing:

- **Left stick – Y axis**: controls the **left** side of the robot (forward/back).
- **Right stick – Y axis**: controls the **right** side of the robot (forward/back).
- **Both sticks up**: drive straight forward.
- **Both sticks down**: drive straight backward.
- **Left / Right stick – X axis**: contribute to left/right strafe. The script averages both X axes for smooth strafing.

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

The script also maps F710 buttons to arm/camera presets:

| Button | Action                                           |
|--------|--------------------------------------------------|
| **A**  | `look_forward` – standard forward-looking pose   |
| **B**  | `pickup_block` – arm sequence to pick up a block |
| **Y**  | `say_yes` – nodding motion                       |
| **X**  | `say_no` – side-to-side motion                   |

Suggested use:

- Press **A** at the start of a run to reset the arm to a known pose.
- Use **B** when the gripper is over a block to run the full pickup sequence.
- Use **Y** or **X** as “celebration” or feedback motions during challenges.

---

## Step 6 – D-Pad Drop Directions

The D-Pad triggers different **drop-block** sequences so you can deliver a carried block in different directions relative to the robot:

| D-Pad Direction | Action                | Description                                 |
|-----------------|-----------------------|---------------------------------------------|
| **Up**          | `forward_drop_block`  | Drop a block in front of the robot          |
| **Down**        | `backward_drop_block` | Drop a block behind the robot               |
| **Left**        | `left_drop_block`     | Rotate/pose to drop a block on the **left** |
| **Right**       | `right_drop_block`    | Rotate/pose to drop a block on the **right**|

Typical sequence during a challenge:

1. Drive to a block and line up.
2. Press **B** to `pickup_block`.
3. Drive to the delivery zone.
4. Use the D-Pad direction that matches where you want to place the block.
5. Press **A** to return to the `look_forward` pose.

---

## Step 7 – Safety Controls

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

At the top of `pf_mecanum_gamepad_drive.py` there are constants you can adjust if you want different behavior:

```python
MAX_LINEAR_SPEED = 80.0   # mm/s
MAX_ROT_SPEED    = 50.0
ROT_SCALE        = 0.008
DEADZONE         = 0.15

TRIGGER_DRIVE_VALUE = 1.0
BUMPER_TURN_VALUE   = 0.8
TRIGGER_THRESHOLD   = 0.1
```

- **MAX_LINEAR_SPEED** – overall forward/back/strafe scale (higher = faster).
- **MAX_ROT_SPEED + ROT_SCALE** – how quickly the robot can rotate.
- **DEADZONE** – how much joystick movement is ignored around center.
- **TRIGGER_DRIVE_VALUE** – scales trigger-controlled speed.
- **BUMPER_TURN_VALUE** – how hard the bumpers turn.

Make small changes, test briefly, and keep values conservative during workshops so teams can focus on strategy and teamwork.

---

## Quick Reference – Gamepad Map

| Control           | Action                                                     |
|-------------------|------------------------------------------------------------|
| Left stick (Y)    | Left side forward/back                                    |
| Right stick (Y)   | Right side forward/back                                   |
| Sticks (X)        | Strafe left/right (mecanum)                               |
| Right trigger     | Analog forward (overrides sticks)                         |
| Left trigger      | Analog backward (overrides sticks)                        |
| Right bumper      | Turn right in place                                       |
| Left bumper       | Turn left in place                                        |
| A                 | Look forward pose                                         |
| B                 | Pickup block sequence                                     |
| Y                 | Say yes                                                   |
| X                 | Say no                                                    |
| D-Pad Up          | Forward drop block                                        |
| D-Pad Down        | Backward drop block                                       |
| D-Pad Left        | Left drop block                                           |
| D-Pad Right       | Right drop block                                          |
| Back              | STOP – reset motors                                       |
| Start             | Quit gamepad drive script                                 |

Use this guide with your team to practice **smooth driving, precise block handling, and clear driver–spotter communication** during the PathfinderBot challenge.

---

## Setup AutoStart

Configure your PathfinderBot to automatically start the mecanum gamepad drive script after boot.

[**AutoStart Guide**](/Reference/PathfinderBot_Gamepad_AutoStart_Guide.md)


