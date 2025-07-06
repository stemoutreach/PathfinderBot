
# 🔊 PathfinderBot Buzzer Control Guide

This guide explains how to use the onboard buzzer using the `Board` module. You’ll learn how to make sounds, add delays, and create simple patterns.

---

## 🛠️ Prerequisites

- Python 3 installed on your Raspberry Pi
- `Board.py` and `BuzzerControlDemo.py` available
- Buzzer connected to GPIO pin 31 (configured in code)

---

## 📦 Module Function

```python
Board.setBuzzer(state)
```

- `state`: `1` to turn the buzzer ON, `0` to turn it OFF

---

## 🔁 BuzzerControlDemo Explained

The demo toggles the buzzer ON and OFF with delays:

```python
import time
import Board

Board.setBuzzer(0)  # Make sure buzzer starts OFF

Board.setBuzzer(1)  # Turn ON
time.sleep(0.1)     # Short beep
Board.setBuzzer(0)  # Turn OFF

time.sleep(1)       # Wait 1 second

Board.setBuzzer(1)  # Longer beep
time.sleep(0.5)
Board.setBuzzer(0)
```

---

## 🔔 Custom Patterns

### Example: Morse Code S (dot-dot-dot)

```python
import time
import Board

for _ in range(3):
    Board.setBuzzer(1)
    time.sleep(0.2)
    Board.setBuzzer(0)
    time.sleep(0.2)
```

---

## ❌ Turn Off Buzzer

Always turn off the buzzer when finished:

```python
Board.setBuzzer(0)
```

---

## ✅ Summary

| Action          | Code                    |
|------------------|-------------------------|
| Buzzer ON        | `Board.setBuzzer(1)`    |
| Buzzer OFF       | `Board.setBuzzer(0)`    |
| Delay            | `time.sleep(seconds)`   |

Use this to signal actions, alerts, or just for fun!

