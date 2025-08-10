# PathfinderBot Troubleshooting Guide

This guide lists common issues encountered during the PathfinderBot workshop and how to quickly resolve them.  
Keep this open during the event for quick reference.

---

## 1. Power Cable Plugged into Pi Audio Jack

**Symptoms:**
- Raspberry Pi will not power on.
- No activity lights on the Pi.
- Power cable is plugged into the 3.5mm audio jack (near the HDMI ports) instead of the USB-C power port.

**Cause:**
- Mistakenly plugging the USB-C cable into the wrong port due to similar placement.

**Solution:**
1. Unplug the power cable from the audio jack.
2. Locate the **USB-C power port** (on the opposite side from the GPIO pins, next to the HDMI ports).
3. Plug the USB-C power cable into the correct port.
4. Check that the red power LED lights up on the Pi.

**Prevention Tip:**
- Apply a small label or colored tape near the correct power port before the event.

**Image:**  
![Correct Pi Power Port](images/correct_power_port.jpg)

---

## 2. Servo Wires Reversed

**Symptoms:**
- Servos do not move, twitch randomly, or move in unexpected directions.
- Robot arm may not respond to commands.

**Cause:**
- Servo connector is plugged in backward on the servo driver board.

**Solution:**
1. Power off the robot before adjusting any wires.
2. Check the servo connectors — **the brown or black wire must face the GND pin** on the board.
3. Reconnect the servo in the correct orientation.
4. Power the robot back on and test servo movement.

**Prevention Tip:**
- Train the build team to identify wire colors before plugging in.
- Mark the GND side of each servo port with a small dot of colored tape.

**Image:**  
![Correct Servo Wiring](images/correct_servo_wiring.jpg)

---

## 3. (Add More Issues Here)

**Format for New Issues:**
- **Symptoms:**  
- **Cause:**  
- **Solution:**  
- **Prevention Tip:**  
- **Image:**  

---

## Quick Reference Diagram

![PathfinderBot Wiring Diagram](images/wiring_diagram.jpg)

---

**Last Updated:** YYYY-MM-DD
