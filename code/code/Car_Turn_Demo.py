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
    print('turning off...')
    chassis.set_velocity(0,0,0)  # Turn off all motors
    

signal.signal(signal.SIGINT, Stop)

if __name__ == '__main__':
    while start:
        chassis.set_velocity(0,90,0.25)# rotate clockwise
        time.sleep(5)
        chassis.set_velocity(0,90,-0.25)# rotate counterclockwise
        time.sleep(3)
    chassis.set_velocity(0,0,0)  # turn odd all motors
    print('turned off')

        
