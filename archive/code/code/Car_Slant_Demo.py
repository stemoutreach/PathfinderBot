#!/usr/bin/python3
# coding=utf8
import sys
import time
import signal
import mecanum as mecanum



chassis = mecanum.MecanumChassis()

start = True
#Process before turning off
def Stop(signum, frame):
    global start

    start = False
    print('turned off...')
    chassis.set_velocity(0,0,0)  # turn off all motors
    

signal.signal(signal.SIGINT, Stop)

if __name__ == '__main__':
    while start:
        chassis.set_velocity(50,45,0)
        time.sleep(1)
        chassis.set_velocity(50,315,0)
        time.sleep(1)
        chassis.set_velocity(50,225,0)
        time.sleep(1)
        chassis.set_velocity(50,135,0)
        time.sleep(1)
    chassis.set_velocity(0,0,0)  # turn off all motors
    print('turned off')

        
