#!/usr/bin/python
# coding=utf8
import time
import Board as Board

def beep(numberofbeeps):
    for _ in range(numberofbeeps):
        Board.setBuzzer(1)   # Turn buzzer on
        time.sleep(0.1)      # Beep duration
        Board.setBuzzer(0)   # Turn buzzer off
        time.sleep(0.3)      # Pause between beeps

beep(1)  # Servo 1
Board.setMotor(1, 45)
time.sleep(0.5)
Board.setMotor(1, 0)
time.sleep(1)
        
beep(2)  # Servo 2
Board.setMotor(2, 45)
time.sleep(0.5)
Board.setMotor(2, 0)
time.sleep(1)

beep(3)  # Servo 3
Board.setMotor(3, 45)
time.sleep(0.5)
Board.setMotor(3, 0)
time.sleep(1)

beep(4)  # Servo 4
Board.setMotor(4, 45)
time.sleep(0.5)
Board.setMotor(4, 0)
time.sleep(1)
