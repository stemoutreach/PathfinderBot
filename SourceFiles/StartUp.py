#!/usr/bin/python3
# coding=utf8
import sys
sys.path.append('/home/pi/MasterPi')
import time
import HiwonderSDK.Sonar as Sonar
import HiwonderSDK.Board as Board
from ArmIK.Transform import *
from ArmIK.ArmMoveIK import *
import HiwonderSDK.mecanum as mecanum


# The closing angle of gripper when gripping
servo1 = 1500

HWSONAR = Sonar.Sonar() #ultrasonic sensor 
AK = ArmIK()
chassis = mecanum.MecanumChassis()

HWSONAR.setRGBMode(0)
HWSONAR.setPixelColor(0, Board.PixelColor(0,0,0))
HWSONAR.setPixelColor(1, Board.PixelColor(0,0,0))    
HWSONAR.show()
    
chassis.set_velocity(0,0,0)
Board.setPWMServoPulse(1, servo1, 300)
AK.setPitchRangeMoving((0, 6, 18), 0,-90, 90, 1500)

Board.setBuzzer(0)
Board.setBuzzer(1)
time.sleep(.1)
Board.setBuzzer(0)
    

      
