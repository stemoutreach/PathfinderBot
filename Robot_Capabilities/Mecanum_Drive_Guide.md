
# 🚗 Mecanum Drive Guide

`mecanum.py` provides the **`MecanumChassis`** class that lets you drive the robot in any direction (omnidirectional) and rotate in place using four mecanum wheels.

---

## 🛠️ Prerequisites

- `mecanum.py` and `Board.py` in the same folder.
- PathfinderBot powered on and connected.
- Python 3 running on Raspberry Pi.

---

## 📚 Class Overview

| Method | Purpose |
|--------|---------|
| `__init__(a=67, b=59, wheel_diameter=65)` | Configure wheel‑base geometry (in mm). |
| `reset_motors()` | Stop all four motors and clear internal state. |
| `set_velocity(velocity, direction, angular_rate, fake=False)` | Main polar‑coordinate drive command. |
| `translation(velocity_x, velocity_y, fake=False)` | Convenience Cartesian drive command (no rotation). |

---

### Geometry Parameters

- **`a`** – Half the front‑to‑back wheel spacing (mm)
- **`b`** – Half the left‑to‑right wheel spacing (mm)
- **`wheel_diameter`** – Wheel diameter (mm)

These affect how the robot calculates wheel speeds for rotation.

---

## 🎮 Coordinate System

- **Direction** is in **degrees** (0 °–360 °).
- 0 ° points **right** (+X)  
- 90 ° points **forward** (+Y)  
- 180 ° points **left** (‑X)  
- 270 ° points **backward** (‑Y)

```
          90°
           ↑
180° ← robot → 0°
           ↓
         270°
```

---

## 🚦 Basic Usage

```python
from mecanum import MecanumChassis
import time

bot = MecanumChassis()

# 1. Drive forward at 200 mm/s for 2 s
bot.set_velocity(200, 90, 0)
time.sleep(2)

# 2. Strafe right (east) at 150 mm/s
bot.set_velocity(150, 0, 0)
time.sleep(1.5)

# 3. Rotate in place clockwise (angular_rate > 0)
bot.set_velocity(0, 0, 80)   # 80 deg/s spin
time.sleep(2)

# 4. Full stop
bot.reset_motors()
```

---

## ➕ Cartesian Helper

`translation(vx, vy)` converts **X/Y velocities** into a direction and magnitude automatically:

```python
# Move diagonally up‑right (vx=100, vy=100 mm/s)
bot.translation(100, 100)
```

Set `fake=True` to **calculate** but **not move** (helpful for debugging):

```python
vel, dir_deg = bot.translation(100, 50, fake=True)
print(vel, dir_deg)
```

---

## 🔄 Rotation While Translating

Combine motion and spin:

```python
# Slide left at 150 mm/s while rotating 45 deg/s CCW
bot.set_velocity(150, 180, -45)
```

---

## 🛑 Emergency Stop

Always stop motors when exiting:

```python
try:
    # driving code…
finally:
    bot.reset_motors()
```

---

## ✅ Quick Reference

| Action | Call |
|--------|------|
| Forward | `set_velocity(v, 90, 0)` |
| Backward | `set_velocity(v, 270, 0)` |
| Strafe Right | `set_velocity(v, 0, 0)` |
| Strafe Left | `set_velocity(v, 180, 0)` |
| Rotate CW | `set_velocity(0, 0, +rate)` |
| Rotate CCW | `set_velocity(0, 0, -rate)` |

Enjoy effortless omnidirectional driving with your PathfinderBot!
