#!/usr/bin/env python3
"""
Test script for PathfinderBot performance optimizations.
This script initializes all of the performance optimization components
and provides a simple way to test their functionality.
"""

import time
import logging
import os
import sys
import threading
import signal
from pathlib import Path

# Add parent directory to path to import from pathfinder_pkg
sys.path.append(str(Path(__file__).parent))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("logs/performance_test.log", mode="w"),
    ],
)

# Create logs directory if it doesn't exist
os.makedirs("logs", exist_ok=True)

logger = logging.getLogger("performance_test")

try:
    # Import PathfinderBot components
    from pathfinder_pkg.utils.performance import (
        start_monitoring,
        PerformanceTimer,
        get_performance_monitor,
    )

    from pathfinder_pkg.web.server import WebInterface
    from pathfinder_pkg.web.websocket import RobotWebSocketServer
except ImportError as e:
    logger.error(f"Error importing components: {e}")
    logger.error(
        "Make sure you're running from the correct directory and all dependencies are installed"
    )
    sys.exit(1)


# Mock classes for testing without actual robot hardware
class MockRobotController:
    """Mock robot controller for testing."""

    def __init__(self):
        self.speed = 0
        self.rotation = 0
        self.battery_level = 85
        self.charging = False

    def set_velocity(self, linear, angular):
        """Set robot velocity."""
        self.speed = linear
        self.rotation = angular
        logger.info(f"Set velocity: linear={linear}, angular={angular}")
        return True

    def get_battery_level(self):
        """Get battery level."""
        return {"level": self.battery_level, "charging": self.charging}

    def get_sonar_readings(self):
        """Get sonar sensor readings."""
        return [random_value(0, 100) for _ in range(4)]

    def get_camera_status(self):
        """Get camera status."""
        return {"connected": True, "resolution": "640x480", "fps": 30}

    def get_imu_data(self):
        """Get IMU data."""
        return {
            "accelerometer": {
                "x": random_value(-1, 1),
                "y": random_value(-1, 1),
                "z": random_value(0, 1),
            },
            "gyroscope": {
                "x": random_value(-1, 1),
                "y": random_value(-1, 1),
                "z": random_value(-1, 1),
            },
        }


class MockSLAM:
    """Mock SLAM system for testing."""

    def __init__(self):
        self.pose = {"x": 0, "y": 0, "theta": 0}
        self.map_data = None

    def get_pose(self):
        """Get current pose."""
        return MockPose(self.pose["x"], self.pose["y"], self.pose["theta"])

    def get_map(self):
        """Get occupancy grid map."""
        return MockGridMap(10, 10, 0.1)


class MockPose:
    """Mock pose for testing."""

    def __init__(self, x, y, theta):
        self.x = x
        self.y = y
        self.theta = theta


class MockGridMap:
    """Mock occupancy grid map for testing."""

    def __init__(self, width, height, resolution):
        self.width = width
        self.height = height
        self.resolution = resolution
        self.origin_x = 0
        self.origin_y = 0
        self.grid = [[0 for _ in range(width)] for _ in range(height)]

    def get_grid(self):
        """Get grid data."""
        import numpy as np

        return np.array(self.grid)


class MockNavigationController:
    """Mock navigation controller for testing."""

    def __init__(self):
        self.goal_pose = None
        self.current_path = []
        self.navigation_status = MockEnum("IDLE")

    def cancel(self):
        """Cancel navigation."""
        logger.info("Navigation cancelled")
        return True


class MockEnum:
    """Mock enum for testing."""

    def __init__(self, name):
        self.name = name


def random_value(min_val, max_val):
    """Generate a random value between min_val and max_val."""
    import random

    return min_val + random.random() * (max_val - min_val)


def test_performance_timer():
    """Test the performance timer."""
    logger.info("Testing PerformanceTimer...")

    # Test timer with different operations
    with PerformanceTimer("operation1"):
        time.sleep(0.1)

    with PerformanceTimer("operation2"):
        time.sleep(0.2)

    # Get timing results
    timers = PerformanceTimer.get_all_timers()
    for name, stats in timers.items():
        logger.info(f"Timer {name}: {stats}")

    logger.info("PerformanceTimer test complete")


