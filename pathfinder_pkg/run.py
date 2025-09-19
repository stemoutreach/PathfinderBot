#!/usr/bin/env python3
"""
Main entry point for running the PathfinderBot system.

This script initializes and runs the PathfinderBot system, including the robot,
web interface, WebSocket server, and other components.
"""

import os
import time
import threading
import argparse
from pathlib import Path
import logging
from pathfinder_pkg.utils.logging import get_logger, set_log_level
from pathfinder_pkg.core.robot import robot
from pathfinder_pkg.core.mecanum import MecanumChassis
from pathfinder_pkg.web.server import WebServer
from pathfinder_pkg.web.websocket import RobotWebSocketServer
from pathfinder_pkg.detectors.block_detector import EnhancedBlockDetector

# Set up logger
logger = get_logger(__name__)


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="PathfinderBot Control System")

    parser.add_argument(
        "--web-port", type=int, default=5000, help="Port for the web server"
    )

    parser.add_argument(
        "--ws-port", type=int, default=8765, help="Port for the WebSocket server"
    )

    parser.add_argument(
        "--host", type=str, default="0.0.0.0", help="Host address to bind servers to"
    )

    parser.add_argument("--debug", action="store_true", help="Enable debug mode")

    parser.add_argument(
        "--no-robot",
        action="store_true",
        help="Run without connecting to robot hardware",
    )

    parser.add_argument(
        "--log-level",
        type=str,
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        default="INFO",
        help="Set the logging level",
    )

    return parser.parse_args()


def init_robot(simulation_mode=False):
    """
    Initialize the robot.

    Args:
        simulation_mode (bool): Whether to run in simulation mode without hardware.

    Returns:
        The initialized robot instance.
    """
    try:
        # Initialize the robot
        robot.initialize()

        # Initialize mecanum drive
        chassis = MecanumChassis()
        robot.add_component("chassis", chassis)

        # Initialize block detector
        block_detector = EnhancedBlockDetector()
        robot.add_component("block_detector", block_detector)

        # Additional components would be initialized here

        logger.info("Robot initialization successful")
        return robot
    except Exception as e:
        logger.error(f"Error initializing robot: {e}")
        if not simulation_mode:
            raise
        logger.warning("Running in simulation mode due to robot initialization failure")
        return robot  # Return the robot instance even if initialization failed


def main():
    """Run the PathfinderBot system."""
    args = parse_args()

    # Set log level
    set_log_level("pathfinder_pkg", getattr(logging, args.log_level))

    # Set up additional logging to stderr for more visibility in debug mode
    if args.debug:
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
        console = logging.StreamHandler()
        console.setFormatter(formatter)

        root_logger = logging.getLogger("pathfinder_pkg")
        root_logger.addHandler(console)
        root_logger.setLevel(logging.DEBUG)

    logger.info("Starting PathfinderBot system")

    # Initialize the robot
    robot_instance = None
    if not args.no_robot:
        try:
            robot_instance = init_robot()
        except Exception as e:
            logger.error(f"Failed to initialize robot hardware: {e}")
            logger.warning("Continuing without robot hardware")

    # Initialize the WebSocket server
    ws_server = RobotWebSocketServer(
        robot=robot_instance, host=args.host, port=args.ws_port
    )
    ws_server.start()
    logger.info(f"WebSocket server started on {args.host}:{args.ws_port}")

    # Initialize the web server
    web_server = WebServer(
        host=args.host, port=args.web_port, robot=robot_instance, ws_server=ws_server
    )

    try:
        # Run the web server (this will block)
        logger.info(f"Web server starting on {args.host}:{args.web_port}")
        web_server.start(debug=args.debug)
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
    except Exception as e:
        logger.error(f"Error running web server: {e}")
    finally:
        # Clean up
        logger.info("Shutting down")
        if ws_server:
            ws_server.stop()

        if robot_instance:
            try:
                robot_instance.shutdown()
            except Exception as e:
                logger.error(f"Error shutting down robot: {e}")


if __name__ == "__main__":
    main()
