#!/usr/bin/python3
# coding=utf8
import sys
import os
import cv2
import time
import queue
import Camera
import logging
import threading
import MjpgServer
import numpy as np
import Sonar as Sonar
import Board as Board

HWSONAR = Sonar.Sonar() #ultrasonic sensor 

def setBuzzer(timer):
    Board.setBuzzer(0)
    Board.setBuzzer(1)
    time.sleep(timer)
    Board.setBuzzer(0)
    
voltage = 0.0

def voltageDetection():
    global voltage
    vi = 0
    dat = []
    previous_time = 0.00
    try:
        while True:
            if time.time() >= previous_time + 1.00 :
                previous_time = time.time()
                volt = Board.getBattery()/1000.0
                
                if 5.0 < volt  < 8.5:
                    dat.insert(vi, volt)
                    vi = vi + 1            
                if vi >= 3:
                    vi = 0
                    volt1 = dat[0]
                    volt2 = dat[1]
                    volt3 = dat[2]
                    voltage = (volt1+volt2+volt3)/3.0 
                    print('Voltage:','%0.2f' % voltage)
            else:
                time.sleep(0.01)
            
    except Exception as e:
        print('Error', e)
            
        
# un subthread
VD = threading.Thread(target=voltageDetection)
VD.setDaemon(True)
VD.start()


def startTruckPi():
    global HWEXT, HWSONIC
    global voltage
    
    previous_time = 0.00
    # After turning on the ultrosonic sensor, the light is turned off by defualt
    HWSONAR.setRGBMode(0)
    HWSONAR.setPixelColor(0, Board.PixelColor(0,0,0))
    HWSONAR.setPixelColor(1, Board.PixelColor(0,0,0))    
    HWSONAR.show()
    
 
    threading.Thread(target=MjpgServer.startMjpgServer,
                     daemon=True).start()  # streaming server

    
    loading_picture = cv2.imread('loading.jpg')
    cam = Camera.Camera()  # camera reading 
    cam.camera_open()

    while True:
        time.sleep(0.03)
        # execute game program:
        try:
            if cam.frame is not None:
                frame = cam.frame.copy()
                if voltage <= 7.2: 
                    MjpgServer.img_show = cv2.putText(frame, "Voltage:%.1fV"%voltage, (420, 460), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0,0,255), 2)
                else:
                    MjpgServer.img_show = cv2.putText(frame, "Voltage:%.1fV"%voltage, (420, 460), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0,255,0), 2)
            else:
                MjpgServer.img_show = loading_picture
        except KeyboardInterrupt:
            break

if __name__ == '__main__':
    # logging.basicConfig(level=logging.ERROR)
    startTruckPi()