def simulate_load(duration=10, cpu_target=50):
    """
    Simulate CPU load for testing.

    Args:
        duration: Duration in seconds
        cpu_target: Target CPU usage percentage
    """
    logger.info(f"Simulating {cpu_target}% CPU load for {duration} seconds...")

    end_time = time.time() + duration
    while time.time() < end_time:
        # Calculate work/sleep ratio to hit target CPU
        work_time = 0.01 * cpu_target / 100
        sleep_time = 0.01 * (1 - cpu_target / 100)

        # Do some meaningless work to consume CPU
        start = time.time()
        while time.time() - start < work_time:
            _ = [i**2 for i in range(1000)]

        # Sleep to reduce CPU usage
        time.sleep(sleep_time)


def main():
    """Main test function."""
    logger.info("Starting PathfinderBot performance test")

    # Initialize performance monitoring
    logger.info("Initializing performance monitoring...")
    perf_monitor = start_monitoring(
        sample_interval=0.5, buffer_size=100, metrics_file="logs/metrics.json"
    )

    # Test performance timer
    test_performance_timer()

    # Create mock components
    logger.info("Creating mock components...")
    robot_controller = MockRobotController()
    slam_system = MockSLAM()
    nav_controller = MockNavigationController()

    # Initialize WebSocket server
    logger.info("Initializing WebSocket server...")
    ws_server = RobotWebSocketServer(
        robot=robot_controller, host="localhost", port=8765
    )

    # Register custom handler
    def echo_handler(data):
        """Echo handler for testing."""
        return {"status": "ok", "echo": data}

    ws_server.register_handler("echo", echo_handler)

    # Start WebSocket server
    ws_server.start()

    # Initialize web interface
    logger.info("Initializing web interface...")
    web_interface = WebInterface(
        slam_system_instance=slam_system,
        navigation_controller=nav_controller,
        robot_ctrl=robot_controller,
        host="localhost",
        port=5000,
        ws_port=8765,
        debug=True,
    )

    # Start web interface in a separate thread
    web_thread = threading.Thread(target=web_interface.start)
    web_thread.daemon = True
    web_thread.start()

    logger.info("Web interface started at http://localhost:5000")
    logger.info("WebSocket server running at ws://localhost:8765")

    # Start telemetry
    ws_server.start_telemetry(0.2)

    # Register a callback to log performance metrics
    def log_performance():
        """Log performance metrics."""
        cpu = perf_monitor.get_metric_recent_average("cpu_usage")
        mem = perf_monitor.get_metric_recent_average("memory_usage")
        if cpu and mem:
            logger.info(f"Performance: CPU {cpu:.1f}%, Memory {mem:.1f}%")

    perf_monitor.register_callback("metrics_logger", log_performance)

    # Simulate different load scenarios
    try:
        logger.info("Running load simulation scenarios...")

        # Normal load
        simulate_load(duration=5, cpu_target=30)

        # Heavy load
        simulate_load(duration=5, cpu_target=70)

        # Normal load again
        simulate_load(duration=5, cpu_target=30)

        # Get and log metrics summary
        metrics = perf_monitor.get_metrics_summary()
        logger.info("Performance metrics summary:")
        for name, data in metrics["metrics"].items():
            if "current" in data and data["current"] is not None:
                logger.info(
                    f"  {name}: {data['current']:.2f} (avg: {data['average']:.2f})"
                )

        logger.info("Performance test complete")
        logger.info("Press Ctrl+C to exit")

        # Keep running until interrupted
        signal.pause()

    except KeyboardInterrupt:
        logger.info("Test interrupted by user")

    finally:
        # Clean up
        logger.info("Stopping services...")
        web_interface.stop()
        ws_server.stop()

        logger.info("Performance test finished")


if __name__ == "__main__":
    main()
