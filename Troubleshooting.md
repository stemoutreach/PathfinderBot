# PathfinderBot Troubleshooting Guide

This guide lists common issues encountered during the PathfinderBot workshop and how to quickly resolve them.  
Keep this open during the event for quick reference.

---

## 1. Power Cable Plugged into Pi Audio interface

**Symptoms:**
- Raspberry Pi will not power on.
- No activity lights on the Pi.
  
**Cause:**
Power cable is plugged into the 3.5mm audio interface (near the USB ports) instead of the robots expantion board power port.

**Solution:**
1. Unplug the power cable from the audio interface.
2. Locate the robots expantion board power port.
3. Make sure both power switches are on.
4. Check that the red power LED lights up on the Pi.
  
   <img src="/zzimages/NotAudio.jpg" width="400" > 
     
---


## 2. Servo Wires Reversed

**Symptoms:**
- Servos do not move, twitch randomly, or move in unexpected directions.
- Robot arm may not respond to commands.

**Cause:**
- Servo connector is plugged in backward on the servo driver board.

**Solution:**
1. Power off the robot before adjusting any wires.
2. Check the servo connectors — **the white or yellow wire must face forward** on the robot.
3. Reconnect the servo in the correct orientation.
4. Power the robot back on and test servo movement.

   <img src="/zzimages/ServoWires.jpg" width="400" >
   
   <img src="/zzimages/WiringDiagram.jpg" width="600" > 
---

## 3. Motor Test is not in the correct order - wires may be incorrect

**Symptoms:**
- Motors test show wrong order.
- Robot may not respond to commands correctly.

**Cause:**
- Motors plugged in wrong order.

**Solution:**
1. Power off the robot before adjusting any wires.
2. Check the motor connectors — see image below.
4. Power the robot back on and test motor movement.

   <img src="/zzimages/MotorConnections.jpg" width="400" >

---
## 4. Strafe not working

**Symptoms:**

- Strafe does not work.
  
**Cause:**
Wheels installed incorrectly

**Solution:**
1. Power off the robot before adjusting any wires.
2. Check wheels - the rollers should form an X looking down on the robot. 
   

   <img src="/zzimages/mecanumX.jpg" width="400" >

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




