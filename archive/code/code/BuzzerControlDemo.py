import time
import Board



Board.setBuzzer(0) # close 

Board.setBuzzer(1) # open
time.sleep(0.1) # delay
Board.setBuzzer(0) #close 

time.sleep(1) # delay

Board.setBuzzer(1)
time.sleep(0.5)
Board.setBuzzer(0)