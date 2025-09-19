#!/usr/bin/python3
# coding=utf8
import sys
import time
import signal
import mecanum as mecanum



chassis = mecanum.MecanumChassis()

start = True
#Process before stopping 
def Stop(signum, frame):
    global start

    start = False
    print('closing...')
    chassis.set_velocity(0,0,0)  # close all motors 
    

signal.signal(signal.SIGINT, Stop)

if __name__ == '__main__':
    while start:
        chassis.set_velocity(50,180,0.3)
        time.sleep(3)
        chassis.set_velocity(50,0,-0.3)
        time.sleep(3)
    chassis.set_velocity(0,0,0)  # stop all motors
    print('turned off')

        
