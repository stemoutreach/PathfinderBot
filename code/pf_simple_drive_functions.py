import time
import Board as Board

def MotorStop(): # stop all motors 
    Board.setMotor(1, 0) 
    Board.setMotor(2, 0)
    Board.setMotor(3, 0)
    Board.setMotor(4, 0)

def Forward(speed):
    Board.setMotor(1, speed) 
    Board.setMotor(2, speed)
    Board.setMotor(3, speed)
    Board.setMotor(4, speed)

def Reverse(speed):
    Board.setMotor(1, -speed) 
    Board.setMotor(2, -speed)
    Board.setMotor(3, -speed)
    Board.setMotor(4, -speed)

def TurnRight(speed):
    Board.setMotor(1, speed) 
    Board.setMotor(2, -speed)
    Board.setMotor(3, speed)
    Board.setMotor(4, -speed)

def TurnLeft(speed):
    Board.setMotor(1, -speed) 
    Board.setMotor(2, speed)
    Board.setMotor(3, -speed)
    Board.setMotor(4, speed)

def StrafeRight(speed):
    Board.setMotor(1, speed) 
    Board.setMotor(2, -speed)
    Board.setMotor(3, -speed)
    Board.setMotor(4, speed)

def StrafeLeft(speed):
    Board.setMotor(1, -speed) 
    Board.setMotor(2, speed)
    Board.setMotor(3, speed)
    Board.setMotor(4, -speed)

if __name__ == '__main__':
    Forward(40)
    time.sleep(1)
    MotorStop()
    Reverse(40)
    time.sleep(1)
    MotorStop()
    StrafeRight(40)
    time.sleep(1)
    MotorStop()
    StrafeLeft(40)
    time.sleep(1)
    MotorStop()
    TurnRight(40)
    time.sleep(1)
    MotorStop()
    TurnLeft(40)
    time.sleep(1)
    MotorStop()
    
