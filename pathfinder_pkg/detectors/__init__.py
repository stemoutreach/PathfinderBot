"""
Detector modules for PathfinderBot.

This package provides various detector implementations for vision-based
detection of objects, AprilTags, and colored blocks.
"""

from .base import Detector, ObjectDetector
from .block_detector import BlockDetector, EnhancedBlockDetector

__all__ = [
    "Detector",
    "ObjectDetector",
    "BlockDetector",
    "EnhancedBlockDetector",
]
