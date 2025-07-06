
# 🕹️ PathfinderBot Simple Drive Guide

This guide shows you how to control your PathfinderBot's motors using basic directional functions. 

---

## 🛠️ Prerequisites

- `Board.py` in the same directory
- PathfinderBot hardware powered and connected

---

## 🚗 Available Movement Functions

All functions use a `speed` value between `0` and `100`.

### ✅ Forward

```python
def Forward(speed):
    Board.setMotor(1, speed) 
    Board.setMotor(2, speed)
    Board.setMotor(3, speed)
    Board.setMotor(4, speed)
```
Drives the robot forward.

---

### 🔁 Reverse

```python
def Reverse(speed):
    Board.setMotor(1, -speed) 
    Board.setMotor(2, -speed)
    Board.setMotor(3, -speed)
    Board.setMotor(4, -speed)
```
Drives the robot backward.

---

### 🔄 Turn Right

```python
def TurnRight(speed):
    Board.setMotor(1, speed) 
    Board.setMotor(2, -speed)
    Board.setMotor(3, speed)
    Board.setMotor(4, -speed)
```
Turns the robot to the right (spin in place).

---

### 🔃 Turn Left

```python
def TurnLeft(speed):
    Board.setMotor(1, -speed) 
    Board.setMotor(2, speed)
    Board.setMotor(3, -speed)
    Board.setMotor(4, speed)
```
Turns the robot to the left (spin in place).

---

### 👉 Strafe Right

```python
def StrafeRight(speed):
    Board.setMotor(1, speed) 
    Board.setMotor(2, -speed)
    Board.setMotor(3, -speed)
    Board.setMotor(4, speed)
```
Slides the robot to the right (requires mecanum wheels).

---

### 👈 Strafe Left

```python
def StrafeLeft(speed):
    Board.setMotor(1, -speed) 
    Board.setMotor(2, speed)
    Board.setMotor(3, speed)
    Board.setMotor(4, -speed)
```
Slides the robot to the left (requires mecanum wheels).

---

### 🛑 Stop All Motors

```python
def MotorStop(): # stop all motors 
    Board.setMotor(1, 0) 
    Board.setMotor(2, 0)
    Board.setMotor(3, 0)
    Board.setMotor(4, 0)
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
