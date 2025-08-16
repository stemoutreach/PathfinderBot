
import sys
import cv2
import time
import threading
import numpy as np
from CalibrationConfig import *
from pupil_apriltags import Detector

TAG_TABLE = {
    0:"TURN_LEFT",
    1:"TURN_RIGHT",
    2:"STRAFE_LEFT",
    3:"STRAFE_RIGHT",
    4:"FINISH",
}

class Camera:
    def __init__(self, resolution=(640, 480)):
        self.cap = None
        self.width = resolution[0]
        self.height = resolution[1]
        self.frame = None
        self.opened = False
        self.param_data = np.load(calibration_param_path + '.npz')
        self.detector = Detector(families='tag36h11')
        self.mtx = self.param_data['mtx_array']
        self.dist = self.param_data['dist_array']
        self.newcameramtx, roi = cv2.getOptimalNewCameraMatrix(
            self.mtx, self.dist, (self.width, self.height), 0, (self.width, self.height)
        )
        self.mapx, self.mapy = cv2.initUndistortRectifyMap(
            self.mtx, self.dist, None, self.newcameramtx, (self.width, self.height), 5
        )
        self.th = threading.Thread(target=self.camera_task, args=(), daemon=True)
        self.th.start()

    def camera_open(self, correction=False):
        try:
            self.cap = cv2.VideoCapture(0)
            self.cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc('Y', 'U', 'Y', 'V'))
            self.cap.set(cv2.CAP_PROP_FPS, 30)
            self.cap.set(cv2.CAP_PROP_SATURATION, 40)
            self.correction = correction
            self.opened = True
        except Exception as e:
            print('Fail to turn on camera:', e)

    def camera_close(self):
        try:
            self.opened = False
            time.sleep(0.2)
            if self.cap is not None:
                self.cap.release()
                time.sleep(0.05)
            self.cap = None
        except Exception as e:
            print('Fail to turn off camera:', e)

    def camera_task(self):
        while True:
            try:
                if self.opened and self.cap.isOpened():
                    ret, frame_tmp = self.cap.read()
                    if ret:
                        frame_resize = cv2.resize(frame_tmp, (self.width, self.height), interpolation=cv2.INTER_NEAREST)
                        self.frame = cv2.remap(frame_resize, self.mapx, self.mapy, cv2.INTER_LINEAR)
                    else:
                        print(1)
                        self.frame = None
                        cap = cv2.VideoCapture(0)
                        ret, _ = cap.read()
                        if ret:
                            self.cap = cap
                elif self.opened:
                    print(2)
                    cap = cv2.VideoCapture(0)
                    ret, _ = cap.read()
                    if ret:
                        self.cap = cap
                else:
                    time.sleep(0.01)
            except Exception as e:
                print('Capture camera screen error:', e)
                time.sleep(0.01)

# Only for testing/demo, NOT for web app usage!
if __name__ == '__main__':
    my_camera = Camera()
    my_camera.camera_open(correction=True)
    detector = Detector(families='tag36h11')
    time.sleep(0.5)
    while True:
        frame = my_camera.frame
        if frame is None:
            continue
        # --- Standalone demo: overlay here ONLY if you run this file directly ---
        gray  = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        tags  = detector.detect(gray)
        for tag in tags:
            pts = tag.corners.astype(int)
            for i in range(4):
                cv2.line(frame, tuple(pts[i]), tuple(pts[(i + 1) % 4]), (0, 255, 0), 2)
            x_min, x_max = pts[:, 0].min(), pts[:, 0].max()
            y_max = pts[:, 1].max()
            x_mid = (x_min + x_max) // 2
            y_txt = y_max + 15
            label_text = TAG_TABLE.get(tag.tag_id, str(tag.tag_id))
            font = cv2.FONT_HERSHEY_SIMPLEX
            font_scale, thickness = 0.6, 2
            (text_w, text_h), _ = cv2.getTextSize(label_text, font, font_scale, thickness)
            label_pos = (x_mid - text_w // 2, y_txt + text_h)
            cv2.putText(frame, label_text, label_pos, font, font_scale, (0, 0, 0), thickness, cv2.LINE_AA)
        cv2.imshow("AprilCam", frame)
        if cv2.waitKey(1) & 0xFF == 27:
            break
    my_camera.camera_close()
    cv2.destroyAllWindows()
