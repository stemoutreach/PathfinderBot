
# 🤖 PathfinderBot Buzzer + RGB Control Guide

This guide combines control of the **buzzer** and **RGB LEDs** using the `Board` module. You’ll learn how to create sounds, light effects, and synchronized patterns.

---

## 🛠️ Prerequisites

- Python 3 installed on your Raspberry Pi
- `Board.py`, `BuzzerControlDemo.py`, and `RGBControlDemo.py` available
- Buzzer connected to GPIO pin 31 (configured in code)
- 2 onboard RGB LEDs connected

---

## 🔊 Buzzer Control

### 📦 Function

```python
Board.setBuzzer(state)
```

- `state`: `1` = ON, `0` = OFF

### 🔁 Buzzer Demo Example

```python
import time
import Board

Board.setBuzzer(0)  # Ensure OFF
Board.setBuzzer(1)  # Turn ON
time.sleep(0.1)     # Short beep
Board.setBuzzer(0)  # Turn OFF

time.sleep(1)

Board.setBuzzer(1)  # Longer beep
time.sleep(0.5)
Board.setBuzzer(0)
```

### Morse Code Example (S = dot-dot-dot)

```python
for _ in range(3):
    Board.setBuzzer(1)
    time.sleep(0.2)
    Board.setBuzzer(0)
    time.sleep(0.2)
```

---

## 🌈 RGB LED Control

### 📦 Functions

```python
Board.RGB.setPixelColor(index, Board.PixelColor(r, g, b))
Board.RGB.show()
```

- `index`: 0 or 1
- `r, g, b`: Values 0–255

### 🎨 RGB Demo Example

```python
# Turn off LEDs
Board.RGB.setPixelColor(0, Board.PixelColor(0, 0, 0))
Board.RGB.setPixelColor(1, Board.PixelColor(0, 0, 0))
Board.RGB.show()

# Set to red
Board.RGB.setPixelColor(0, Board.PixelColor(255, 0, 0))
Board.RGB.setPixelColor(1, Board.PixelColor(255, 0, 0))
Board.RGB.show()
time.sleep(1)
```

### Flashing Red Pattern

```python
while True:
    Board.RGB.setPixelColor(0, Board.PixelColor(255, 0, 0))
    Board.RGB.setPixelColor(1, Board.PixelColor(255, 0, 0))
    Board.RGB.show()
    time.sleep(0.5)

    Board.RGB.setPixelColor(0, Board.PixelColor(0, 0, 0))
    Board.RGB.setPixelColor(1, Board.PixelColor(0, 0, 0))
    Board.RGB.show()
    time.sleep(0.5)
```

---

## 🧼 Safe Shutdown

```python
Board.setBuzzer(0)

Board.RGB.setPixelColor(0, Board.PixelColor(0, 0, 0))
Board.RGB.setPixelColor(1, Board.PixelColor(0, 0, 0))
Board.RGB.show()
```

Use a signal handler to automatically shut off when interrupted:

```python
import signal

def Stop(signum, frame):
    global start
    start = False
    Board.setBuzzer(0)
    # Turn off lights
```

---

## ✅ Quick Summary

| Action           | Code                            |
|------------------|---------------------------------|
| Buzzer ON        | `Board.setBuzzer(1)`            |
| Buzzer OFF       | `Board.setBuzzer(0)`            |
| RGB Color Red    | `Board.PixelColor(255, 0, 0)`   |
| Show LED Update  | `Board.RGB.show()`              |
| Turn off LEDs    | Set RGB values to `(0, 0, 0)`   |

Bring your PathfinderBot to life with sound + light!

