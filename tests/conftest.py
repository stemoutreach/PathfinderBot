"""
pytest configuration for PathfinderBot testing.

This file contains fixtures and configuration for the PathfinderBot test suite.
"""

import os
import sys
import pytest
import logging
from pathlib import Path

# Add the project root to the path so we can import from pathfinder_pkg
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

# Import PathfinderBot components
from pathfinder_pkg.utils.logging import setup_logging


@pytest.fixture(scope="session")
def setup_test_logging():
    """Set up logging for tests."""
    # Create logs directory if it doesn't exist
    logs_dir = project_root / "logs"
    logs_dir.mkdir(exist_ok=True)

    # Set up logging
    setup_logging(
        level="DEBUG",
        log_file=str(logs_dir / "test.log"),
    )

    yield

    # No teardown needed for logging


@pytest.fixture
def mock_robot_controller():
    """Fixture to provide a mock robot controller."""
    from pathfinder_pkg.sensors.simulated_controller import SimulatedRobotController

    # Create a simulated controller for testing
    controller = SimulatedRobotController()

    yield controller


@pytest.fixture
def mock_slam_system():
    """Fixture to provide a mock SLAM system."""

    # Create a simple mock class
    class MockSLAM:
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
            import numpy as np

            self.grid = np.zeros((height, width))

        def get_grid(self):
            """Get grid data."""
            return self.grid

    slam = MockSLAM()
    yield slam


@pytest.fixture
def mock_navigation_controller():
    """Fixture to provide a mock navigation controller."""

    # Create a simple mock class
    class MockNavigationController:
        def __init__(self):
            self.goal_pose = None
            self.current_path = []
            self.navigation_status = "IDLE"

        def cancel(self):
            """Cancel navigation."""
            return True

        def navigate_to(self, x, y, theta=None):
            """Navigate to a pose."""
            self.goal_pose = {"x": x, "y": y, "theta": theta}
            self.navigation_status = "NAVIGATING"
            return True

    controller = MockNavigationController()
    yield controller
