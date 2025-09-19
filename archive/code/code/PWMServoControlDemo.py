#!/usr/bin/python3
# coding=utf8
import sys
import time
import signal
import threading
import Board as Board

i

start = True
#Process before stopping 
def Stop(signum, frame):
    global start

    start = False
    print('...')

signal.signal(signal.SIGINT, Stop)

if __name__ == '__main__':
    
    while True:
        Board.setPWMServoPulse(1, 1500, 1000) # set the pulse width of No.1 servo as 1500 and the running time as 1000ms
        time.sleep(1)
        Board.setPWMServoPulse(1, 2500, 1000) # set the pulse width of No.1 servo as 2500 and the running time as 1000ms
        time.sleep(1)
        
        if not start:
            Board.setPWMServoPulse(1, 1500, 1000) # set the pulse width of No.1 servo as 1500 and the running time as 1000ms
            time.sleep(1)
            print('closed')
            break
    
    
        