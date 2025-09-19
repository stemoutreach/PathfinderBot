#!/usr/bin/env python3
import os
import sys
import time
import yaml_handle
import RPi.GPIO as GPIO
from smbus2 import SMBus, i2c_msg
from rpi_ws281x import PixelStrip
from rpi_ws281x import Color as PixelColor



__ADC_BAT_ADDR = 0
__SERVO_ADDR   = 21
__MOTOR_ADDR   = 31
__SERVO_ADDR_CMD  = 40

__motor_speed = [0, 0, 0, 0]
__servo_angle = [0, 0, 0, 0, 0, 0]
__servo_pulse = [0, 0, 0, 0, 0, 0]
__i2c = 1
__i2c_addr = 0x7A

GPIO.setwarnings(False)
GPIO.setmode(GPIO.BOARD)

__RGB_COUNT = 2
__RGB_PIN = 12
__RGB_FREQ_HZ = 800000
__RGB_DMA = 10
__RGB_BRIGHTNESS = 120
__RGB_CHANNEL = 0
__RGB_INVERT = False
RGB = PixelStrip(__RGB_COUNT, __RGB_PIN, __RGB_FREQ_HZ, __RGB_DMA, __RGB_INVERT, __RGB_BRIGHTNESS, __RGB_CHANNEL)
RGB.begin()
for i in range(RGB.numPixels()):
    RGB.setPixelColor(i, PixelColor(0,0,0))
    RGB.show()

def setMotor(index, speed):
    if index < 1 or index > 4:
        raise AttributeError("Invalid motor num: %d"%index)
    if index == 2 or index == 4:
        speed = speed
    else:
        speed = -speed
    index = index - 1
    speed = 100 if speed > 100 else speed
    speed = -100 if speed < -100 else speed
    reg = __MOTOR_ADDR + index
    
    with SMBus(__i2c) as bus:
        try:
            msg = i2c_msg.write(__i2c_addr, [reg, speed.to_bytes(1, 'little', signed=True)[0]])
            bus.i2c_rdwr(msg)
            __motor_speed[index] = speed
            
        except:
            msg = i2c_msg.write(__i2c_addr, [reg, speed.to_bytes(1, 'little', signed=True)[0]])
            bus.i2c_rdwr(msg)
            __motor_speed[index] = speed
           
    return __motor_speed[index]

     
def getMotor(index):
    if index < 1 or index > 4:
        raise AttributeError("Invalid motor num: %d"%index)
    index = index - 1
    return __motor_speed[index]

def setPWMServoAngle(index, angle):
    if servo_id < 1 or servo_id > 6:
        raise AttributeError("Invalid Servo ID: %d"%servo_id)
    index = servo_id - 1
    angle = 180 if angle > 180 else angle
    angle = 0 if angle < 0 else angle
    reg = __SERVO_ADDR + index
    with SMBus(__i2c) as bus:
        try:
            msg = i2c_msg.write(__i2c_addr, [reg, angle])
            bus.i2c_rdwr(msg)
            __servo_angle[index] = angle
            __servo_pulse[index] = int(((200 * angle) / 9) + 500)

        except:
            msg = i2c_msg.write(__i2c_addr, [reg, angle])
            bus.i2c_rdwr(msg)
            __servo_angle[index] = angle
            __servo_pulse[index] = int(((200 * angle) / 9) + 500)

    return __servo_angle[index]

def setPWMServoPulse(servo_id, pulse = 1500, use_time = 1000):
    if servo_id< 1 or servo_id > 6:
        raise AttributeError("Invalid Servo ID: %d" %servo_id)
    deviation_data = yaml_handle.get_yaml_data(yaml_handle.Deviation_file_path)
    index = servo_id - 1
    pulse += deviation_data[str(servo_id)]
    pulse = 500 if pulse < 500 else pulse
    pulse = 2500 if pulse > 2500 else pulse
    use_time = 0 if use_time < 0 else use_time
    use_time = 30000 if use_time > 30000 else use_time
    buf = [__SERVO_ADDR_CMD, 1] + list(use_time.to_bytes(2, 'little')) + [servo_id,] + list(pulse.to_bytes(2, 'little'))
    
    with SMBus(__i2c) as bus:
        try:
            msg = i2c_msg.write(__i2c_addr, buf)
            bus.i2c_rdwr(msg)
            __servo_pulse[index] = pulse
            __servo_angle[index] = int((pulse - 500) * 0.09)
        except BaseException as e:
            print(e)
            msg = i2c_msg.write(__i2c_addr, buf)
            bus.i2c_rdwr(msg)
            __servo_pulse[index] = pulse
            __servo_angle[index] = int((pulse - 500) * 0.09)

    return __servo_pulse[index]

