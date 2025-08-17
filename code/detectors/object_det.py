import cv2, numpy as np, os
from .base import Detector
DEFAULT_PROTOTXT = "models/MobileNetSSD_deploy.prototxt"
DEFAULT_MODEL    = "models/MobileNetSSD_deploy.caffemodel"
DEFAULT_LABELS = ["background","aeroplane","bicycle","bird","boat","bottle","bus","car","cat","chair",
                  "cow","diningtable","dog","horse","motorbike","person","pottedplant","sheep","sofa",
                  "train","tvmonitor"]
class ObjectDetector(Detector):
    name="object"
    def __init__(self, model_path=DEFAULT_MODEL, prototxt=DEFAULT_PROTOTXT, conf=0.5, frame_skip=1):
        self.model_path=model_path; self.prototxt=prototxt; self.conf=float(conf)
        self.frame_skip=max(0,int(frame_skip)); self._i=0; self._net=None; self.labels=DEFAULT_LABELS
    def warmup(self):
        if not (os.path.exists(self.model_path) and os.path.exists(self.prototxt)):
            raise RuntimeError(f"Missing model files for ObjectDetector: {self.prototxt}, {self.model_path}")
        self._net = cv2.dnn.readNetFromCaffe(self.prototxt, self.model_path)
    def infer(self, frame_bgr):
        self._i = (self._i + 1) % (self.frame_skip + 1)
        if self._i: return {"type":"object","items":[],"debug":{"skipped":True}}
        if self._net is None: self.warmup()
        h,w = frame_bgr.shape[:2]
        blob = cv2.dnn.blobFromImage(cv2.resize(frame_bgr,(300,300)), 0.007843, (300,300), 127.5)
        self._net.setInput(blob)
        detections = self._net.forward()
        items = []
        for i in range(detections.shape[2]):
            conf = float(detections[0,0,i,2])
            if conf < self.conf: continue
            idx = int(detections[0,0,i,1])
            box = detections[0,0,i,3:7] * np.array([w,h,w,h])
            x1,y1,x2,y2 = box.astype(int).tolist()
            label = self.labels[idx] if 0<=idx<len(self.labels) else str(idx)
            items.append({"label":label,"conf":conf,"box":[x1,y1,x2,y2]})
        return {"type":"object","items":items,"debug":{"count":len(items)}}
