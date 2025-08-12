# Inverse Kinematics

Inverse Kinematics (IK) answers the question: **“What joint angles do we need so the end‑effector (gripper) reaches a desired position and orientation?”**  
For PathfinderBot’s 5‑Degree‑of‑Freedom (DOF) servo arm, IK lets your code move the gripper precisely to pick up blocks and interact with AprilTag targets.

---

## 1. Arm Layout & Joint Nomenclature

Assuming the standard HiWonder MasterPi / ArmPi Pro configuration:

| Joint # | Name           | Axis & Type                   |
|---------|----------------|-------------------------------|
| 1       | Base Yaw       | Rotates arm around Z          |
| 2       | Shoulder Pitch | Rotates in vertical plane     |
| 3       | Elbow Pitch    | Rotates in vertical plane     |
| 4       | Wrist Pitch    | Rotates in vertical plane     |

> **Note:** A 5‑DOF arm allows full XYZ positioning and a single rotational axis. Full 6‑DOF orientation (roll, pitch, yaw) isn’t possible—so specify only the gripper roll or allow limited orientation adjustments.

---

## 2. Forward vs. Inverse Kinematics

- **Forward Kinematics (FK)**: Given joint angles (`θ₁…θ₅`), compute the end‑effector pose (T). Typically implemented using Denavit–Hartenberg (DH) parameters.
- **Inverse Kinematics (IK)**: Given desired pose `T`, compute `θ`. Can be solved **analytically** (closed‑form) or **numerically** (iterative).

**Why IK Is Harder**: Many arms have multiple (or no) solutions, and joint limits add constraints. A 5‑DOF arm may have redundant positional solutions but limited orientation control.

---

## 3. Suggested Workflow for PathfinderBot

1. **Model the Arm**
   - Measure all link lengths (L₁…L₄), gripper length, and joint offsets.
   - Construct your DH parameter table (`aᵢ`, `αᵢ`, `dᵢ`, `θᵢ`).

2. **Implement Forward Kinematics**
   - Verify FK results match real-world measurements.

3. **Derive Analytical IK**
   - Compute base angle (`θ₁`) from target X, Y:
     ```
     θ₁ = atan2(y, x)
     ```
   - Use a planar 2‑link law‑of‑cosines solution for Shoulder (`θ₂`) and Elbow (`θ₃`) in the vertical plane.
   - Determine Wrist Pitch (`θ₄`) to orient the end‑effector appropriately.

4. **Apply Joint Limits**
   - Clip or reject any invalid solutions beyond the physical range.

5. **Command the Servos**
   - Send smooth, interpolated servo commands (e.g., ease‑in/ease‑out ramps).

---

## 4. Example Python (Numerical IK via `ikpy`)

```python
from ikpy.chain import Chain
from ikpy.link import URDFLink
import numpy as np

arm_chain = Chain(name='5dof_arm', links=[
    URDFLink(rotation=[0, 0, 1], bounds=(-np.pi, np.pi)),        # Base
    URDFLink(length=0.06, rotation=[0, 1, 0], bounds=(-1.4, 1.4)),# Shoulder
    URDFLink(length=0.08, rotation=[0, 1, 0], bounds=(-1.4, 1.4)),# Elbow
    URDFLink(length=0.05, rotation=[0, 1, 0], bounds=(-1.4, 1.4)),# Wrist pitch
    URDFLink(rotation=[0, 0, 1], bounds=(-np.pi, np.pi))          # Gripper yaw
])

target = [0.15, 0.05, 0.10]  # meters (x, y, z)
pose = np.eye(4)
pose[:3, 3] = target

angles = arm_chain.inverse_kinematics(pose)
print("Computed joint angles (rad):", angles[1:])
```

_Map `angles` to PWM commands for your actual servos._

---

## 5. Calibration & Testing Tips

- **Zero the Joints**: Align all servos to a known zero position physically.
- **Incremental Testing**: Move one joint at a time during initial tests.
- **Workspace Mapping**: Visualize reachable coordinates to ensure safety.
- **Safety Margins**: Implement error thresholds and motion stops for safety.

---

## 6. Up‑to‑Date Resources & Further Reading

- **IkPy Documentation**: [https://ikpy.readthedocs.io/en/latest/](https://ikpy.readthedocs.io/en/latest/)


