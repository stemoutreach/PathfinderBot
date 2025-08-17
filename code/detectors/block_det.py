import cv2, numpy as np
from .base import Detector
class BlockDetector(Detector):
    name="block"
    def __init__(self, hsv_ranges=None, min_area=1200, rect_min_fill=0.6):
        self.hsv_ranges = hsv_ranges or {
            "red":[([0,120,70],[10,255,255]),([170,120,70],[180,255,255])],
            "green":[([35,100,70],[85,255,255])],
            "blue":[([90,100,70],[130,255,255])],
            "yellow":[([18,120,120],[35,255,255])],
        }
        self.min_area=int(min_area); self.rect_min_fill=float(rect_min_fill)
    def infer(self, frame_bgr):
        hsv = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2HSV)
        full=None
        for ranges in self.hsv_ranges.values():
            m=None
            for lo,hi in ranges:
                lo=np.array(lo,np.uint8); hi=np.array(hi,np.uint8)
                mm=cv2.inRange(hsv,lo,hi)
                m = mm if m is None else (m|mm)
            full = m if full is None else (full|m)
        if full is None:
            return {"type":"block","items":[], "debug":{"note":"no hsv ranges"}}
        full = cv2.morphologyEx(full, cv2.MORPH_OPEN, np.ones((3,3),np.uint8), iterations=1)
        full = cv2.morphologyEx(full, cv2.MORPH_CLOSE, np.ones((5,5),np.uint8), iterations=1)
        cnts,_ = cv2.findContours(full, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        items=[]
        for c in cnts:
            area=cv2.contourArea(c)
            if area<self.min_area: continue
            x,y,w,h=cv2.boundingRect(c)
            rect_area=w*h if w>0 and h>0 else 1
            fill = area/rect_area
            if fill<self.rect_min_fill: continue
            peri=cv2.arcLength(c,True)
            approx=cv2.approxPolyDP(c,0.04*peri,True)
            if len(approx)<4: continue
            items.append({"label":"block","box":[int(x),int(y),int(x+w),int(y+h)],"area":int(area),"fill":float(fill),"corners":int(len(approx))})
        items.sort(key=lambda it: it["area"], reverse=True)
        return {"type":"block","items":items[:3], "debug":{"count":len(items)}}
