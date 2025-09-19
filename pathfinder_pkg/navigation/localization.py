"""
Localization module for PathfinderBot navigation.

This module provides classes for robot pose representation and localization
algorithms, including particle filter localization.
"""

import numpy as np
from typing import List, Tuple, Dict, Optional, Union, Any
import matplotlib.pyplot as plt
from dataclasses import dataclass
import math
import random

from pathfinder_pkg.utils.logging import get_logger
from pathfinder_pkg.navigation.map import OccupancyGridMap

logger = get_logger(__name__)


@dataclass
class Pose:
    """Representation of a 2D robot pose (position and orientation)."""

    x: float  # X position in meters
    y: float  # Y position in meters
    theta: float  # Orientation in radians

    def distance_to(self, other: "Pose") -> float:
        """Calculate the Euclidean distance to another pose."""
        return math.sqrt((self.x - other.x) ** 2 + (self.y - other.y) ** 2)

    def angle_to(self, other: "Pose") -> float:
        """Calculate the angle to another pose."""
        return math.atan2(other.y - self.y, other.x - self.x)

    def add_noise(self, position_noise: float, orientation_noise: float) -> "Pose":
        """Create a new pose with added Gaussian noise."""
        return Pose(
            x=self.x + np.random.normal(0, position_noise),
            y=self.y + np.random.normal(0, position_noise),
            theta=self.theta + np.random.normal(0, orientation_noise),
        )

    def __str__(self) -> str:
        """String representation of the pose."""
        return f"Pose(x={self.x:.2f}, y={self.y:.2f}, theta={math.degrees(self.theta):.1f}°)"


