import time
import Board
import signal



start = True
#Process before stopping 
def Stop(signum, frame):
    global start

    start = False
    print('closing ...')

#Turn off all lights first
Board.RGB.setPixelColor(0, Board.PixelColor(0, 0, 0))
Board.RGB.setPixelColor(1, Board.PixelColor(0, 0, 0))
Board.RGB.show()

signal.signal(signal.SIGINT, Stop)

while True:
    #set two lights to red
    Board.RGB.setPixelColor(0, Board.PixelColor(255, 0, 0))
    Board.RGB.setPixelColor(1, Board.PixelColor(255, 0, 0))
    Board.RGB.show()
    time.sleep(1)
    
    #set two lights to green 
    Board.RGB.setPixelColor(0, Board.PixelColor(0, 255, 0))
    Board.RGB.setPixelColor(1, Board.PixelColor(0, 255, 0))
    Board.RGB.show()
    time.sleep(1)
    
    #set two lights to blue
    Board.RGB.setPixelColor(0, Board.PixelColor(0, 0, 255))
    Board.RGB.setPixelColor(1, Board.PixelColor(0, 0, 255))
    Board.RGB.show()
    time.sleep(1)
    
    #set two lights to yellow
    Board.RGB.setPixelColor(0, Board.PixelColor(255, 255, 0))
    Board.RGB.setPixelColor(1, Board.PixelColor(255, 255, 0))
    Board.RGB.show()
    time.sleep(1)

    if not start:
        #turn off all lights 
        Board.RGB.setPixelColor(0, Board.PixelColor(0, 0, 0))
        Board.RGB.setPixelColor(1, Board.PixelColor(0, 0, 0))
        Board.RGB.show()
        print('turned off')
        break
