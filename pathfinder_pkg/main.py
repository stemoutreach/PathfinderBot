#!/usr/bin/env python3
"""
Main entry point for PathfinderBot.

This module initializes and connects all the major components of the PathfinderBot
system, including navigation, sensors, and the web interface.
"""

import os
import sys
import time
import argparse
import logging
import signal
import threading
from typing import Optional, Any

from pathfinder_pkg.utils.logging import setup_logging, get_logger
from pathfinder_pkg.navigation.map import OccupancyGridMap
from pathfinder_pkg.navigation.localization import Pose
from pathfinder_pkg.navigation.slam.slam import SLAM
from pathfinder_pkg.navigation.behaviors.navigator import NavigationController
from pathfinder_pkg.web.server import WebInterface
from pathfinder_pkg.sensors.robot_controller import RobotController

# Initialize logger
logger = get_logger(__name__)


class PathfinderBot:
    """
    Main class for the PathfinderBot system.

    This class initializes and connects all the major components of the system,
    including navigation, sensors, and the web interface.
    """

    def __init__(
        self,
        map_resolution: float = 0.05,  # 5 cm per cell
        map_width: int = 400,  # 20m x 20m map
        map_height: int = 400,
        web_host: str = "0.0.0.0",
        web_port: int = 5000,
        config_file: Optional[str] = None,
    ):
        """
        Initialize the PathfinderBot system.

        Args:
            map_resolution: Resolution of the occupancy grid map (meters per cell)
            map_width: Width of the map in cells
            map_height: Height of the map in cells
            web_host: Host address for the web server
            web_port: Port for the web server
            config_file: Path to configuration file (optional)
        """
        self.config_file = config_file
        self.web_host = web_host
        self.web_port = web_port

        # Initialize components
        logger.info("Initializing PathfinderBot components...")

        # Initialize robot hardware controller
        self.robot_controller = self._init_robot_controller()

        # Initialize map
        self.grid_map = OccupancyGridMap(
            width=map_width, height=map_height, resolution=map_resolution
        )

        # Initialize SLAM
        self.slam = SLAM(grid_map=self.grid_map, robot_controller=self.robot_controller)

        # Initialize navigation controller
        self.nav_controller = NavigationController(
            slam_system=self.slam,
            robot_controller=self.robot_controller,
            default_planner="a_star",
            planning_rate=1.0,  # 1 Hz
            control_rate=10.0,  # 10 Hz
        )

        # Initialize web interface
        self.web_interface = WebInterface(
            slam_system_instance=self.slam,
            navigation_controller=self.nav_controller,
            robot_ctrl=self.robot_controller,
            host=self.web_host,
            port=self.web_port,
        )

        # Set up signal handlers
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

        logger.info("PathfinderBot initialization complete")

    def _init_robot_controller(self) -> RobotController:
        """
        Initialize the robot hardware controller.

        Returns:
            Initialized robot controller
        """
        logger.info("Initializing robot hardware controller")
        try:
            # Load configuration if available
            config = {}
            if self.config_file and os.path.exists(self.config_file):
                import json

                with open(self.config_file, "r") as f:
                    config = json.load(f)

            # Initialize robot controller with configuration
            controller = RobotController(**config)
            logger.info("Robot controller initialized successfully")
            return controller

        except Exception as e:
            logger.error(f"Failed to initialize robot controller: {e}")
            logger.warning("Falling back to simulated robot controller")

            # Fall back to simulated controller
            from pathfinder_pkg.sensors.simulated_controller import (
                SimulatedRobotController,
            )

            return SimulatedRobotController()

    def start(self):
        """Start the PathfinderBot system."""
        logger.info("Starting PathfinderBot system")

        try:
            # Start robot controller
            if hasattr(self.robot_controller, "start"):
                self.robot_controller.start()

            # Start SLAM system
            self.slam.start()

            # Start web interface (this call is blocking)
            self.web_interface.start()

        except Exception as e:
            logger.error(f"Error starting PathfinderBot: {e}")
            self.stop()
            sys.exit(1)

    def stop(self):
        """Stop the PathfinderBot system."""
        logger.info("Stopping PathfinderBot system")

        try:
            # Stop web interface
            if hasattr(self.web_interface, "stop"):
                self.web_interface.stop()

            # Stop SLAM system
            if hasattr(self.slam, "stop"):
                self.slam.stop()

            # Stop robot controller
            if hasattr(self.robot_controller, "stop"):
                self.robot_controller.stop()

        except Exception as e:
            logger.error(f"Error stopping PathfinderBot: {e}")

    def _signal_handler(self, sig, frame):
        """Handle termination signals."""
        logger.info(f"Received signal {sig}, shutting down")
        self.stop()
        sys.exit(0)


def parse_arguments():
    """
    Parse command line arguments.

    Returns:
        Parsed arguments
    """
    parser = argparse.ArgumentParser(description="PathfinderBot robotic system")

    parser.add_argument(
        "--map-resolution",
        type=float,
        default=0.05,
        help="Map resolution in meters per cell",
    )
    parser.add_argument("--map-width", type=int, default=400, help="Map width in cells")
    parser.add_argument(
        "--map-height", type=int, default=400, help="Map height in cells"
    )
    parser.add_argument(
        "--web-host",
        type=str,
        default="0.0.0.0",
        help="Host address for the web server",
    )
    parser.add_argument(
        "--web-port", type=int, default=5000, help="Port for the web server"
    )
    parser.add_argument(
        "--config", type=str, default=None, help="Path to configuration file"
    )
    parser.add_argument(
        "--log-level",
        type=str,
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        help="Logging level",
    )
    parser.add_argument("--log-file", type=str, default=None, help="Log file path")

    return parser.parse_args()


def main():
    """Main entry point for PathfinderBot."""
    # Parse command line arguments
    args = parse_arguments()

    # Setup logging
    setup_logging(level=args.log_level, log_file=args.log_file)

    # Create and start PathfinderBot
    bot = PathfinderBot(
        map_resolution=args.map_resolution,
        map_width=args.map_width,
        map_height=args.map_height,
        web_host=args.web_host,
        web_port=args.web_port,
        config_file=args.config,
    )

    # Start the system
    bot.start()


if __name__ == "__main__":
    main()
