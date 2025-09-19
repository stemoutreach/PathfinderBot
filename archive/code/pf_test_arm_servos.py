#!/usr/bin/python3
# coding=utf8
import sys
import time
import Board as Board
from pf_start_robot import initialize_robot

def beep(numberofbeeps):
    for _ in range(numberofbeeps):
        Board.setBuzzer(1)   # Turn buzzer on
        time.sleep(0.1)      # Beep duration
        Board.setBuzzer(0)   # Turn buzzer off
        time.sleep(0.2)      # Pause between beeps

initialize_robot()

beep(1)  # Servo 1
Board.setPWMServoPulse(1, 1750, 300) 
time.sleep(0.3)
Board.setPWMServoPulse(1, 1500, 300) 
time.sleep(0.3)
Board.setPWMServoPulse(1, 1750, 300) 
time.sleep(0.3)
Board.setPWMServoPulse(1, 1500, 300) 
time.sleep(1.5)

beep(3)  # Servo 3
Board.setPWMServoPulse(3, 575, 300) 
time.sleep(0.3)
Board.setPWMServoPulse(3, 850, 300) 
time.sleep(0.3)
Board.setPWMServoPulse(3, 695, 300) 
time.sleep(1.5)

beep(4)  # Servo 4
Board.setPWMServoPulse(4, 2290, 300) 
time.sleep(0.3)
Board.setPWMServoPulse(4, 2550, 300) 
time.sleep(0.3)
Board.setPWMServoPulse(4, 2415, 300) 
time.sleep(1.5)

beep(5)  # Servo 5
Board.setPWMServoPulse(5, 620, 300) 
time.sleep(0.3)
Board.setPWMServoPulse(5, 930, 300) 
time.sleep(0.3)
Board.setPWMServoPulse(5, 780, 300) 
time.sleep(1.5)

beep(6)  # Servo 6
Board.setPWMServoPulse(6, 1250, 300) 
time.sleep(0.3)
Board.setPWMServoPulse(6, 1750, 300) 
time.sleep(0.3)
Board.setPWMServoPulse(6, 1500, 300) 
time.sleep(1.5)


