#!/usr/bin/env python3
"""
PathfinderBot main entry point script.

This script serves as the main entry point for running the PathfinderBot package.
It provides a command-line interface to start different components of the system.

Examples:
    # Start the web interface
    python -m pathfinder_pkg.run --web

    # Start the robot with apriltag navigation
    python -m pathfinder_pkg.run --apriltag-nav

    # Start the robot with block detection
    python -m pathfinder_pkg.run --block-detection

    # Start the robot with a demo sequence
    python -m pathfinder_pkg.run --demo
"""

import argparse
import sys
import logging
from pathfinder_pkg.utils.logging import setup_logging

# Setup logging
logger = setup_logging(__name__)


def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="PathfinderBot Command Line Interface")

    # Main operation modes
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--web", action="store_true", help="Start the web interface")
    group.add_argument(
        "--apriltag-nav",
        action="store_true",
        help="Start the robot with AprilTag navigation",
    )
    group.add_argument(
        "--block-detection",
        action="store_true",
        help="Start the robot with block detection",
    )
    group.add_argument(
        "--demo", action="store_true", help="Run a demonstration sequence"
    )
    group.add_argument(
        "--jupyter",
        action="store_true",
        help="Launch Jupyter notebook server for educational content",
    )

    # Additional options
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")
    parser.add_argument(
        "--sim",
        action="store_true",
        help="Run in simulation mode (no hardware required)",
    )

    return parser.parse_args()


def main():
    """Main entry point function."""
    args = parse_arguments()

    # Set logging level
    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)
        logger.debug("Debug logging enabled")

    # Check if simulation mode is enabled
    sim_mode = args.sim
    if sim_mode:
        logger.info("Running in simulation mode")

    try:
        # Run the selected mode
        if args.web:
            from pathfinder_pkg.web.server import start_server

            logger.info("Starting web interface")
            start_server(simulation=sim_mode)

        elif args.apriltag_nav:
            from pathfinder_pkg.navigation.apriltag_navigator import (
                start_apriltag_navigation,
            )

            logger.info("Starting AprilTag navigation")
            start_apriltag_navigation(simulation=sim_mode)

        elif args.block_detection:
            from pathfinder_pkg.detectors.block_detector import run_block_detection

            logger.info("Starting block detection")
            run_block_detection(simulation=sim_mode)

        elif args.demo:
            from pathfinder_pkg.core.demo import run_demo

            logger.info("Running demonstration sequence")
            run_demo(simulation=sim_mode)

        elif args.jupyter:
            import subprocess
            import os

            logger.info("Launching Jupyter notebook server")
            # Get the examples directory
            examples_dir = os.path.join(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                "pathfinder_pkg",
                "education",
                "examples",
            )

            # Launch Jupyter notebook server
            subprocess.run(
                [
                    "jupyter",
                    "notebook",
                    "--notebook-dir",
                    examples_dir,
                    "--ip",
                    "0.0.0.0",
                ]
            )

    except ImportError as e:
        logger.error(f"Failed to import required module: {e}")
        print(f"Error: {e}")
        print("Make sure you have installed all required dependencies. Run:")
        print("pip install -r requirements.txt")
        return 1

    except Exception as e:
        logger.error(f"An error occurred: {e}", exc_info=True)
        print(f"Error: {e}")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
