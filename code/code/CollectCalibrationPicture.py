#!/usr/bin/env python3
# encoding:utf-8
import os
import cv2
from CalibrationConfig import *

#Collect calibration image and save into the calib folder
#Press space key to save image and press "Esc" to exit

cap = cv2.VideoCapture(-1)

#If calib folder does not exit, create a new one.
if not os.path.exists(save_path):
    os.mkdir(save_path)

#caculate the number of images.
num = 0
while True:
    ret, frame = cap.read()
    if ret:
        Frame = frame.copy()
        cv2.putText(Frame, str(num), (10, 50), cv2.FONT_HERSHEY_COMPLEX, 2.0, (0, 0, 255), 5)
        cv2.imshow("Frame", Frame)
        key = cv2.waitKey(1)
        if key == 27:
            break
        if key == 32:
            num += 1
            #The format of image name: current image number.jpg
            cv2.imwrite(save_path + str(num) + ".jpg", frame) 

cap.release()
cv2.destroyAllWindows()
