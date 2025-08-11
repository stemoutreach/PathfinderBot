# PathfinderBot – Troubleshooting Guide

This guide lists common issues encountered during the PathfinderBot workshop and provides quick fixes.  
Keep this open during the event for rapid reference.

---

## Quick Reference Table

| Issue | Symptom | Likely Cause | Fix Summary |
|-------|---------|--------------|-------------|
| Power cable in wrong port | Pi won’t power on | Cable in audio jack | Move to expansion board port, turn on switches |
| Servo wires reversed | Servos twitch/move wrong | Connector backward | White/yellow wire forward, reconnect |
| Motors wired wrong | Incorrect motor order | Wrong ports | Match wiring to diagram |
| Strafe not working | No sideways movement | Wheels installed wrong | Rollers form an “X” pattern |

---

## 1. Power Cable Plugged into Pi Audio Jack

**Symptoms:**
- Raspberry Pi does not power on.
- No lights or activity indicators.

**Cause:**
- Power cable is accidentally plugged into the **3.5mm audio jack** (near the USB ports) instead of the **expansion board power port**.

**Fix:**
1. Unplug the power cable from the audio jack.
2. Locate the robot’s **expansion board power port**.
3. Turn on **both** power switches.
4. Verify that the Pi’s **red power LED** is lit.

<img src="/zzimages/NotAudio.jpg" width="400">

---

## 2. Servo Wires Reversed

**Symptoms:**
- Servos don’t move, twitch randomly, or move incorrectly.
- Robot arm does not respond to commands.

**Cause:**
- Servo connector is plugged in backward on the servo driver board.

**Fix:**
1. Turn off the robot before touching wires.
2. Ensure the **white or yellow wire faces forward** (toward the front of the robot).
3. Reconnect the servo correctly.
4. Turn the robot back on and test movement.

<img src="/zzimages/ServoWires.jpg" width="400">  
<img src="/zzimages/WiringDiagram.jpg" width="600">

---

## 3. Motors Wired in the Wrong Order

**Symptoms:**
- Motor test results show incorrect movement order.
- Robot drives unpredictably.

**Cause:**
- Motors connected to the wrong ports.

**Fix:**
1. Turn off the robot.
2. Check motor connections against the diagram.
3. Reconnect as needed.
4. Turn the robot back on and retest.

<img src="/zzimages/MotorConnections.jpg" width="400">

---

## 4. Strafe Movement Not Working

**Symptoms:**
- Robot can’t strafe (sideways movement doesn’t work).

**Cause:**
- Mecanum wheels installed incorrectly.

**Fix:**
1. Turn off the robot.
2. Check wheel orientation – rollers should form an **“X” pattern** when viewed from above.

<img src="/zzimages/mecanumX.jpg" width="400">

---
