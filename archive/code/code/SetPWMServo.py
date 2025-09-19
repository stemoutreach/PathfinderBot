#!/usr/bin/env python3
import os
import sys
import time
import RPi.GPIO as GPIO
from smbus2 import SMBus, i2c_msg

if sys.version_info.major == 2:
    print('Please run this program with python3!')
    sys.exit(0)

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

def setPWMServosPulse(args):
    ''' time,number, id1, pos1, id2, pos2...'''
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

def setPWMServoPulse(servo_id, pulse = 1500, use_time = 1000):
    if servo_id< 1 or servo_id > 6:
        raise AttributeError("Invalid Servo ID: %d" %servo_id)
    index = servo_id - 1
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
        except:
            msg = i2c_msg.write(__i2c_addr, buf)
            bus.i2c_rdwr(msg)
            __servo_pulse[index] = pulse
            __servo_angle[index] = int((pulse - 500) * 0.09)

    return __servo_pulse[index]

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
    

