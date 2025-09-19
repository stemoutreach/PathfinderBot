"""
PathfinderBot Package

A comprehensive robotics platform for STEM outreach and education.

This package provides a modular, well-documented framework for controlling and
programming the PathfinderBot robot, which includes a mobile platform with
mecanum wheels, a 5-DOF robotic arm, camera system, sensors, and more.
"""

# Version information
__version__ = "1.0.0"
__author__ = "PathfinderBot Team"
__email__ = "info@pathfinderbot.org"

# Import key modules for easier access
from pathfinder_pkg.utils.logging import setup_logging, get_logger
from pathfinder_pkg.sensors.robot_controller import RobotController
from pathfinder_pkg.sensors.simulated_controller import SimulatedRobotController

# Define what's available when using "from pathfinder_pkg import *"
__all__ = ["setup_logging", "get_logger", "RobotController", "SimulatedRobotController"]
