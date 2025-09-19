#!/usr/bin/python3
# coding=utf8
import sys
sys.path.append('/home/pi/MasterPi/')
import cv2
import time
import Camera
import threading
import yaml_handle
from ArmIK.Transform import *
from ArmIK.ArmMoveIK import *
import HiwonderSDK.Sonar as Sonar
import HiwonderSDK.Board as Board
from CameraCalibration.CalibrationConfig import *

if sys.version_info.major == 2:
    print('Please run this program with python3!')
    sys.exit(0)

AK = ArmIK()
HWSONAR = Sonar.Sonar() #Ultrasonic sensor

range_rgb = {
    'red':   (0, 0, 255),
    'blue':  (255, 0, 0),
    'green': (0, 255, 0),
    'black': (0, 0, 0),
    'white': (255, 255, 255),
}

lab_data = None
def load_config():
    global lab_data, servo_data
    
    lab_data = yaml_handle.get_yaml_data(yaml_handle.lab_file_path)

__target_color = ('red')
# set detection color
def setTargetColor(target_color):
    global __target_color

    print("COLOR", target_color)
    __target_color = target_color
    return (True, ())

#Find out the contour with the maximum area
#The parameter is the list of the contour to be compared
def getAreaMaxContour(contours) :
        contour_area_temp = 0
        contour_area_max = 0
        area_max_contour = None

        for c in contours : #loop all the contours
            contour_area_temp = math.fabs(cv2.contourArea(c))  #Calculate the contour area
            if contour_area_temp > contour_area_max:
                contour_area_max = contour_area_temp
                if contour_area_temp > 300:  #Only when the area is greater than 300, the maximum contour is effective in order to avoid interference.
                    area_max_contour = c

        return area_max_contour, contour_area_max  #Return the maximum contour

# The closing angle of gripper when gripping
servo1 = 1500

# initial position
def initMove():
    Board.setPWMServoPulse(1, servo1, 800)
    AK.setPitchRangeMoving((0, 8, 10), -90, -90, 0, 1500)

def setBuzzer(timer):
    Board.setBuzzer(0)
    Board.setBuzzer(1)
    time.sleep(timer)
    Board.setBuzzer(0)
    

#RGB light color of expansion board is set to consistent with the color of tracking object.
def set_rgb(color):
    if color == "red":
        Board.RGB.setPixelColor(0, Board.PixelColor(255, 0, 0))
        Board.RGB.setPixelColor(1, Board.PixelColor(255, 0, 0))
        Board.RGB.show()
    elif color == "green":
        Board.RGB.setPixelColor(0, Board.PixelColor(0, 255, 0))
        Board.RGB.setPixelColor(1, Board.PixelColor(0, 255, 0))
        Board.RGB.show()
    elif color == "blue":
        Board.RGB.setPixelColor(0, Board.PixelColor(0, 0, 255))
        Board.RGB.setPixelColor(1, Board.PixelColor(0, 0, 255))
        Board.RGB.show()
    else:
        Board.RGB.setPixelColor(0, Board.PixelColor(0, 0, 0))
        Board.RGB.setPixelColor(1, Board.PixelColor(0, 0, 0))
        Board.RGB.show()

count = 0
_stop = False
color_list = []
get_roi = False
__isRunning = False
detect_color = 'None'
start_pick_up = False
start_count_t1 = True

# Reset variable
def reset():
    global _stop
    global count
    global get_roi
    global color_list
    global detect_color
    global start_pick_up
    global __target_color
    global start_count_t1

    count = 0
    _stop = False
    color_list = []
    get_roi = False
    __target_color = ()
    detect_color = 'None'
    start_pick_up = False
    start_count_t1 = True

# APP initialized calling
def init():
    print("ColorSorting Init")
    # The ligt is off after turning on the ultrasonice sensor
    HWSONAR.setRGBMode(0)
    HWSONAR.setPixelColor(0, Board.PixelColor(0,0,0))
    HWSONAR.setPixelColor(1, Board.PixelColor(0,0,0))    
    HWSONAR.show()
    load_config()
    initMove()

# APP starts game calling
def start():
    global __isRunning
    reset()
    __isRunning = True
    print("ColorSorting Start")