def setPWMServosPulse(args):
    ''' time,number, id1, pos1, id2, pos2...'''
    deviation_data = yaml_handle.get_yaml_data(yaml_handle.Deviation_file_path)
    arglen = len(args)
    servos = args[2:arglen:2]
    pulses = args[3:arglen:2]
    use_time = args[0]
    use_time = 0 if use_time < 0 else use_time
    use_time = 30000 if use_time > 30000 else use_time
    servo_number = args[1]
    buf = [__SERVO_ADDR_CMD, servo_number] + list(use_time.to_bytes(2, 'little'))
    dat = zip(servos, pulses)
    for (s, p) in dat:
        buf.append(s)
        p += deviation_data[str(s)]
        p = 500 if p < 500 else p
        p = 2500 if p > 2500 else p
        buf += list(p.to_bytes(2, 'little'))  
        __servo_pulse[s-1] = p
        __servo_angle[s-1] = int((p - 500) * 0.09)
     
    with SMBus(__i2c) as bus:
        try:
            msg = i2c_msg.write(__i2c_addr, buf)
            bus.i2c_rdwr(msg)
        except:
            msg = i2c_msg.write(__i2c_addr, buf)
            bus.i2c_rdwr(msg)


def getPWMServoAngle(servo_id):
    if servo_id < 1 or servo_id > 6:
        raise AttributeError("Invalid Servo ID: %d"%servo_id)
    index = servo_id - 1
    return __servo_pulse[index]

def getPWMServoPulse(servo_id):
    if servo_id < 1 or servo_id > 6:
        raise AttributeError("Invalid Servo ID: %d"%servo_id)
    index = servo_id - 1
    return __servo_pulse[index]
    
def getBattery():
    ret = 0
    with SMBus(__i2c) as bus:
        try:
            msg = i2c_msg.write(__i2c_addr, [__ADC_BAT_ADDR,])
            bus.i2c_rdwr(msg)
            read = i2c_msg.read(__i2c_addr, 2)
            bus.i2c_rdwr(read)
            ret = int.from_bytes(bytes(list(read)), 'little')
            
        except:
            msg = i2c_msg.write(__i2c_addr, [__ADC_BAT_ADDR,])
            bus.i2c_rdwr(msg)
            read = i2c_msg.read(__i2c_addr, 2)
            bus.i2c_rdwr(read)
            ret = int.from_bytes(bytes(list(read)), 'little')
           
    return ret

def setBuzzer(new_state):
    GPIO.setup(31, GPIO.OUT)
    GPIO.output(31, new_state)

def setBusServoID(oldid, newid):
    """
    Configure servo ID. It defualts to 1 
    :param oldid: The old ID defaults to 1.
    :param newid: The new ID 
    """
    serial_serro_wirte_cmd(oldid, LOBOT_SERVO_ID_WRITE, newid)

def getBusServoID(id=None):
    """
    read servo ID 
    :param id: empty by default
    :return: return servo ID 
    """
    
    while True:
        if id is None:  # A servo only is connected.
            serial_servo_read_cmd(0xfe, LOBOT_SERVO_ID_READ)
        else:
            serial_servo_read_cmd(id, LOBOT_SERVO_ID_READ)
        # get conetent
        msg = serial_servo_get_rmsg(LOBOT_SERVO_ID_READ)
        if msg is not None:
            return msg

def setBusServoPulse(id, pulse, use_time):
    """
    Drive the servo to the specific position 
    :param id: The ID of servo to be driven
    :pulse: position
    :use_time: The required time for rotation
    """

    pulse = 0 if pulse < 0 else pulse
    pulse = 1000 if pulse > 1000 else pulse
    use_time = 0 if use_time < 0 else use_time
    use_time = 30000 if use_time > 30000 else use_time
    serial_serro_wirte_cmd(id, LOBOT_SERVO_MOVE_TIME_WRITE, pulse, use_time)

def stopBusServo(id=None):
    '''
    stop running servo
    :param id:
    :return:
    '''
    serial_serro_wirte_cmd(id, LOBOT_SERVO_MOVE_STOP)

def setBusServoDeviation(id, d=0):
    """
    Adjust deviation
    :param id: servo ID 
    :param d:  deviation
    """
    serial_serro_wirte_cmd(id, LOBOT_SERVO_ANGLE_OFFSET_ADJUST, d)

def saveBusServoDeviation(id):
    """
    Configure deviation, power off protection
    :param id: 舵机id
    """
    serial_serro_wirte_cmd(id, LOBOT_SERVO_ANGLE_OFFSET_WRITE)

