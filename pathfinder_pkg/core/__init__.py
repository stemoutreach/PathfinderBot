"""
Core modules for PathfinderBot.

This package contains the fundamental components and interfaces for controlling
the PathfinderBot hardware.
"""

from .robot import Robot, robot
from .mecanum import MecanumChassis

__all__ = ["Robot", "robot", "MecanumChassis"]
