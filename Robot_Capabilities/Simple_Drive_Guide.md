
# 🕹️ PathfinderBot Simple Drive Guide

This guide shows you how to control your PathfinderBot's motors using basic directional functions. These functions are defined in `SimpleDrive.py`.

---

## 🛠️ Prerequisites

- `SimpleDrive.py` and `Board.py` in the same directory
- PathfinderBot hardware powered and connected
- Python 3 environment on Raspberry Pi

---

## 🚗 Available Movement Functions

All functions use a `speed` value between `-100` and `100`.

### ✅ Forward

```python
Forward(speed)
```
Drives the robot forward.

---

### 🔁 Reverse

```python
Reverse(speed)
```
Drives the robot backward.

---

### 🔄 Turn Right

```python
TurnRight(speed)
```
Turns the robot to the right (spin in place).

---

### 🔃 Turn Left

```python
TurnLeft(speed)
```
Turns the robot to the left (spin in place).

---

### 👉 Strafe Right

```python
StrafeRight(speed)
```
Slides the robot to the right (requires mecanum wheels).

---

### 👈 Strafe Left

```python
StrafeLeft(speed)
```
Slides the robot to the left (requires mecanum wheels).

---

### 🛑 Stop All Motors

```python
MotorStop()
```
Stops all movement.

---

## 🧪 Example Test

```python
if __name__ == '__main__':
    Forward(40)
    time.sleep(1)
    MotorStop()
```

This example moves the robot forward for 1 second and then stops.

---

## ⚠️ Safety Tips

- Always call `MotorStop()` at the end of your script
- Avoid high speeds indoors
- Keep cables clear of wheels

---

## ✅ Summary Table

| Function        | Description               |
|----------------|---------------------------|
| `Forward(x)`    | Drive forward             |
| `Reverse(x)`    | Drive backward            |
| `TurnLeft(x)`   | Rotate left               |
| `TurnRight(x)`  | Rotate right              |
| `StrafeLeft(x)` | Slide left (mecanum)      |
| `StrafeRight(x)`| Slide right (mecanum)     |
| `MotorStop()`   | Stop all motors           |
