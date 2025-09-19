#!/usr/bin/env python3
"""
PathfinderBot Multi-Robot Coordination
=====================================

Main module for launching the coordination system.

Run with:
    python -m pathfinder_pkg.coordination
"""

import sys
import logging
import argparse
from .communication import CoordinationServer
from .ui import launch_dashboard

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("PathfinderCoordination")


def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="PathfinderBot Multi-Robot Coordination System"
    )

    parser.add_argument(
        "--port", type=int, default=9000, help="Server port (default: 9000)"
    )

    parser.add_argument(
        "--no-gui", action="store_true", help="Run server without GUI dashboard"
    )

    parser.add_argument("--debug", action="store_true", help="Enable debug logging")

    return parser.parse_args()


def main():
    """Main entry point for the coordination module."""
    args = parse_arguments()

    # Configure logging level
    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)
        logger.debug("Debug logging enabled")

    # Create and start the coordination server
    server = CoordinationServer(server_port=args.port)
    server.start()

    logger.info(f"Coordination server started on port {args.port}")

    try:
        # Launch dashboard if requested
        if not args.no_gui:
            logger.info("Launching coordination dashboard")
            launch_dashboard(server)
        else:
            logger.info("Running in headless mode (no GUI)")
            # Keep the server running until interrupted
            import time

            while True:
                time.sleep(1)
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
    finally:
        # Clean shutdown
        server.stop()
        logger.info("Coordination server stopped")

    return 0


if __name__ == "__main__":
    sys.exit(main())
