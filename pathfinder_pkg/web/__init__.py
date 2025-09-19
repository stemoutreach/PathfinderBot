"""
Web module for PathfinderBot.

This module provides a web-based interface for controlling the robot,
visualizing its state, and configuring its parameters. It uses Flask
to serve a responsive web application that works on desktop and mobile devices.
"""

from pathfinder_pkg.web.server import WebInterface

__all__ = ["WebInterface"]
