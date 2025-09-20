#!/usr/bin/env python3
"""
Script to run the PathfinderBot web server.
This script ensures the proper Python path setup.
"""

import os
import sys

# Add the parent directory to the Python path to allow importing pathfinder_pkg
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import and start the server
from pathfinder_pkg.web.server import start_server

if __name__ == "__main__":
    print("Starting PathfinderBot web server...")
    start_server(host="0.0.0.0", port=8000)
    print("Server started on http://0.0.0.0:8000")

    try:
        # Keep the main thread alive
        import time

        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("Server stopping...")
