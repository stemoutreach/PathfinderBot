#!/usr/bin/env python3
# encoding: utf-8
# 4DOF robotic arm inverse kinematics: according to the given coordinates (x,y,z) and the pitch angle to, caculate the rotation angle of each joint.
# 2020/07/20 Aiden
import logging
from math import *

# CRITICAL, ERROR, WARNING, INFO, DEBUG
logging.basicConfig(level=logging.ERROR)
logger = logging.getLogger(__name__)

class IK:
    l1 = 8.00    
    l2 = 6.50   
    l3 = 6.20    
    l4 = 0.00     
    l5 = 4.70 
    l6 = 4.46  
    alpha = degrees(atan(l6 / l5)) 

    def __init__(self, arm_type): 
        self.arm_type = arm_type
        if self.arm_type == 'pump':
            self.l4 = sqrt(pow(self.l5, 2) + pow(self.l6, 2))  
        elif self.arm_type == 'arm':
            self.l4 = 10.00  

    def setLinkLength(self, L1=l1, L2=l2, L3=l3, L4=l4, L5=l5, L6=l6):
        self.l1 = L1
        self.l2 = L2
        self.l3 = L3
        self.l4 = L4
        self.l5 = L5
        self.l6 = L6
        if self.arm_type == 'pump':
            self.l4 = sqrt(pow(self.l5, 2) + pow(self.l6, 2))
            self.alpha = degrees(atan(self.l6 / self.l5))

    def getLinkLength(self):
        if self.arm_type == 'pump':
            return {"L1":self.l1, "L2":self.l2, "L3":self.l3, "L4":self.l4, "L5":self.l5, "L6":self.l6}
        else:
            return {"L1":self.l1, "L2":self.l2, "L3":self.l3, "L4":self.l4}

    def getRotationAngle(self, coordinate_data, Alpha):
        X, Y, Z = coordinate_data
        if self.arm_type == 'pump':
            Alpha -= self.alpha
    
        theta6 = degrees(atan2(Y, X))
 
        P_O = sqrt(X*X + Y*Y) 
        CD = self.l4 * cos(radians(Alpha))
        PD = self.l4 * sin(radians(Alpha)) 
        AF = P_O - CD
        CF = Z - self.l1 - PD
        AC = sqrt(pow(AF, 2) + pow(CF, 2))
        if round(CF, 4) < -self.l1:
            logger.debug('高度低于0, CF(%s)<l1(%s)', CF, -self.l1)
            return False
        if self.l2 + self.l3 < round(AC, 4): 
            logger.debug('不能构成连杆结构, l2(%s) + l3(%s) < AC(%s)', self.l2, self.l3, AC)
            return False

 
        cos_ABC = round((pow(self.l2, 2) + pow(self.l3, 2) - pow(AC, 2))/(2*self.l2*self.l3), 4) 
        if abs(cos_ABC) > 1:
            logger.debug('不能构成连杆结构, abs(cos_ABC(%s)) > 1', cos_ABC)
            return False
        ABC = acos(cos_ABC) 
        theta4 = 180.0 - degrees(ABC)

        #求theta5
        CAF = acos(AF / AC)
        cos_BAC = round((pow(AC, 2) + pow(self.l2, 2) - pow(self.l3, 2))/(2*self.l2*AC), 4) 
        if abs(cos_BAC) > 1:
            logger.debug('不能构成连杆结构, abs(cos_BAC(%s)) > 1', cos_BAC)
            return False
        if CF < 0:
            zf_flag = -1
        else:
            zf_flag = 1
        theta5 = degrees(CAF * zf_flag + acos(cos_BAC))

        #求theta3
        theta3 = Alpha - theta5 + theta4
        if self.arm_type == 'pump':
            theta3 += self.alpha

        return {"theta3":theta3, "theta4":theta4, "theta5":theta5, "theta6":theta6} 
            
if __name__ == '__main__':
    ik = IK('arm')
    #ik.setLinkLength(L1=ik.l1 + 1.30, L4=ik.l4)
    print('linkage length：', ik.getLinkLength())
    #print(ik.getRotationAngle((0, ik.l4, ik.l1 + ik.l2 + ik.l3), 0))
