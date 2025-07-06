
# 🌈 PathfinderBot RGB Control Guide

This guide shows you how to control the onboard RGB LEDs connected through the `Board` module. You'll learn how to set colors, cycle through patterns, and cleanly shut off the lights.

---

## 🛠️ Prerequisites

- Python 3 installed on your Raspberry Pi
- `Board.py` and `RGBControlDemo.py` on your robot
- Onboard LEDs connected (2 RGB pixels)

---

## 📦 Module Reference

All RGB control is handled via:
```python
Board.RGB.setPixelColor(index, Board.PixelColor(r, g, b))
Board.RGB.show()
```

- `index`: 0 or 1 (there are two RGB pixels)
- `r`, `g`, `b`: Red, Green, Blue intensity (0–255)

---

## 🎨 RGBControlDemo Explained

The demo cycles colors on both RGB LEDs:

```python
# Turn off both LEDs
Board.RGB.setPixelColor(0, Board.PixelColor(0, 0, 0))
Board.RGB.setPixelColor(1, Board.PixelColor(0, 0, 0))
Board.RGB.show()

# Cycle through red, green, blue, yellow
Board.RGB.setPixelColor(0, Board.PixelColor(255, 0, 0))  # Red
Board.RGB.setPixelColor(1, Board.PixelColor(255, 0, 0))
Board.RGB.show()
time.sleep(1)
...
```

### 🛑 Safe Shutdown

A signal handler is included to turn off the lights when you press `CTRL+C`.

```python
import signal

def Stop(signum, frame):
    global start
    start = False
    print('closing ...')
```

---

## ✅ Customization Ideas

- Change the colors by modifying the RGB values
- Use `time.sleep(0.1)` for faster transitions
- Create your own loop to flash, blink, or chase

### Example: Flashing Red

```python
import time
import Board

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

## 🧼 Reset/Clear LEDs

To turn off all lights at any time:

```python
Board.RGB.setPixelColor(0, Board.PixelColor(0, 0, 0))
Board.RGB.setPixelColor(1, Board.PixelColor(0, 0, 0))
Board.RGB.show()
```

---

## ✅ Summary

| Action             | Code Example |
|--------------------|--------------|
| Set red color      | `Board.PixelColor(255, 0, 0)` |
| Show LED update    | `Board.RGB.show()` |
| Turn off LEDs      | RGB values `(0, 0, 0)` |

