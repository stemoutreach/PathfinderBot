
# 🦾 Arm Inverse Kinematics Guide (`ArmMoveIK.py`)

`ArmMoveIK.py` lets you move the robot arm **by giving target X / Y / Z coordinates and a desired pitch angle** instead of manually tweaking every servo.  
It wraps two main parts:

1. **`InverseKinematics.py`** – converts position + pitch to joint angles (θ₃ θ₄ θ₅ θ₆).  
2. **`ArmIK` class** – converts those angles to PWM pulses and drives servos **3 – 6** through `Board.setPWMServoPulse()`.

---

## 🛠️ Prerequisites

| Requirement | Details |
|-------------|---------|
| Files       | `ArmMoveIK.py`, `InverseKinematics.py`, `Transform.py`, `Board.py` |
| Hardware    | 4‑DOF arm (servos 3–6) on PathfinderBot |
| Software    | Python, NumPy, Matplotlib (only needed for optional plotting) |

---

## 📚 Key Classes & Methods

| Component | Purpose |
|-----------|---------|
| `IK('arm')` | Calculates angles θ₃–θ₆ for a 4‑DOF arm. |
| `ArmIK.transformAngelAdaptArm()` | Maps θ‑angles to servo pulses, enforcing safe ranges. |
| `ArmIK.servosMove()` | Sends pulses to servos 3‑6 with an automatically chosen or user‑defined move‑time. |
| `ArmIK.setPitchRange()` | Finds a valid pitch **α** within a range that reaches `(x, y, z)` and returns pulses. |
| `ArmIK.setPitchRangeMoving()` | **One‑call helper**: finds α, moves servos, and returns `(servos, α, movetime)`. |

---

## 🧮 Coordinate & Pitch Convention

* **Units:** centimeters  
* **Origin (0,0,0):** center of Servo 1 axis  
* **Axes:**  
  * +X → right of robot  
  * +Y → forward (away)  
  * +Z → up  
* **Pitch α:** angle of end‑effector relative to horizontal plane  
  * 0 ° → horizontal  
  * +90 ° → pointing down  
  * –90 ° → pointing up

---

## 🚀 Quick‑Start Example

Move the gripper to **(x = 0 cm, y = 6 cm, z = 18 cm)** with a neutral pitch (0 °):

```python
import time
from ArmMoveIK import ArmIK

arm = ArmIK()

target_xyz = (0, 6, 18)   # cm
current_alpha = 0         # present pitch guess
alpha_min = -90           # allowed pitch range
alpha_max =  90

servos, alpha, movetime = arm.setPitchRangeMoving(
        target_xyz,
        current_alpha,
        alpha_min,
        alpha_max,
        movetime=1500)     # optional ms

print("Moved with pitch =", alpha, "° in", movetime, "ms")
time.sleep(2)
```

---

## 🤔 Troubleshooting

| Symptom | Likely Cause | Fix |
|---------|--------------|-----|
| `False` returned from `setPitchRangeMoving()` | Point outside workspace or pitch impossible | Try a different α range or closer coordinates |
| Logger warns “servoX out of range” | Calculated pulse beyond servo limits | Verify `setServoRange()` values or arm geometry in `IK.setLinkLength()` |
| Arm jitters on long moves | Move‑time too short | Increase `movetime` |

---

## 🛡️ Safety Tips

- **Calibrate** linkage lengths in `InverseKinematics.py` **before first use**.  
- Keep the arm clear of obstacles; IK doesn’t know your environment.  
- Call `arm.servosMove((1500,1500,1500,1500),500)` to return to a safe neutral pose.

---

## ✅ Summary Cheat‑Sheet

```python
from ArmMoveIK import ArmIK
arm = ArmIK()

# Move to (x,y,z) with best pitch between -45 and +45°
arm.setPitchRangeMoving((4,10,12), 0, -45, 45)

# Direct move with known θ‑angles (deg)
angles = ik.getRotationAngle((4,10,12), 30)
pulses = arm.transformAngelAdaptArm(**angles)
arm.servosMove((pulses['servo3'], pulses['servo4'], pulses['servo5'], pulses['servo6']), 1000)
```

You're now ready to command the PathfinderBot arm in 3‑D space!
