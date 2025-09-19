import threading, time
class DetectionManager:
    def __init__(self, camera, detectors: dict, initial="apriltag"):
        self.camera=camera; self.detectors=detectors
        self.current_name = initial if initial in detectors else next(iter(detectors))
        self.current = self.detectors[self.current_name]
        self.latest=None; self._stop=False; self._lock=threading.Lock()
        self.t=threading.Thread(target=self._loop, daemon=True); self.t.start()
    def set_mode(self, name:str):
        if name not in self.detectors: raise KeyError(f"Unknown mode {name}")
        with self._lock:
            self.current_name=name; self.current=self.detectors[name]
            try: self.current.warmup()
            except Exception as e:
                self.latest={"type":name,"items":[],"debug":{"warmup_error":str(e)}}
                return
            self.latest=None
    def get_latest(self): return self.latest
    def get_mode(self): return self.current_name
    def stop(self): self._stop=True
    def _loop(self):
        while not self._stop:
            frame = getattr(self.camera, "frame", None)
            if frame is None: time.sleep(0.01); continue
            with self._lock:
                try: self.latest = self.current.infer(frame)
                except Exception as e:
                    self.latest={"type":self.current_name,"items":[],"debug":{"infer_error":str(e)}}
