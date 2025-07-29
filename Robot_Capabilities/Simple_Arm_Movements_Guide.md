
# 🤖 Simple Arm Movements Guide

This guide explains how to use the `Board.setPWMServoPulse()` function to control the robot arm. Each servo is identified by an ID from 1 to 6, and you can control the position and speed using pulse-width modulation (PWM).

## 🛠️ Prerequisites

- Always run code from cd /home/robot/code
- PathfinderBot hardware powered and connected
- Robot is on the floor and able to move

---
## Run sample code [pf_simple_arm_movements.py](/code/pf_simple_arm_movements.py) from the Raspberry Pi 500

1. **SSH Connection**

    Open a terminal and enter the following command replacing the XXX.XXX.XXX.XXX with the robot's IP
    - NOTE: user = robot
    ~~~
    ssh robot@XXX.XXX.XXX.XXX
    ~~~

1. **Run start up script**
  
   This script runs through arm movements to pickup a block and place it on the back of the robot
   ~~~
   cd /home/robot/code
   sudo python pf_simple_arm_movements.py
   ~~~

---

## 🛠️ Function Format

```python
Board.setPWMServoPulse(servo_id, pulse, use_time)
```

- `servo_id`: Servo number (1–6)
- `pulse`: Position (typically between 500 and 2500)
- `use_time`: Time in milliseconds to move

---

## 📸 Example: Point Camera Forward and Down

This positions the arm so the camera looks forward and slightly downward:

```python
Board.setPWMServoPulse(1, 1500, 500)
Board.setPWMServoPulse(3, 500, 1000)
Board.setPWMServoPulse(4, 2500, 1000)
Board.setPWMServoPulse(5, 1000, 1000)
Board.setPWMServoPulse(6, 1500, 1000)
```

---

## 🔧 Example: Test Each Servo

Each servo is moved back and forth to verify motion and range:

```python
# Test Servo 1
Board.setPWMServoPulse(1, 1650, 300)
time.sleep(0.3)
Board.setPWMServoPulse(1, 1500, 300)
time.sleep(0.3)
Board.setPWMServoPulse(1, 1650, 300)
time.sleep(0.3)
Board.setPWMServoPulse(1, 1500, 300)
time.sleep(1.5)

# Test Servo 3
Board.setPWMServoPulse(3, 645, 300)
time.sleep(0.3)
Board.setPWMServoPulse(3, 745, 300)
time.sleep(0.3)
Board.setPWMServoPulse(3, 695, 300)
time.sleep(1.5)

# Test Servo 4
Board.setPWMServoPulse(4, 2365, 300)
time.sleep(0.3)
Board.setPWMServoPulse(4, 2465, 300)
time.sleep(0.3)
Board.setPWMServoPulse(4, 2415, 300)
time.sleep(1.5)

# Test Servo 5
Board.setPWMServoPulse(5, 730, 300)
time.sleep(0.3)
Board.setPWMServoPulse(5, 830, 300)
time.sleep(0.3)
Board.setPWMServoPulse(5, 780, 300)
time.sleep(1.5)

# Test Servo 6
Board.setPWMServoPulse(6, 1450, 300)
time.sleep(0.3)
Board.setPWMServoPulse(6, 1550, 300)
time.sleep(0.3)
Board.setPWMServoPulse(6, 1500, 300)
time.sleep(1.5)
```

---

## ⚠️ Tips

- Always start from a known safe position before testing.
- Avoid going below 500 or above 2500 unless the hardware supports it.
- Use `time.sleep()` to allow the movement to finish before sending the next command.

---

## ✅ Summary Table

| Servo ID | Typical Function |
|----------|------------------|
| 1        | Base rotation    |
| 3        | Shoulder         |
| 4        | Elbow            |
| 5        | Wrist            |
| 6        | Gripper |


[UI for ARM movements](Arm_Guide.md)   
<img src="/zzimages/ArmAction.png" width="300" >   

---
[Return to Robot Capabilities page](README.md)

[Return to PathfinderBot Workshop page](/README.md)