# APP stops game calling
def stop():
    global _stop
    global __isRunning
    _stop = True
    __isRunning = False
    set_rgb('None')
    print("ColorSorting Stop")

# APP exits game calling
def exit():
    global _stop
    global __isRunning
    _stop = True
    set_rgb('None')
    __isRunning = False
    print("ColorSorting Exit")


rect = None
size = (640, 480)
rotation_angle = 0
unreachable = False 
world_X, world_Y = 0, 0
def move():
    global rect
    global _stop
    global get_roi
    global unreachable
    global __isRunning
    global detect_color
    global start_pick_up
    global rotation_angle
    global world_X, world_Y
    
    #placement coordinate
    coordinate = {
        'red':   (-15, 14, 2),
        'green': (-18, 9,  3),
        'blue':  (-18, 0, 2),
        'capture': (0, 16.5, 2)
    }
    
    while True:
        if __isRunning:        
            if detect_color != 'None' and start_pick_up:  #Grip after detecting block.
                
                set_rgb(detect_color) # RGB light color of expansion board is set to consistent with the color of tracking object.
                setBuzzer(0.1)     # The buzzer is set to sound for 0.1s
                
                AK.setPitchRangeMoving((0, 6, 18), 0,-90, 90, 1500) # lift up robotic arm 
                time.sleep(1.5)
                if not __isRunning:  # Detect whether to stop game
                    continue
                Board.setPWMServoPulse(1, 2000, 500) # the gripper opens
                time.sleep(1.5)
                if not __isRunning:
                    continue
                Board.setPWMServoPulse(1, 1500, 500) # the gripper closes
                time.sleep(1.5)
                if not __isRunning:
                    continue
                if detect_color == 'red':       # The robotic arm rotates to the corresponding angle according to the detected color.
                    Board.setPWMServoPulse(6, 1900, 500)
                    time.sleep(0.5)
                elif detect_color == 'green':
                    Board.setPWMServoPulse(6, 2100, 800)
                    time.sleep(0.8)
                elif detect_color == 'blue':
                    Board.setPWMServoPulse(6, 2500, 1500)
                    time.sleep(1.5)
                if not __isRunning:
                    continue
                result = AK.setPitchRangeMoving((coordinate[detect_color][0], coordinate[detect_color][1], 8), -90, -90, 0) # Move to above the coordinates of the corresponding color
                if result == False:
                    unreachable = True
                else:
                    unreachable = False
                    time.sleep(result[2]/1000) #If it can get to the specific posiiton, the running time is obtained.
                if not __isRunning:
                    continue
                AK.setPitchRangeMoving((coordinate[detect_color]), -90, -90, 0, 500)  # Place at the coordinate of the detected color
                time.sleep(0.5)
                if not __isRunning:
                    continue
                Board.setPWMServoPulse(1, 1800, 500) # The gripper opens 
                time.sleep(0.5)
                if not __isRunning:
                    continue
                AK.setPitchRangeMoving((coordinate[detect_color][0], coordinate[detect_color][1], 8), -90, -90, 0, 800) #  Move to above the coordinates of the corresponding color
                time.sleep(0.8)
                if not __isRunning:
                    continue
                Board.setPWMServosPulse([1200, 4, 1,1500, 3,515, 4,2170, 5,945]) # reset the robotic arm
                time.sleep(1.2)
                if detect_color == 'red':
                    Board.setPWMServoPulse(6, 1500, 500)
                    time.sleep(0.5)
                elif detect_color == 'green':
                    Board.setPWMServoPulse(6, 1500, 800)
                    time.sleep(0.8)
                elif detect_color == 'blue':
                    Board.setPWMServoPulse(6, 1500, 1500)
                    time.sleep(1.5)
                AK.setPitchRangeMoving((0, 8, 10), -90, -90, 0, 1000)
                time.sleep(1)
                
                detect_color = 'None'
                get_roi = False
                start_pick_up = False
                set_rgb(detect_color)
            else:
                time.sleep(0.01)                
        else:
            if _stop:
                _stop = False
                initMove()
            time.sleep(0.01)
          
#Run subthread
th = threading.Thread(target=move)
th.setDaemon(True)
th.start()    

