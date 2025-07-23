#!/usr/bin/python3
# coding=utf8

import time
import Sonar as Sonar
import Board as Board
from Transform import *
from ArmMoveIK import *
import mecanum as mecanum


def initialize_robot():

    servo1 = 1500

    HWSONAR = Sonar.Sonar()
    AK = ArmIK()
    chassis = mecanum.MecanumChassis()

    # Turn off onboard LEDs
    HWSONAR.setRGBMode(0)
    HWSONAR.setPixelColor(0, Board.PixelColor(0, 0, 0))
    HWSONAR.setPixelColor(1, Board.PixelColor(0, 0, 0))
    HWSONAR.show()

    # Stop robot movement
    chassis.set_velocity(0, 0, 0)

    # Move arm to forward-facing position
    Board.setPWMServoPulse(1, servo1, 300)
    AK.setPitchRangeMoving((0, 6, 18), 0, -90, 90, 1500)

    # Beep to indicate startup complete
    Board.setBuzzer(0)
    Board.setBuzzer(1)
    time.sleep(0.1)
    Board.setBuzzer(0)
