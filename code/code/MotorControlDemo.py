#!/usr/bin/python3
# coding=utf8
import sys
import time
import signal
import threading
import Board as Board

i
# stop all motors 
def MotorStop():
    Board.setMotor(1, 0) 
    Board.setMotor(2, 0)
    Board.setMotor(3, 0)
    Board.setMotor(4, 0)

start = True
#Process before stopping 
def Stop(signum, frame):
    global start

    start = False
    print('closing...')
    MotorStop()  # stop all motors
    

signal.signal(signal.SIGINT, Stop)

if __name__ == '__main__':
    
    while True:
        Board.setMotor(1, 35)  #Set No.1 motor at the speed of 35
        time.sleep(1)
        Board.setMotor(1, 60)  #60 Set No.1 motor at the speed of 60
        time.sleep(2)
        Board.setMotor(1, 90)  #90 Set No.1 motor at the speed of 90
        time.sleep(3)     
        
        if not start:
            MotorStop()  # stop all motors
            print('closed')
            break
    
    
        