time_out = 50
def getBusServoDeviation(id):
    '''
    read deviation
    :param id: servo ID 
    :return:
    '''
    # send the command for reading deviation
    count = 0
    while True:
        serial_servo_read_cmd(id, LOBOT_SERVO_ANGLE_OFFSET_READ)
        # get
        msg = serial_servo_get_rmsg(LOBOT_SERVO_ANGLE_OFFSET_READ)
        count += 1
        if msg is not None:
            return msg
        if count > time_out:
            return None

def setBusServoAngleLimit(id, low, high):
    '''
    set the range of servo rotation 
    :param id:
    :param low:
    :param high:
    :return:
    '''
    serial_serro_wirte_cmd(id, LOBOT_SERVO_ANGLE_LIMIT_WRITE, low, high)

def getBusServoAngleLimit(id):
    '''
    read the range of servo rotation 
    :param id:
    :return: return tuple 0： low bit  1： high bit
    '''
    
    while True:
        serial_servo_read_cmd(id, LOBOT_SERVO_ANGLE_LIMIT_READ)
        msg = serial_servo_get_rmsg(LOBOT_SERVO_ANGLE_LIMIT_READ)
        if msg is not None:
            count = 0
            return msg

def setBusServoVinLimit(id, low, high):
    '''
    set the range of servo rotation
    :param id:
    :param low:
    :param high:
    :return:
    '''
    serial_serro_wirte_cmd(id, LOBOT_SERVO_VIN_LIMIT_WRITE, low, high)

def getBusServoVinLimit(id):
    '''
    read the range of servo rotation 
    :param id:
    :return: return tuple 0： low bit  1： high bit
    '''
    while True:
        serial_servo_read_cmd(id, LOBOT_SERVO_VIN_LIMIT_READ)
        msg = serial_servo_get_rmsg(LOBOT_SERVO_VIN_LIMIT_READ)
        if msg is not None:
            return msg

def setBusServoMaxTemp(id, m_temp):
    '''
    set the servo alarming at the highest temperature 
    :param id:
    :param m_temp:
    :return:
    '''
    serial_serro_wirte_cmd(id, LOBOT_SERVO_TEMP_MAX_LIMIT_WRITE, m_temp)

def getBusServoTempLimit(id):
    '''
    read the temperature range of the servo alarming
    :param id:
    :return:
    '''
    
    while True:
        serial_servo_read_cmd(id, LOBOT_SERVO_TEMP_MAX_LIMIT_READ)
        msg = serial_servo_get_rmsg(LOBOT_SERVO_TEMP_MAX_LIMIT_READ)
        if msg is not None:
            return msg

def getBusServoPulse(id):
    '''
     read the current position of servo
    :param id:
    :return:
    '''
    while True:
        serial_servo_read_cmd(id, LOBOT_SERVO_POS_READ)
        msg = serial_servo_get_rmsg(LOBOT_SERVO_POS_READ)
        if msg is not None:
            return msg

def getBusServoTemp(id):
    '''
    read the servo temperature
    :param id:
    :return:
    '''
    while True:
        serial_servo_read_cmd(id, LOBOT_SERVO_TEMP_READ)
        msg = serial_servo_get_rmsg(LOBOT_SERVO_TEMP_READ)
        if msg is not None:
            return msg

def getBusServoVin(id):
    '''
    read servo voltage
    :param id:
    :return:
    '''
    while True:
        serial_servo_read_cmd(id, LOBOT_SERVO_VIN_READ)
        msg = serial_servo_get_rmsg(LOBOT_SERVO_VIN_READ)
        if msg is not None:
            return msg

def restBusServoPulse(oldid):
    # The servo deviation is cleared to 0 and the P value is at the middle position (500)
    serial_servo_set_deviation(oldid, 0)    # the deviation is cleared to 0
    time.sleep(0.1)
    serial_serro_wirte_cmd(oldid, LOBOT_SERVO_MOVE_TIME_WRITE, 500, 100)    # Middle position

##power off
def unloadBusServo(id):
    serial_serro_wirte_cmd(id, LOBOT_SERVO_LOAD_OR_UNLOAD_WRITE, 0)

##read whether it powers off 
def getBusServoLoadStatus(id):
    while True:
        serial_servo_read_cmd(id, LOBOT_SERVO_LOAD_OR_UNLOAD_READ)
        msg = serial_servo_get_rmsg(LOBOT_SERVO_LOAD_OR_UNLOAD_READ)
        if msg is not None:
            return msg

setBuzzer(0)

# setMotor(1, 60)
# setMotor(2, 60)
# setMotor(3, 60)
# setMotor(4, 60)

