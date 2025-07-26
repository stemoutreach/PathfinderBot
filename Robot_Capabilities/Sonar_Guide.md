
# 🧭 Sonar Guide: Using the Sonar and RGB LEDs

This guide will help you learn how to:
- 📏 Read distances using the ultrasonic sonar sensor.
- 💡 Control the RGB LEDs (2 on the sonar sensor).
- 🎨 Add effects like solid colors or breathing animations.

---

## 🛠️ Prerequisites

- Always run code from cd /home/robot/code
- PathfinderBot hardware powered and connected
- Robot is on the floor and able to move

---
## Run sample code [pf_sonar_nav.py](/code/pf_sonar_nav.py) from the Raspberry Pi 500

1. **SSH Connection**

    Open a terminal and enter the following command replacing the XXX.XXX.XXX.XXX with the robot's IP
    - NOTE: user = robot
    ~~~
    ssh robot@XXX.XXX.XXX.XXX
    ~~~

1. **Run pf_sonar_nav.py script**
  
   This script runs through driving forward undil blocked, then turns etc...
   ~~~
   cd /home/robot/code
   sudo python pf_sonar_nav.py
   ~~~


1. **Try pf_sonar_led_nav.py script**
  
   This script is same as above but adds color to the sonar...
   ~~~
   cd /home/robot/code
   sudo python pf_sonar_led_nav.py
   ~~~
---


## 1. 📏 Getting Distance from Sonar

The sonar sensor returns the distance to the nearest object (up to 5 meters).

### Example: Read and print distance

```python
from Sonar import Sonar
import time

sonar = Sonar()

while True:
    distance = sonar.getDistance()
    print(f"Distance: {distance} mm")
    time.sleep(1)
```

---

## 2. 💡 Controlling the RGB LEDs

There are two RGB LEDs (index 0 and 1). You can set colors using RGB values.

### Example: Set both LEDs to red

```python
import Board
from Sonar import Sonar
import time

sonar = Sonar()
sonar.setRGBMode(0)  # Solid color mode
sonar.setPixelColor(0, Board.PixelColor(255, 0, 0))  # LED 0 - Red
sonar.setPixelColor(1, Board.PixelColor(255, 0, 0))  # LED 1 - Red
sonar.show()
```

---

## 3. 🎨 Change LED Colors Based on Distance

Light up green when safe, red when something is close!

```python
import Board
from Sonar import Sonar
import time

sonar = Sonar()
sonar.setRGBMode(0)  # Solid color mode

while True:
    dist = sonar.getDistance()
    print(f"Distance: {dist} mm")

    if dist < 200:
        # Close = Red
        color = Board.PixelColor(255, 0, 0)
    else:
        # Far = Green
        color = Board.PixelColor(0, 255, 0)

    sonar.setPixelColor(0, color)
    sonar.setPixelColor(1, color)
    sonar.show()

    time.sleep(0.5)
```

---

## 4. 🌈 Breathing LED Effect (Pulsing)

Use the "symphony" mode to create a breathing/pulsing effect on both LEDs.

```python
from Sonar import Sonar

sonar = Sonar()
sonar.startSymphony()  # Activates built-in breathing cycle
```

---

## 5. 💡 Custom Breathing Color and Speed

Control the breathing speed of R, G, or B channels individually.

```python
from Sonar import Sonar

sonar = Sonar()
sonar.setRGBMode(1)  # Breathing mode

# index: 0 or 1 (LED)
# rgb: 0 (R), 1 (G), 2 (B)
# cycle: milliseconds (higher = slower pulse)

sonar.setBreathCycle(0, 0, 3000)  # LED 0, Red, 3-second pulse
sonar.setBreathCycle(0, 1, 1000)  # LED 0, Green, 1-second pulse
sonar.setBreathCycle(0, 2, 2000)  # LED 0, Blue, 2-second pulse
```

---

## ✅ Summary

| Feature                | Function                      |
|------------------------|-------------------------------|
| Get distance           | `getDistance()`               |
| Set LED color          | `setPixelColor(index, rgb)`   |
| Show color             | `show()`                      |
| Breathing effect       | `setBreathCycle()`            |
| Start symphony         | `startSymphony()`             |
