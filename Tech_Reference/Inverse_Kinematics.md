# Inverse Kinematics

Inverse Kinematics (IK) answers the question: **“What joint angles do we need so the end‑effector (gripper) reaches a desired position and orientation?”**
For PathfinderBot’s 5‑Degree‑of‑Freedom (DOF) servo arm, IK lets your code move the gripper precisely to pick up blocks and interact with AprilTag targets.

---

## 1. Arm Layout & Joint Nomenclature

Assuming the standard HiWonder MasterPi / ArmPi Pro configuration:

| Joint # | Name                     | Axis & Type                      |
| ------- | ------------------------ | -------------------------------- |
| 1       | Base Yaw                 | Rotates arm around Z             |
| 2       | Shoulder Pitch           | Rotates in vertical plane        |
| 3       | Elbow Pitch              | Rotates in vertical plane        |
| 4       | Wrist Pitch              | Rotates in vertical plane        |


> **Note:** 5 DOF allows full XYZ positioning and a single rotational axis. Full 6‑DOF orientation (roll, pitch, yaw) is **not** possible—so specify only the gripper roll or allow limited orientation.

---

## 2. Forward vs. Inverse Kinematics

* **Forward Kinematics (FK)**: Given joint angles $\theta_1\dots\theta_5$ → compute end‑effector pose **T**. Generally solved using Denavit–Hartenberg (DH) parameters.
* **Inverse Kinematics (IK)**: Given desired pose **T** → compute $\theta$. Can be solved **analytically** (closed‑form) or **numerically** (iterative).

### Why IK Is Harder

For most real arms, multiple (or zero) solutions exist, and joint limits add constraints. A 5‑DOF arm may have redundant solutions in position but limited orientation freedom.

---

## 3. Workflow for PathfinderBot

1. **Model the Arm**

   * Measure link lengths (L1…L4), gripper length, and joint offsets.
   * Create DH table ($a_i, \alpha_i, d_i, \theta_i$).
2. **Implement FK** (verify with measured positions).
3. **Derive Analytical IK** (recommended for real‑time on Raspberry Pi):

   * **Base Angle ($\theta_1$)** from target **X,Y**: $\theta_1 = \"operatorname"{atan2}(y,x)$
   * **Planar 2‑link Solution** for Shoulder ($\theta_2$) and Elbow ($\theta_3$) using law of cosines in the vertical plane.
   * **Wrist Pitch ($\theta_4$)** ensures end‑effector points to target angle.
4. **Check Joint Limits** (clip or reject invalid solutions).
5. **Command Servos** with smooth interpolation (ease‑in/out ramps).

---

## 4. Example Python (PyPi `ikpy` Numeric Solver)

```python
from ikpy.chain import Chain
from ikpy.link import URDFLink
import numpy as np

# Define simplified 5‑DOF chain
arm_chain = Chain(name='5dof_arm', links=[
    URDFLink(rotation=[0, 0, 1], bounds=(-np.pi, np.pi)),   # Base
    URDFLink(length=0.06, rotation=[0, 1, 0], bounds=(-1.4, 1.4)), # Shoulder
    URDFLink(length=0.08, rotation=[0, 1, 0], bounds=(-1.4, 1.4)), # Elbow
    URDFLink(length=0.05, rotation=[0, 1, 0], bounds=(-1.4, 1.4)), # Wrist pitch
    URDFLink(rotation=[0, 0, 1], bounds=(-np.pi, np.pi))    # Gripper yaw
])

target = [0.15, 0.05, 0.10]  # meters (x, y, z)
pose = np.eye(4)
pose[:3, 3] = target          # only position, leave orientation default

angles = arm_chain.inverse_kinematics(pose)
print("Computed joint angles (rad):", angles[1:])
```

> Replace link lengths and limits with your measurements. Map `angles` to PWM values for each servo.

---

## 5. Calibration & Testing Tips

* **Zero the Joints**: Physically align servos to known zero positions.
* **Iterate Slowly**: Move one joint at a time during first tests.
* **Workspace Check**: Plot reachable positions to avoid commands outside range.
* **Add Safety Margins**: Stop motion if large error persists.

---

## 6. Resources & Further Reading

* **Modern Robotics Textbook (open access)** – Chapter 11 covers IK: [https://modernrobotics.northwestern.edu/book.html](https://modernrobotics.northwestern.edu/book.html)
* **IkPy Docs**: [https://ikpy.readthedocs.io/](https://ikpy.readthedocs.io/)
* **ROS MoveIt IK Tutorial**: [https://ros-planning.github.io/moveit\_tutorials/doc/ikfast\_tutorial/ikfast\_tutorial.html](https://ros-planning.github.io/moveit_tutorials/doc/ikfast_tutorial/ikfast_tutorial.html)
* **HiWonder ArmPi Sample Code** (demonstrates FK/IK): [https://github.com/Hiwonder-Tech/hiwonder\_armpi\_firmware](https://github.com/Hiwonder-Tech/hiwonder_armpi_firmware)
* **Lecture Video: 5‑DOF Arm IK Explained**: [https://www.youtube.com/watch?v=\_j1qN2Xqh40](https://www.youtube.com/watch?v=_j1qN2Xqh40)

---

Mastering IK lets PathfinderBot pick, place, and interact with objects accurately. Combine this guide with your AprilTags and Mecanum drive knowledge to create fully autonomous challenges!
