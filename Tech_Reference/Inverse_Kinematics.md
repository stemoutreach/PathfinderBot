# Inverse Kinematics (PathfinderBot Arm)

Inverse Kinematics (IK) answers: **“What joint angles move the gripper to a desired position (and limited orientation)?”**  
For PathfinderBot’s 5‑DOF servo arm (MasterPi/ArmPi‑style), IK lets you place the gripper precisely to pick up blocks and interact with AprilTags.

---

## 1) Arm Layout & Joint Names

Assuming a typical HiWonder MasterPi / ArmPi Pro configuration:

| Joint # | Name           | Motion Axis / Type            |
|---------|----------------|-------------------------------|
| 1       | Base Yaw       | Rotation about Z              |
| 2       | Shoulder Pitch | Rotation in vertical plane    |
| 3       | Elbow Pitch    | Rotation in vertical plane    |
| 4       | Wrist Pitch    | Rotation in vertical plane    |

> **Note:** With 5‑DOF you can command **XYZ** and one orientation axis. Full 6‑DOF orientation (roll, pitch, yaw simultaneously) is not available.

---

## 2) FK vs. IK (quick refresher)

- **Forward kinematics (FK)**: joint angles → end‑effector pose (use DH parameters).
- **Inverse kinematics (IK)**: desired pose → joint angles. Can be **analytical** (closed form) or **numerical** (iterative). Multiple or no solutions may exist; joint limits and reachability matter.

---

## 3) Practical IK Workflow for PathfinderBot

1. **Measure & Model**
   - Measure link lengths (L1…L4), gripper length, offsets.
   - Build a DH table (`aᵢ, αᵢ, dᵢ, θᵢ`).

2. **Implement FK** and verify positions against real measurements.

3. **Solve IK**
   - Base yaw from target XY: `θ₁ = atan2(y, x)`.
   - Shoulder/elbow from a planar 2‑link law‑of‑cosines in the vertical plane.
   - Wrist pitch aligns the approach angle to the target.

4. **Validate constraints**
   - Clip to joint limits; reject unreachable poses.

5. **Command servos smoothly**
   - Use motion profiles (ease‑in/out) and rate limits to prevent overshoot.

---

## 4) Numeric IK in Python (IKPy example)

```python
# pip install ikpy numpy
from ikpy.chain import Chain
from ikpy.link import URDFLink
import numpy as np

arm = Chain(name="5dof_arm", links=[
    URDFLink(rotation=[0, 0, 1], bounds=(-np.pi, np.pi)),          # base
    URDFLink(length=0.06, rotation=[0, 1, 0], bounds=(-1.4, 1.4)), # shoulder
    URDFLink(length=0.08, rotation=[0, 1, 0], bounds=(-1.4, 1.4)), # elbow
    URDFLink(length=0.05, rotation=[0, 1, 0], bounds=(-1.4, 1.4)), # wrist pitch
    URDFLink(rotation=[0, 0, 1], bounds=(-np.pi, np.pi))           # gripper yaw (if used)
])

target_xyz = [0.15, 0.05, 0.10]  # meters: x, y, z
T = np.eye(4); T[:3, 3] = target_xyz

angles = arm.inverse_kinematics(T)  # radians, includes a dummy base element at index 0
print("Joint angles (rad):", angles[1:])
```

> Replace link lengths and bounds with your measurements. Map radians → PWM values for your servos.

---

## 5) Calibration & Safety

- **Zeroing:** Physically align servos to a known zero and store offsets.
- **Incremental moves:** Test one joint at a time at reduced speed.
- **Workspace check:** Avoid commanding poses outside reach (visualize or probe).
- **Watch torque/overcurrent:** Add current/time guards; stop on excessive error.

---

## 6) Verified Resources (working links)

- **Modern Robotics (textbook page): Inverse Kinematics of Open Chains** — concise chapter overview.  
  https://modernrobotics.northwestern.edu/nu-gm-book-resource/inverse-kinematics-of-open-chains/

- **Modern Robotics (full preprint PDF)** — canonical reference used in many courses.  
  https://hades.mech.northwestern.edu/images/2/25/MR-v2.pdf

- **IKPy Documentation (Read the Docs)** — API and usage for Python IK.  
  https://ikpy.readthedocs.io/

- **IKPy GitHub repository** — source code, issues, examples.  
  https://github.com/Phylliade/ikpy

- **MoveIt IKFast Tutorial (PickNik docs)** — how analytic IK is integrated in MoveIt.  
  https://moveit.picknik.ai/main/doc/examples/ikfast/ikfast_tutorial.html

- **MoveIt Tutorials (index)** — motion planning + kinematics across ROS releases.  
  https://moveit.github.io/moveit_tutorials/

- **Robotics Toolbox for Python: Inverse Kinematics** (Peter Corke) — solid numerical IK alternatives and theory notes.  
  https://petercorke.github.io/robotics-toolbox-python/IK/ik.html

- **HiWonder ArmPi Pro Official Docs** — assembly, usage, and references for the platform.  
  https://docs.hiwonder.com/projects/ArmPi_Pro/en/latest/
