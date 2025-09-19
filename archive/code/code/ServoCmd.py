import sys
import threading
import ActionGroupControl as AGC

def setServoPulse(id, pulse, use_time):
    setPWMServoPulse(id, pulse, use_time)

def setServoDeviation(id ,dev):
    setPWMServoDeviation(id, dev)

def runActionGroup(num):
    runAct = threading.Thread(target=AGC.runAction, args=(num, ))
    runAct.start()

def stopActionGroup():
    AGC.stop_action_group()

