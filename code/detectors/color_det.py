import cv2, numpy as np
from .base import Detector
class ColorDetector(Detector):
    name="color"
    def __init__(self, hsv_ranges=None):
        self.hsv_ranges = hsv_ranges or {
            "red":[([0,120,70],[10,255,255]),([170,120,70],[180,255,255])],
            "green":[([35,100,70],[85,255,255])],
            "blue":[([90,100,70],[130,255,255])],
        }
    def infer(self, frame_bgr):
        hsv = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2HSV)
        items=[]
        for color, ranges in self.hsv_ranges.items():
            mask=None
            for lo,hi in ranges:
                lo=np.array(lo,np.uint8); hi=np.array(hi,np.uint8)
                m=cv2.inRange(hsv,lo,hi)
                mask = m if mask is None else (mask|m)
            cnts,_ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            cnts = sorted(cnts, key=cv2.contourArea, reverse=True)[:3]
            for c in cnts:
                area=cv2.contourArea(c)
                if area<300: continue
                x,y,w,h=cv2.boundingRect(c)
                items.append({"color":color,"box":[x,y,x+w,y+h],"area":int(area)})
        return {"type":"color","items":items,"debug":{"colors":list(self.hsv_ranges.keys())}}