t1 = 0
roi = ()
center_list = []
last_x, last_y = 0, 0
draw_color = range_rgb["black"]
length = 50
w_start = 200
h_start = 200
def run(img):
    global roi
    global rect
    global count
    global get_roi
    global center_list
    global unreachable
    global __isRunning
    global start_pick_up
    global rotation_angle
    global last_x, last_y
    global world_X, world_Y
    global start_count_t1, t1
    global detect_color, draw_color, color_list
    
    img_copy = img.copy()
    img_h, img_w = img.shape[:2]   

    if not __isRunning: # Detect whether the game is started, if not, return the original image.
        return img
    
    frame_resize = cv2.resize(img_copy, size, interpolation=cv2.INTER_NEAREST)
    frame_gb = cv2.GaussianBlur(frame_resize, (3, 3), 3)     
    frame_lab = cv2.cvtColor(frame_gb, cv2.COLOR_BGR2LAB)  # Convert the image into LAB space 

    color_area_max = None
    max_area = 0
    areaMaxContour_max = 0
    
    if not start_pick_up:
        for i in lab_data:
            if i in __target_color:
                frame_mask = cv2.inRange(frame_lab,
                                             (lab_data[i]['min'][0],
                                              lab_data[i]['min'][1],
                                              lab_data[i]['min'][2]),
                                             (lab_data[i]['max'][0],
                                              lab_data[i]['max'][1],
                                              lab_data[i]['max'][2]))  #Perform bit operation on the original image and mask
                opened = cv2.morphologyEx(frame_mask, cv2.MORPH_OPEN, np.ones((3, 3),np.uint8))  #Open 
                closed = cv2.morphologyEx(opened, cv2.MORPH_CLOSE, np.ones((3, 3),np.uint8)) #Close
                closed[:, 0:100] = 0
                contours = cv2.findContours(closed, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)[-2]  #Find out the contour
                areaMaxContour, area_max = getAreaMaxContour(contours)  #Find out the maximum contour
                if areaMaxContour is not None:
                    if area_max > max_area:#Find out the maximum area
                        max_area = area_max
                        color_area_max = i
                        areaMaxContour_max = areaMaxContour
        if max_area > 2500:  # The maximum area is found
            rect = cv2.minAreaRect(areaMaxContour_max)
            box = np.int0(cv2.boxPoints(rect))
            cv2.drawContours(img, [box], -1, range_rgb[color_area_max], 2)
            
            if not start_pick_up:
                if color_area_max == 'red':  #Red area is the largest
                    color = 1
                elif color_area_max == 'green':  #Green area is the largest
                    color = 2
                elif color_area_max == 'blue':  #Blue area is the largest
                    color = 3
                else:
                    color = 0
                color_list.append(color)

                if len(color_list) == 3:  #Determine for multiple times
                    # Take the average
                    color = int(round(np.mean(np.array(color_list))))
                    color_list = []
                    if color:
                        start_pick_up = True
                        if color == 1:
                            detect_color = 'red'
                            draw_color = range_rgb["red"]
                        elif color == 2:
                            detect_color = 'green'
                            draw_color = range_rgb["green"]
                        elif color == 3:
                            detect_color = 'blue'
                            draw_color = range_rgb["blue"]
                    else:
                        start_pick_up = False
                        detect_color = 'None'
                        draw_color = range_rgb["black"]
        else:
            if not start_pick_up:
                draw_color = (0, 0, 0)
                detect_color = "None"

    cv2.putText(img, "Color: " + detect_color, (10, img.shape[0] - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.65, draw_color, 2)
    return img

if __name__ == '__main__':
    init()
    start()
    __target_color = ('red', 'green', 'blue')
    cap = cv2.VideoCapture('http://127.0.0.1:8080?action=stream')
    while True:
        ret,img = cap.read()
        if ret:
            frame = img.copy()
            Frame = run(frame)  
            frame_resize = cv2.resize(Frame, (320, 240))
            cv2.imshow('frame', frame_resize)
            key = cv2.waitKey(1)
            if key == 27:
                break
        else:
            time.sleep(0.01)
    cv2.destroyAllWindows()