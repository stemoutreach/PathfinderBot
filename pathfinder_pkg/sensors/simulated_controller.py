"""
Simulated robot controller for PathfinderBot.

This module provides a simulated version of the robot controller for development,
testing, and demonstration purposes.
"""

import time
import threading
import math
import random
import numpy as np
from typing import Dict, List, Tuple, Optional, Any

from pathfinder_pkg.utils.logging import get_logger
from pathfinder_pkg.sensors.robot_controller import RobotController

logger = get_logger(__name__)


class SimulatedRobotController(RobotController):
    """
    Simulated controller for the robot hardware.

    This class provides a simulated implementation of the RobotController
    interface for development, testing, and demonstration purposes.
    """

    def __init__(self, **kwargs):
        """
        Initialize the simulated robot controller.

        Args:
            **kwargs: Additional configuration parameters
        """
        logger.info("Initializing simulated robot controller")

        # Initialize state
        self._position = [0.0, 0.0, 0.0]  # x, y, theta in m and rad
        self._velocity = [0.0, 0.0]  # linear, angular in m/s and rad/s
        self._arm_position = [0.0, 0.0, 0.0, 0.0, 0.0]  # 5 joint angles in rad
        self._gripper_state = 0.0  # 0.0 = open, 1.0 = closed
        self._running = False
        self._lock = threading.RLock()

        # Simulated environment
        self._obstacles = []  # List of (x, y, radius) tuples
        self._map_size = (10.0, 10.0)  # Width and height in meters
        self._battery_level = 100.0  # Percentage
        self._battery_discharge_rate = 0.01  # Percentage per second
        self._last_update_time = time.time()

        # Set up some random obstacles
        for _ in range(5):
            x = random.uniform(1.0, self._map_size[0] - 1.0)
            y = random.uniform(1.0, self._map_size[1] - 1.0)
            radius = random.uniform(0.2, 0.5)
            self._obstacles.append((x, y, radius))

        # Simulation thread
        self._simulation_thread = None
        self._stop_simulation = threading.Event()

        logger.info("Simulated robot controller initialized")

    def start(self):
        """Start the simulated robot controller."""
        with self._lock:
            if self._running:
                logger.warning("Simulated robot controller already running")
                return

            logger.info("Starting simulated robot controller")
            self._running = True
            self._stop_simulation.clear()
            self._simulation_thread = threading.Thread(
                target=self._simulation_loop, daemon=True
            )
            self._simulation_thread.start()

    def stop(self):
        """Stop the simulated robot controller."""
        with self._lock:
            if not self._running:
                logger.warning("Simulated robot controller not running")
                return

            logger.info("Stopping simulated robot controller")
            self._running = False
            self._stop_simulation.set()

            if self._simulation_thread:
                self._simulation_thread.join(timeout=1.0)
                self._simulation_thread = None

    def _simulation_loop(self):
        """Background thread for running the simulation."""
        logger.info("Simulation loop started")

        update_interval = 0.05  # 20 Hz

        while not self._stop_simulation.is_set():
            try:
                # Update simulation
                self._update_simulation(update_interval)

                # Sleep until next update
                time.sleep(update_interval)

            except Exception as e:
                logger.error(f"Error in simulation loop: {e}")
                time.sleep(1.0)

        logger.info("Simulation loop stopped")

    def _update_simulation(self, dt):
        """
        Update the simulation state.

        Args:
            dt: Time step in seconds
        """
        with self._lock:
            # Update position based on velocity
            linear_vel, angular_vel = self._velocity
            theta = self._position[2]

            # Simple kinematics
            dx = linear_vel * math.cos(theta) * dt
            dy = linear_vel * math.sin(theta) * dt
            dtheta = angular_vel * dt

            # Update position
            self._position[0] += dx
            self._position[1] += dy
            self._position[2] = (self._position[2] + dtheta) % (2 * math.pi)

            # Constrain to map boundaries
            self._position[0] = max(0.0, min(self._position[0], self._map_size[0]))
            self._position[1] = max(0.0, min(self._position[1], self._map_size[1]))

            # Update battery level
            current_time = time.time()
            elapsed = current_time - self._last_update_time
            self._last_update_time = current_time

            # Battery discharges faster when moving
            discharge_factor = 1.0 + abs(linear_vel) + abs(angular_vel)
            self._battery_level -= (
                self._battery_discharge_rate * elapsed * discharge_factor
            )
            self._battery_level = max(0.0, min(self._battery_level, 100.0))

    def set_velocity(self, linear: float, angular: float) -> None:
        """
        Set the robot's velocity.

        Args:
            linear: Linear velocity in m/s (positive is forward)
            angular: Angular velocity in rad/s (positive is counter-clockwise)
        """
        with self._lock:
            # Update velocity
            self._velocity = [linear, angular]

    def set_arm_position(self, joint_angles: List[float]) -> None:
        """
        Set the arm joint positions.

        Args:
            joint_angles: List of joint angles in radians (5-DOF)
        """
        with self._lock:
            if len(joint_angles) != 5:
                raise ValueError("Expected 5 joint angles for 5-DOF arm")

            # Update arm position
            self._arm_position = joint_angles.copy()

    def get_sonar_readings(self) -> List[float]:
        """
        Get simulated readings from the sonar sensors.

        Returns:
            List of distances in meters, one for each sonar sensor
        """
        with self._lock:
            # Simulate 4 sonar sensors at 90-degree intervals
            readings = []

            # Robot position
            robot_x, robot_y, robot_theta = self._position

            # Sensor angles (front, right, back, left)
            sensor_angles = [0, math.pi / 2, math.pi, 3 * math.pi / 2]

            for angle in sensor_angles:
                # Sensor's absolute angle
                abs_angle = robot_theta + angle

                # Sensor direction vector
                dx = math.cos(abs_angle)
                dy = math.sin(abs_angle)

                # Find closest obstacle in this direction
                min_distance = 5.0  # Maximum sonar range

                # Check walls
                if dx > 0:
                    wall_dist = (self._map_size[0] - robot_x) / dx
                    min_distance = min(min_distance, wall_dist)
                elif dx < 0:
                    wall_dist = robot_x / -dx
                    min_distance = min(min_distance, wall_dist)

                if dy > 0:
                    wall_dist = (self._map_size[1] - robot_y) / dy
                    min_distance = min(min_distance, wall_dist)
                elif dy < 0:
                    wall_dist = robot_y / -dy
                    min_distance = min(min_distance, wall_dist)

                # Check obstacles
                for obs_x, obs_y, obs_radius in self._obstacles:
                    # Vector from robot to obstacle
                    to_obs_x = obs_x - robot_x
                    to_obs_y = obs_y - robot_y

                    # Distance to obstacle
                    dist_to_obs = math.sqrt(to_obs_x**2 + to_obs_y**2)

                    # Skip if obstacle is behind the sensor
                    if to_obs_x * dx + to_obs_y * dy < 0:
                        continue

                    # Project onto sensor ray
                    proj = to_obs_x * dx + to_obs_y * dy

                    # Distance from ray to obstacle center
                    perp_dist = math.sqrt(dist_to_obs**2 - proj**2)

                    # Skip if ray doesn't intersect obstacle
                    if perp_dist > obs_radius:
                        continue

                    # Calculate intersection point (using Pythagorean theorem)
                    intersect_dist = proj - math.sqrt(obs_radius**2 - perp_dist**2)

                    # Update minimum distance if this obstacle is closer
                    if intersect_dist > 0 and intersect_dist < min_distance:
                        min_distance = intersect_dist

                # Add some noise
                noise = random.gauss(0, 0.05)  # 5cm standard deviation
                reading = min_distance + noise
                readings.append(max(0.0, reading))

            return readings

    def get_camera_image(self) -> Optional[Any]:
        """
        Get a simulated camera image.

        Returns:
            Simulated image data
        """
        with self._lock:
            # For simulation purposes, we'll just return a placeholder
            # In a real implementation, this would be a numpy array or similar
            return "SIMULATED_CAMERA_IMAGE"

    def get_battery_level(self) -> Dict[str, Any]:
        """
        Get the simulated battery level.

        Returns:
            Dictionary with battery status information
        """
        with self._lock:
            return {
                "level": round(self._battery_level),
                "voltage": 12.0 - (12.0 - 9.0) * (1.0 - self._battery_level / 100.0),
                "charging": False,
            }

    def get_camera_status(self) -> Dict[str, Any]:
        """
        Get the status of the simulated camera.

        Returns:
            Dictionary with camera status information
        """
        with self._lock:
            return {"enabled": True, "resolution": "640x480", "fps": 30, "error": None}

    def get_imu_data(self) -> Dict[str, Any]:
        """
        Get simulated IMU data.

        Returns:
            Dictionary with IMU data
        """
        with self._lock:
            # Add some noise to the orientation
            roll_noise = random.gauss(0, 0.01)  # Small amount of noise
            pitch_noise = random.gauss(0, 0.01)
            yaw_noise = random.gauss(0, 0.01)

            # Calculate acceleration based on current velocity and orientation
            theta = self._position[2]
            linear_vel, angular_vel = self._velocity

            # Simulated acceleration due to gravity and motion
            acc_x = math.sin(roll_noise) * 9.81
            acc_y = -math.sin(pitch_noise) * 9.81
            acc_z = -math.cos(roll_noise) * math.cos(pitch_noise) * 9.81

            return {
                "accelerometer": {
                    "x": acc_x + random.gauss(0, 0.05),
                    "y": acc_y + random.gauss(0, 0.05),
                    "z": acc_z + random.gauss(0, 0.05),
                },
                "gyroscope": {
                    "x": random.gauss(0, 0.01),
                    "y": random.gauss(0, 0.01),
                    "z": self._velocity[1] + random.gauss(0, 0.01),
                },
                "orientation": {
                    "roll": roll_noise,
                    "pitch": pitch_noise,
                    "yaw": self._position[2] + yaw_noise,
                },
            }

    def get_position(self) -> Tuple[float, float, float]:
        """
        Get the current position of the robot in the simulation.

        This method is specific to the simulated controller and is not part
        of the standard RobotController interface.

        Returns:
            Tuple of (x, y, theta) in meters and radians
        """
        with self._lock:
            return tuple(self._position)

    def get_map_data(self) -> Dict[str, Any]:
        """
        Get the map data from the simulation.

        This method is specific to the simulated controller and is not part
        of the standard RobotController interface.

        Returns:
            Dictionary with map data
        """
        with self._lock:
            return {"size": self._map_size, "obstacles": self._obstacles}