class ParticleFilter:
    """
    Particle filter localization algorithm.

    The particle filter represents the robot's belief about its position
    as a set of weighted particles (poses).
    """

    def __init__(
        self,
        num_particles: int = 100,
        position_sigma: float = 0.1,
        orientation_sigma: float = 0.1,
        initial_pose: Optional[Pose] = None,
    ):
        """
        Initialize the particle filter.

        Args:
            num_particles: Number of particles to use
            position_sigma: Standard deviation of position noise model (meters)
            orientation_sigma: Standard deviation of orientation noise model (radians)
            initial_pose: Initial pose estimate (if available)
        """
        self.num_particles = num_particles
        self.position_sigma = position_sigma
        self.orientation_sigma = orientation_sigma

        # Initialize particles
        self.particles = []
        self.weights = np.ones(num_particles) / num_particles  # Uniform initial weights

        self.best_pose = initial_pose
        self.initialized = initial_pose is not None

        logger.info(f"Initialized particle filter with {num_particles} particles")

    def initialize_uniform(self, map_obj: OccupancyGridMap) -> None:
        """
        Initialize particles uniformly across the map.

        Args:
            map_obj: Occupancy grid map
        """
        self.particles = []

        # Calculate map dimensions in world coordinates
        width_meters = map_obj.width * map_obj.resolution
        height_meters = map_obj.height * map_obj.resolution

        # Create particles with uniform distribution
        for _ in range(self.num_particles):
            x = map_obj.origin_x + random.uniform(0, width_meters)
            y = map_obj.origin_y + random.uniform(0, height_meters)
            theta = random.uniform(0, 2 * math.pi)

            # Only place particles in free space
            grid_x, grid_y = map_obj.world_to_grid(x, y)
            if 0 <= grid_x < map_obj.width and 0 <= grid_y < map_obj.height:
                if map_obj.is_free(grid_x, grid_y):
                    self.particles.append(Pose(x, y, theta))

        # If we couldn't place all particles, keep trying
        attempts = 0
        while len(self.particles) < self.num_particles and attempts < 1000:
            x = map_obj.origin_x + random.uniform(0, width_meters)
            y = map_obj.origin_y + random.uniform(0, height_meters)
            theta = random.uniform(0, 2 * math.pi)

            grid_x, grid_y = map_obj.world_to_grid(x, y)
            if 0 <= grid_x < map_obj.width and 0 <= grid_y < map_obj.height:
                if map_obj.is_free(grid_x, grid_y):
                    self.particles.append(Pose(x, y, theta))

            attempts += 1

        # If we still don't have enough particles, just place them randomly
        while len(self.particles) < self.num_particles:
            x = map_obj.origin_x + random.uniform(0, width_meters)
            y = map_obj.origin_y + random.uniform(0, height_meters)
            theta = random.uniform(0, 2 * math.pi)
            self.particles.append(Pose(x, y, theta))

        # Reset weights to uniform
        self.weights = np.ones(self.num_particles) / self.num_particles

        # Update best pose as centroid of particles
        self._update_best_pose()

        self.initialized = True
        logger.info(
            f"Initialized {self.num_particles} particles uniformly across the map"
        )

    def initialize_gaussian(
        self, initial_pose: Pose, position_sigma: float, orientation_sigma: float
    ) -> None:
        """
        Initialize particles with a Gaussian distribution around an initial pose.

        Args:
            initial_pose: Mean pose for initialization
            position_sigma: Standard deviation for position (meters)
            orientation_sigma: Standard deviation for orientation (radians)
        """
        self.particles = []

        for _ in range(self.num_particles):
            x = initial_pose.x + np.random.normal(0, position_sigma)
            y = initial_pose.y + np.random.normal(0, position_sigma)
            theta = initial_pose.theta + np.random.normal(0, orientation_sigma)

            # Normalize angle to [0, 2π)
            theta = theta % (2 * math.pi)

            self.particles.append(Pose(x, y, theta))

        # Reset weights to uniform
        self.weights = np.ones(self.num_particles) / self.num_particles

        # Set best pose
        self.best_pose = initial_pose

        self.initialized = True
        logger.info(
            f"Initialized {self.num_particles} particles with Gaussian distribution around {initial_pose}"
        )

    def predict(
        self,
        delta_pose: Pose,
        position_sigma: Optional[float] = None,
        orientation_sigma: Optional[float] = None,
    ) -> None:
        """
        Update particles based on motion model (prediction step).

        Args:
            delta_pose: Change in pose since last update
            position_sigma: Optional override for position noise
            orientation_sigma: Optional override for orientation noise
        """
        if not self.initialized:
            logger.warning(
                "Particle filter not initialized. Call initialize_uniform() or initialize_gaussian() first."
            )
            return

        pos_sigma = (
            position_sigma if position_sigma is not None else self.position_sigma
        )
        ori_sigma = (
            orientation_sigma
            if orientation_sigma is not None
            else self.orientation_sigma
        )

        for i in range(len(self.particles)):
            # Apply motion model with noise
            dx = delta_pose.x
            dy = delta_pose.y
            dtheta = delta_pose.theta

            # Transform delta in robot coordinates to world coordinates
            current_theta = self.particles[i].theta
            world_dx = dx * math.cos(current_theta) - dy * math.sin(current_theta)
            world_dy = dx * math.sin(current_theta) + dy * math.cos(current_theta)

            # Add noise proportional to movement
            motion_pos_sigma = pos_sigma * math.sqrt(dx**2 + dy**2)
            motion_ori_sigma = ori_sigma * abs(dtheta)

            # Apply noisy motion to particle
            self.particles[i].x += world_dx + np.random.normal(0, motion_pos_sigma)
            self.particles[i].y += world_dy + np.random.normal(0, motion_pos_sigma)
            self.particles[i].theta += dtheta + np.random.normal(0, motion_ori_sigma)

            # Normalize angle to [0, 2π)
            self.particles[i].theta = self.particles[i].theta % (2 * math.pi)

        logger.debug("Particle filter prediction step completed")

    def update_from_landmarks(
        self,
        observed_landmarks: Dict[str, Tuple[float, float]],
        map_obj: OccupancyGridMap,
    ) -> None:
        """
        Update particle weights based on landmark observations (correction step).

        Args:
            observed_landmarks: Dictionary of landmark_id -> (range, bearing) tuples
            map_obj: Occupancy grid map containing landmark positions
        """
        if not self.initialized:
            logger.warning(
                "Particle filter not initialized. Call initialize_uniform() or initialize_gaussian() first."
            )
            return

        if not observed_landmarks:
            logger.debug("No landmarks observed, skipping update step")
            return

        # Get landmark positions from map
        map_landmarks = map_obj.metadata.get("landmarks", {})

        # Calculate weights for each particle
        new_weights = np.zeros(self.num_particles)

        for i, particle in enumerate(self.particles):
            particle_weight = 1.0

            for landmark_id, (obs_range, obs_bearing) in observed_landmarks.items():
                # Skip if landmark not in map
                if landmark_id not in map_landmarks:
                    continue

                # Get landmark position
                landmark_x = map_landmarks[landmark_id]["x"]
                landmark_y = map_landmarks[landmark_id]["y"]

                # Calculate expected range and bearing
                dx = landmark_x - particle.x
                dy = landmark_y - particle.y
                expected_range = math.sqrt(dx**2 + dy**2)
                expected_bearing = (math.atan2(dy, dx) - particle.theta) % (2 * math.pi)

                # Normalize bearing difference to [-π, π]
                bearing_diff = (obs_bearing - expected_bearing + math.pi) % (
                    2 * math.pi
                ) - math.pi

                # Calculate likelihood using Gaussian sensor model
                range_error = obs_range - expected_range
                range_likelihood = math.exp(
                    -0.5 * (range_error / 0.5) ** 2
                )  # σ = 0.5m for range
                bearing_likelihood = math.exp(
                    -0.5 * (bearing_diff / 0.1) ** 2
                )  # σ = 0.1rad for bearing

                # Update particle weight
                particle_weight *= range_likelihood * bearing_likelihood

            new_weights[i] = particle_weight

        # Normalize weights
        if np.sum(new_weights) > 0:
            self.weights = new_weights / np.sum(new_weights)
        else:
            # If all weights are zero, reset to uniform
            self.weights = np.ones(self.num_particles) / self.num_particles
            logger.warning("All particle weights are zero, reset to uniform")

        # Resample if effective number of particles is too low
        n_eff = 1.0 / np.sum(np.square(self.weights))
        if n_eff < self.num_particles / 2:
            self._resample()

        # Update best pose
        self._update_best_pose()

        logger.debug("Particle filter update from landmarks completed")

    def update_from_scan(
        self, scan: np.ndarray, angles: np.ndarray, map_obj: OccupancyGridMap
    ) -> None:
        """
        Update particle weights based on range scan observations (correction step).

        Args:
            scan: Array of range measurements
            angles: Array of corresponding angles
            map_obj: Occupancy grid map
        """
        if not self.initialized:
            logger.warning(
                "Particle filter not initialized. Call initialize_uniform() or initialize_gaussian() first."
            )
            return

        # Calculate weights for each particle
        new_weights = np.zeros(self.num_particles)

        for i, particle in enumerate(self.particles):
            particle_weight = 1.0
            valid_beams = 0

            for j, (range_measurement, angle) in enumerate(zip(scan, angles)):
                # Skip invalid measurements
                if (
                    range_measurement <= 0
                    or math.isnan(range_measurement)
                    or math.isinf(range_measurement)
                ):
                    continue

                # Calculate expected range by ray casting in the map
                expected_range = self._ray_cast(
                    particle, angle, map_obj, max_range=10.0
                )

                if expected_range is not None:
                    # Calculate likelihood using Gaussian sensor model
                    range_error = range_measurement - expected_range
                    likelihood = math.exp(
                        -0.5 * (range_error / 0.2) ** 2
                    )  # σ = 0.2m for range

                    # Update particle weight
                    particle_weight *= likelihood
                    valid_beams += 1

            # Only consider particles with sufficient valid beams
            if valid_beams >= 5:
                new_weights[i] = particle_weight
            else:
                new_weights[i] = 1e-10  # Very small but non-zero

        # Normalize weights
        if np.sum(new_weights) > 0:
            self.weights = new_weights / np.sum(new_weights)
        else:
            # If all weights are zero, reset to uniform
            self.weights = np.ones(self.num_particles) / self.num_particles
            logger.warning("All particle weights are zero, reset to uniform")

        # Resample if effective number of particles is too low
        n_eff = 1.0 / np.sum(np.square(self.weights))
        if n_eff < self.num_particles / 2:
            self._resample()

        # Update best pose
        self._update_best_pose()

        logger.debug("Particle filter update from scan completed")

    def _ray_cast(
        self, pose: Pose, angle: float, map_obj: OccupancyGridMap, max_range: float
    ) -> Optional[float]:
        """
        Perform ray casting in the map to determine expected range measurement.

        Args:
            pose: Robot pose
            angle: Angle of the ray (in robot frame)
            map_obj: Occupancy grid map
            max_range: Maximum range to check

        Returns:
            Expected range or None if no obstacle found
        """
        # Convert angle to world frame
        world_angle = (pose.theta + angle) % (2 * math.pi)

        # Convert pose to grid coordinates
        start_x, start_y = map_obj.world_to_grid(pose.x, pose.y)

        # Check if starting position is valid
        if not (0 <= start_x < map_obj.width and 0 <= start_y < map_obj.height):
            return None

        # Calculate ray direction in grid coordinates
        dx = math.cos(world_angle)
        dy = math.sin(world_angle)

        # Convert max_range to grid cells
        max_cells = int(max_range / map_obj.resolution)

        # Bressenham line algorithm for ray casting
        x, y = start_x, start_y

        # Calculate step sizes and initial error
        step_x = 1 if dx > 0 else -1 if dx < 0 else 0
        step_y = 1 if dy > 0 else -1 if dy < 0 else 0

        # Handle vertical and horizontal lines
        if dx == 0:
            for i in range(max_cells):
                y += step_y
                if not (0 <= y < map_obj.height) or map_obj.is_occupied(x, y):
                    # Convert back to world coordinates and calculate distance
                    hit_x, hit_y = map_obj.grid_to_world(x, y)
                    return math.sqrt((hit_x - pose.x) ** 2 + (hit_y - pose.y) ** 2)
            return None
        elif dy == 0:
            for i in range(max_cells):
                x += step_x
                if not (0 <= x < map_obj.width) or map_obj.is_occupied(x, y):
                    # Convert back to world coordinates and calculate distance
                    hit_x, hit_y = map_obj.grid_to_world(x, y)
                    return math.sqrt((hit_x - pose.x) ** 2 + (hit_y - pose.y) ** 2)
            return None
        else:
            # General case using Bresenham's algorithm
            dx_abs = abs(dx)
            dy_abs = abs(dy)

            if dx_abs > dy_abs:
                err = dx_abs / 2.0
                for i in range(max_cells):
                    x += step_x
                    err -= dy_abs
                    if err < 0:
                        y += step_y
                        err += dx_abs

                    if not (0 <= x < map_obj.width and 0 <= y < map_obj.height):
                        return max_range  # Ray goes out of map

                    if map_obj.is_occupied(x, y):
                        # Convert back to world coordinates and calculate distance
                        hit_x, hit_y = map_obj.grid_to_world(x, y)
                        return math.sqrt((hit_x - pose.x) ** 2 + (hit_y - pose.y) ** 2)
            else:
                err = dy_abs / 2.0
                for i in range(max_cells):
                    y += step_y
                    err -= dx_abs
                    if err < 0:
                        x += step_x
                        err += dy_abs

                    if not (0 <= x < map_obj.width and 0 <= y < map_obj.height):
                        return max_range  # Ray goes out of map

                    if map_obj.is_occupied(x, y):
                        # Convert back to world coordinates and calculate distance
                        hit_x, hit_y = map_obj.grid_to_world(x, y)
                        return math.sqrt((hit_x - pose.x) ** 2 + (hit_y - pose.y) ** 2)

        return max_range  # No obstacle found within max range

    def _resample(self) -> None:
        """
        Resample particles based on their weights using low-variance resampling.
        """
        new_particles = []
        r = random.uniform(0, 1.0 / self.num_particles)
        c = self.weights[0]
        i = 0

        for m in range(self.num_particles):
            u = r + m / self.num_particles
            while u > c:
                i += 1
                c += self.weights[i]
            new_particles.append(
                Pose(self.particles[i].x, self.particles[i].y, self.particles[i].theta)
            )

        self.particles = new_particles
        self.weights = np.ones(self.num_particles) / self.num_particles

        logger.debug("Resampled particles")

    def _update_best_pose(self) -> None:
        """
        Update the best pose estimate as weighted average of particles.
        """
        if not self.particles:
            return

        # Get the highest weight particle
        best_idx = np.argmax(self.weights)
        best_particle = self.particles[best_idx]

        # For orientation, we need to handle the circular nature
        sin_sum = 0
        cos_sum = 0

        for i, particle in enumerate(self.particles):
            weight = self.weights[i]
            sin_sum += weight * math.sin(particle.theta)
            cos_sum += weight * math.cos(particle.theta)

        avg_theta = math.atan2(sin_sum, cos_sum)

        # Use weighted average for position
        avg_x = np.sum([p.x * w for p, w in zip(self.particles, self.weights)])
        avg_y = np.sum([p.y * w for p, w in zip(self.particles, self.weights)])

        # Update best pose
        self.best_pose = Pose(avg_x, avg_y, avg_theta)

    def get_pose(self) -> Optional[Pose]:
        """
        Get the current best pose estimate.

        Returns:
            Current best pose estimate or None if not initialized
        """
        return self.best_pose

    def get_pose_covariance(self) -> Optional[np.ndarray]:
        """
        Calculate the covariance matrix of the pose estimate.

        Returns:
            3x3 covariance matrix [x, y, theta] or None if not initialized
        """
        if not self.initialized or not self.particles:
            return None

        poses = np.array([[p.x, p.y, p.theta] for p in self.particles])
        mean_pose = np.array([self.best_pose.x, self.best_pose.y, self.best_pose.theta])

        # Handle circular mean for theta
        poses[:, 2] = (
            (poses[:, 2] - self.best_pose.theta + math.pi) % (2 * math.pi)
            - math.pi
            + self.best_pose.theta
        )

        # Calculate weighted covariance
        cov = np.zeros((3, 3))
        for i in range(self.num_particles):
            diff = poses[i] - mean_pose
            cov += self.weights[i] * np.outer(diff, diff)

        return cov

    def visualize(self, ax=None, show: bool = True):
        """
        Visualize the particle filter state.

        Args:
            ax: Matplotlib axes to plot on
            show: Whether to show the plot

        Returns:
            Matplotlib axes object
        """
        if not self.initialized:
            logger.warning("Particle filter not initialized, nothing to visualize")
            return None

        if ax is None:
            fig, ax = plt.subplots(figsize=(8, 8))

        # Plot particles
        xs = [p.x for p in self.particles]
        ys = [p.y for p in self.particles]

        # Scale particle markers by weight
        sizes = 10 + 100 * self.weights
        ax.scatter(xs, ys, s=sizes, alpha=0.5, color="blue", label="Particles")

        # Plot best pose
        if self.best_pose:
            ax.plot(
                self.best_pose.x,
                self.best_pose.y,
                "ro",
                markersize=10,
                label="Best Estimate",
            )

            # Draw orientation arrow
            arrow_len = 0.5
            dx = arrow_len * math.cos(self.best_pose.theta)
            dy = arrow_len * math.sin(self.best_pose.theta)
            ax.arrow(
                self.best_pose.x,
                self.best_pose.y,
                dx,
                dy,
                head_width=0.1,
                head_length=0.2,
                fc="r",
                ec="r",
            )

        ax.set_xlabel("X (meters)")
        ax.set_ylabel("Y (meters)")
        ax.set_title("Particle Filter Localization")
        ax.legend()

        # Try to keep aspect ratio equal
        ax.set_aspect("equal")

        if show:
            plt.tight_layout()
            plt.show()

        return ax
