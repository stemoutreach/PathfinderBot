#!/usr/bin/python3
# coding=utf8
import sys
import time
import Board as Board


Board.setPWMServoPulse(1, 1650, 300) 
time.sleep(0.3)
Board.setPWMServoPulse(1, 1500, 300) 
time.sleep(0.3)
Board.setPWMServoPulse(1, 1650, 300) 
time.sleep(0.3)
Board.setPWMServoPulse(1, 1500, 300) 
time.sleep(1.5)

Board.setPWMServoPulse(3, 645, 300) 
time.sleep(0.3)
Board.setPWMServoPulse(3, 745, 300) 
time.sleep(0.3)
Board.setPWMServoPulse(3, 695, 300) 
time.sleep(1.5)

Board.setPWMServoPulse(4, 2365, 300) 
time.sleep(0.3)
Board.setPWMServoPulse(4, 2465, 300) 
time.sleep(0.3)
Board.setPWMServoPulse(4, 2415, 300) 
time.sleep(1.5)

Board.setPWMServoPulse(5, 730, 300) 
time.sleep(0.3)
Board.setPWMServoPulse(5, 830, 300) 
time.sleep(0.3)
Board.setPWMServoPulse(5, 780, 300) 
time.sleep(1.5)

Board.setPWMServoPulse(6, 1450, 300) 
time.sleep(0.3)
Board.setPWMServoPulse(6, 1550, 300) 
time.sleep(0.3)
Board.setPWMServoPulse(6, 1500, 300) 
time.sleep(1.5)

Board.setMotor(1, 45)
time.sleep(0.5)
Board.setMotor(1, 0)
time.sleep(1)
        
Board.setMotor(2, 45)
time.sleep(0.5)
Board.setMotor(2, 0)
time.sleep(1)

Board.setMotor(3, 45)
time.sleep(0.5)
Board.setMotor(3, 0)
time.sleep(1)

Board.setMotor(4, 45)
time.sleep(0.5)
Board.setMotor(4, 0)
time.sleep(1)
