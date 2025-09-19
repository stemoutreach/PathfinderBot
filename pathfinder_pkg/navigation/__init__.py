"""
Navigation module for PathfinderBot.

This module provides classes and functions for robot navigation, mapping,
localization, path planning, and SLAM.
"""

# Import key components for easier access
from pathfinder_pkg.navigation.map import OccupancyGridMap
from pathfinder_pkg.navigation.localization import Pose
from pathfinder_pkg.navigation.slam.slam import SLAM
from pathfinder_pkg.navigation.behaviors.navigator import NavigationController

__all__ = ["OccupancyGridMap", "Pose", "SLAM", "NavigationController"]
