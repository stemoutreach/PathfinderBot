from abc import ABC, abstractmethod

class Detector(ABC):
    name: str = "base"
    def warmup(self): pass
    @abstractmethod
    def infer(self, frame_bgr):
        raise NotImplementedError
