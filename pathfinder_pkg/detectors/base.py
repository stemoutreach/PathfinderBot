"""
Base detector classes for PathfinderBot.

This module defines abstract base classes for various types of detectors
used in the PathfinderBot system, such as object detection, AprilTag detection,
and block detection.
"""

from abc import ABC, abstractmethod
from pathfinder_pkg.utils.logging import get_logger

logger = get_logger(__name__)


class Detector(ABC):
    """
    Abstract base class for all detectors.

    All detector implementations should inherit from this class and implement
    the required methods.

    Attributes:
        name (str): The name of the detector.
    """

    name: str = "base"

    def __init__(self):
        """Initialize the detector."""
        logger.debug(f"Initializing {self.name} detector")

    def warmup(self):
        """
        Perform any necessary warm-up steps for the detector.

        This might involve loading models, initializing hardware, etc.
        Default implementation does nothing.
        """
        pass

    @abstractmethod
    def infer(self, frame_bgr):
        """
        Process a frame and detect objects.

        Args:
            frame_bgr (numpy.ndarray): BGR image frame to process.

        Returns:
            dict: Detection results with standardized format.
        """
        raise NotImplementedError

    def release(self):
        """
        Release any resources used by the detector.

        Default implementation does nothing.
        """
        pass


class ObjectDetector(Detector):
    """
    Base class for object detectors.

    This class specializes the Detector base class for general object detection.
    """

    name = "object"

    def infer(self, frame_bgr):
        """
        Process a frame and detect objects.

        Args:
            frame_bgr (numpy.ndarray): BGR image frame to process.

        Returns:
            dict: Object detection results.
        """
        # This is an abstract base class, so provide a basic implementation
        # that should be overridden by subclasses
        return {"type": self.name, "items": []}
