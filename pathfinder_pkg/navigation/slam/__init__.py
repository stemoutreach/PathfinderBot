"""
SLAM (Simultaneous Localization and Mapping) module for PathfinderBot.

This module provides classes and functions for implementing SLAM algorithms
that allow the robot to build a map of its environment while simultaneously
localizing itself within that map.
"""

from pathfinder_pkg.navigation.slam.slam import SLAM
from pathfinder_pkg.navigation.slam.feature_extraction import FeatureExtractor
from pathfinder_pkg.navigation.slam.loop_closure import LoopClosureDetector

__all__ = ["SLAM", "FeatureExtractor", "LoopClosureDetector"]
