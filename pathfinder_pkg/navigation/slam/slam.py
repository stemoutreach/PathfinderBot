"""
SLAM (Simultaneous Localization and Mapping) implementation for PathfinderBot.

This module provides the core SLAM functionality that allows the robot to
build a map of its environment while simultaneously keeping track of its
position within the map.
"""

import numpy as np
import time
import math
from typing import Dict, List, Optional, Tuple, Union
import matplotlib.pyplot as plt
from dataclasses import dataclass, field
import logging
from pathlib import Path
import uuid

from pathfinder_pkg.utils.logging import get_logger
from pathfinder_pkg.navigation.map import OccupancyGridMap
from pathfinder_pkg.navigation.localization import Pose, ParticleFilter
from pathfinder_pkg.navigation.slam.feature_extraction import FeatureExtractor
from pathfinder_pkg.navigation.slam.loop_closure import LoopClosureDetector

logger = get_logger(__name__)


@dataclass
class MapUpdateParams:
    """Parameters for map update."""

    occupied_prob_update: float = 0.9  # Probability update for occupied cells
    free_prob_update: float = 0.1  # Probability update for free cells
    free_area_expansion: int = 1  # Expand free area around rays by this many cells
    max_range_limit: float = 10.0  # Maximum range to update map cells
    min_range_limit: float = 0.1  # Minimum range to update map cells
    update_cone_width: float = 0.05  # Width of the ray update cone in radians


class SLAM:
    """
    SLAM (Simultaneous Localization and Mapping) implementation.

    Combines particle filter localization with occupancy grid mapping to
    simultaneously build a map and track the robot's position.
    """

    def __init__(
        self,
        map_width: int = 500,
        map_height: int = 500,
        map_resolution: float = 0.05,
        particle_count: int = 100,
        init_pose: Optional[Pose] = None,
        map_update_params: Optional[MapUpdateParams] = None,
    ):
        """
        Initialize the SLAM system.

        Args:
            map_width: Width of the occupancy grid map in cells
            map_height: Height of the occupancy grid map in cells
            map_resolution: Resolution of the map in meters/cell
            particle_count: Number of particles for the particle filter
            init_pose: Initial robot pose, if available
            map_update_params: Parameters for map updates
        """
        # Create initial map
        self.map = OccupancyGridMap(
            width=map_width,
            height=map_height,
            resolution=map_resolution,
            origin_x=-map_width * map_resolution / 2,  # Center the map origin
            origin_y=-map_height * map_resolution / 2,
        )

        # Create particle filter for localization
        self.particle_filter = ParticleFilter(
            num_particles=particle_count,
            position_sigma=0.1,  # 10cm position noise
            orientation_sigma=0.05,  # ~3 degrees orientation noise
            initial_pose=init_pose,
        )

        # Initialize with Gaussian around initial pose if provided
        if init_pose:
            self.particle_filter.initialize_gaussian(
                initial_pose=init_pose,
                position_sigma=0.2,  # 20cm initial position uncertainty
                orientation_sigma=0.1,  # ~6 degrees initial orientation uncertainty
            )

            # Mark initial position as free in the map
            init_x, init_y = self.map.world_to_grid(init_pose.x, init_pose.y)
            self.map.update_cells_in_radius(init_x, init_y, 5, 0.1)  # Mark as free

        # Path history for visualization
        self.pose_history: List[Pose] = []
        if init_pose:
            self.pose_history.append(init_pose)

        # For loop closure detection
        self.loop_closure_detector = LoopClosureDetector()

        # Feature extractor for landmark detection
        self.feature_extractor = FeatureExtractor()

        # Map update parameters
        self.map_update_params = map_update_params or MapUpdateParams()

        # SLAM status
        self.initialized = init_pose is not None
        self.last_update_time = time.time()

        # Runtime statistics
        self.stats = {
            "updates": 0,
            "avg_update_time": 0.0,
            "loop_closures": 0,
            "landmarks_detected": 0,
        }

        logger.info(
            f"Initialized SLAM with {map_width}x{map_height} map at {map_resolution}m resolution"
        )

    def update(
        self,
        delta_pose: Optional[Pose] = None,
        scan: Optional[np.ndarray] = None,
        scan_angles: Optional[np.ndarray] = None,
        landmarks: Optional[Dict[str, Tuple[float, float]]] = None,
        robot_state: Optional[Dict] = None,
    ) -> Tuple[Optional[Pose], bool]:
        """
        Update the SLAM system with new sensor and odometry data.

        Args:
            delta_pose: Odometry-based pose change since last update
            scan: Array of range measurements from LiDAR or depth sensors
            scan_angles: Array of corresponding angles for the scan
            landmarks: Dictionary of detected landmarks with (range, bearing) values
            robot_state: Additional robot state information

        Returns:
            Tuple of (current_pose, updated) where updated is True if the map was updated
        """
        start_time = time.time()

        # If no delta pose is provided, assume the robot is stationary
        if delta_pose is None:
            delta_pose = Pose(0, 0, 0)

        # Initialize map if needed and we have scan data
        if not self.initialized and scan is not None and scan_angles is not None:
            # We need to initialize with an arbitrary pose since we don't have one
            init_pose = Pose(0, 0, 0)
            self.particle_filter.initialize_gaussian(
                initial_pose=init_pose,
                position_sigma=0.5,  # 50cm initial position uncertainty
                orientation_sigma=0.2,  # ~11 degrees initial orientation uncertainty
            )
            self.initialized = True
            self.pose_history.append(init_pose)

        # Return early if still not initialized
        if not self.initialized:
            logger.warning("SLAM not initialized, waiting for scan data")
            return None, False

        # Prediction step (motion model)
        self.particle_filter.predict(delta_pose)

        map_updated = False

        # Correction step with landmarks if available
        if landmarks and len(landmarks) > 0:
            self.particle_filter.update_from_landmarks(landmarks, self.map)
            self.stats["landmarks_detected"] += len(landmarks)

            # Update map with new landmark positions if they are new
            for landmark_id, (range_val, bearing) in landmarks.items():
                if landmark_id not in self.map.metadata["landmarks"]:
                    # Get current pose estimate
                    pose = self.particle_filter.get_pose()
                    if pose:
                        # Calculate landmark position in world coordinates
                        landmark_x = pose.x + range_val * math.cos(pose.theta + bearing)
                        landmark_y = pose.y + range_val * math.sin(pose.theta + bearing)

                        # Add to map
                        self.map.add_landmark(landmark_id, landmark_x, landmark_y)

            map_updated = True

        # Correction step with scan data if available
        if (
            scan is not None
            and scan_angles is not None
            and len(scan) == len(scan_angles)
        ):
            # Update particle weights based on scan
            self.particle_filter.update_from_scan(scan, scan_angles, self.map)

            # Get current pose estimate
            pose = self.particle_filter.get_pose()
            if pose:
                # Update map with new scan data
                self._update_map_with_scan(pose, scan, scan_angles)
                map_updated = True

        # Get the current pose estimate
        current_pose = self.particle_filter.get_pose()

        # Add to pose history
        if current_pose:
            self.pose_history.append(current_pose)

            # Limit history length to avoid memory issues
            if len(self.pose_history) > 1000:
                self.pose_history = self.pose_history[-1000:]

        # Check for loop closures periodically
        if (
            map_updated
            and len(self.pose_history) > 10
            and self.stats["updates"] % 10 == 0
        ):
            loop_closed = self._check_loop_closure()
            if loop_closed:
                self.stats["loop_closures"] += 1
                logger.info("Loop closure detected and processed")

        # Update statistics
        self.stats["updates"] += 1
        update_time = time.time() - start_time
        self.stats["avg_update_time"] = (
            self.stats["avg_update_time"] * (self.stats["updates"] - 1) + update_time
        ) / self.stats["updates"]

        self.last_update_time = time.time()

        return current_pose, map_updated

    def _update_map_with_scan(
        self, pose: Pose, scan: np.ndarray, scan_angles: np.ndarray
    ) -> None:
        """
        Update the occupancy grid map with new scan data.

        Args:
            pose: Current robot pose
            scan: Array of range measurements
            scan_angles: Array of corresponding angles
        """
        params = self.map_update_params

        # Get pose in grid coordinates
        grid_x, grid_y = self.map.world_to_grid(pose.x, pose.y)

        # Skip if pose is outside the map
        if not (0 <= grid_x < self.map.width and 0 <= grid_y < self.map.height):
            logger.warning(f"Robot pose ({pose.x}, {pose.y}) is outside the map bounds")
            return

        # Process each scan point
        for range_val, angle in zip(scan, scan_angles):
            # Skip invalid measurements
            if (
                range_val <= params.min_range_limit
                or range_val > params.max_range_limit
            ):
                continue

            # Calculate endpoint in world coordinates
            world_angle = pose.theta + angle
            end_x = pose.x + range_val * math.cos(world_angle)
            end_y = pose.y + range_val * math.sin(world_angle)

            # Convert to grid coordinates
            end_grid_x, end_grid_y = self.map.world_to_grid(end_x, end_y)

            # Skip if endpoint is outside the map
            if not (
                0 <= end_grid_x < self.map.width and 0 <= end_grid_y < self.map.height
            ):
                continue

            # Bresenham's line algorithm to trace the ray
            self._trace_ray(grid_x, grid_y, end_grid_x, end_grid_y, True)

            # Mark the endpoint as occupied
            self.map.update_cell(end_grid_x, end_grid_y, params.occupied_prob_update)

            # Mark cells around the endpoint as occupied with decreasing probability
            if params.free_area_expansion > 0:
                for r in range(1, params.free_area_expansion + 1):
                    prob_decrease = params.occupied_prob_update * (
                        1 - r / (params.free_area_expansion + 1)
                    )
                    for dx in range(-r, r + 1):
                        for dy in range(-r, r + 1):
                            if dx * dx + dy * dy <= r * r:  # Within circle of radius r
                                nx, ny = end_grid_x + dx, end_grid_y + dy
                                if (
                                    0 <= nx < self.map.width
                                    and 0 <= ny < self.map.height
                                ):
                                    current = self.map.get_cell(nx, ny)
                                    if current is not None:
                                        # Linear interpolation toward occupied
                                        self.map.update_cell(
                                            nx,
                                            ny,
                                            current
                                            + (params.occupied_prob_update - current)
                                            * prob_decrease,
                                        )

    def _trace_ray(
        self, x0: int, y0: int, x1: int, y1: int, mark_free: bool = True
    ) -> None:
        """
        Trace a ray from (x0, y0) to (x1, y1) and update cells along the ray.

        Args:
            x0, y0: Starting point in grid coordinates
            x1, y1: Ending point in grid coordinates
            mark_free: Whether to mark cells along the ray as free
        """
        free_prob = self.map_update_params.free_prob_update

        dx = abs(x1 - x0)
        dy = abs(y1 - y0)
        sx = 1 if x0 < x1 else -1
        sy = 1 if y0 < y1 else -1
        err = dx - dy

        x, y = x0, y0

        while x != x1 or y != y1:
            if mark_free and 0 <= x < self.map.width and 0 <= y < self.map.height:
                # Skip updating the start and end points
                if (x != x0 or y != y0) and (x != x1 or y != y1):
                    self.map.update_cell(x, y, free_prob)

            e2 = 2 * err
            if e2 > -dy:
                err -= dy
                x += sx
            if e2 < dx:
                err += dx
                y += sy

    def _check_loop_closure(self) -> bool:
        """
        Check for loop closures and update the map if a loop is detected.

        Returns:
            True if a loop closure was detected and processed
        """
        # We need a sufficient pose history to detect loops
        if len(self.pose_history) < 50:
            return False

        # Get current pose
        current_pose = self.pose_history[-1]

        # Check against poses from earlier in the trajectory
        # Skip the most recent poses (we're looking for loop closures)
        search_range = self.pose_history[:-20]

        # Search for a pose that is close to the current pose
        best_match_idx = -1
        best_match_dist = float("inf")

        for i, old_pose in enumerate(search_range):
            dist = current_pose.distance_to(old_pose)
            # Only consider poses that are close enough
            if dist < 1.0:  # Within 1 meter
                # Check angular difference as well
                angle_diff = abs(
                    (current_pose.theta - old_pose.theta + math.pi) % (2 * math.pi)
                    - math.pi
                )
                if angle_diff < 0.3:  # Within ~17 degrees
                    if dist < best_match_dist:
                        best_match_dist = dist
                        best_match_idx = i

        # If we found a good match, process the loop closure
        if best_match_idx >= 0:
            logger.info(f"Loop closure detected at distance {best_match_dist:.2f}m")

            # In a full implementation, we would:
            # 1. Adjust the particle filter
            # 2. Update the map based on the corrected poses
            # 3. Possibly run a graph optimization

            # For this simple implementation, we'll just mark the loop closure
            matched_pose = search_range[best_match_idx]

            # Mark the loop closure point in the map
            grid_x, grid_y = self.map.world_to_grid(current_pose.x, current_pose.y)
            self.map.update_cells_in_radius(
                grid_x, grid_y, 3, 0.5
            )  # Neutral probability

            return True

        return False

    def get_pose(self) -> Optional[Pose]:
        """
        Get the current robot pose estimate.

        Returns:
            Current pose estimate
        """
        return self.particle_filter.get_pose()

    def get_map(self) -> OccupancyGridMap:
        """
        Get the current occupancy grid map.

        Returns:
            Current map
        """
        return self.map

    def get_pose_covariance(self) -> Optional[np.ndarray]:
        """
        Get the covariance matrix of the current pose estimate.

        Returns:
            3x3 covariance matrix [x, y, theta] or None if not initialized
        """
        return self.particle_filter.get_pose_covariance()

    def save_map(self, filepath: Union[str, Path]) -> bool:
        """
        Save the current map to a file.

        Args:
            filepath: Path to save the map

        Returns:
            True if the save was successful, False otherwise
        """
        # Add current timestamp to metadata
        self.map.metadata["last_updated"] = time.strftime("%Y-%m-%d %H:%M:%S")
        if self.map.metadata["created"] is None:
            self.map.metadata["created"] = self.map.metadata["last_updated"]

        return self.map.save(filepath)

    @classmethod
    def load_map(cls, filepath: Union[str, Path]) -> Optional[OccupancyGridMap]:
        """
        Load a map from a file.

        Args:
            filepath: Path to the map file

        Returns:
            Loaded map or None if the load failed
        """
        return OccupancyGridMap.load(filepath)

    def visualize(
        self,
        ax=None,
        show_particles: bool = True,
        show_pose: bool = True,
        show_history: bool = True,
        show: bool = True,
    ):
        """
        Visualize the SLAM state, including map, pose, and particles.

        Args:
            ax: Matplotlib axes to plot on
            show_particles: Whether to show particles
            show_pose: Whether to show the current pose
            show_history: Whether to show the pose history
            show: Whether to show the plot

        Returns:
            Matplotlib axes object
        """
        if ax is None:
            fig, ax = plt.subplots(figsize=(10, 8))

        # Plot the map
        ax = self.map.visualize(ax=ax, show=False)

        # Plot particle filter if requested
        if show_particles and self.initialized:
            self.particle_filter.visualize(ax=ax, show=False)

        # Plot pose history if requested
        if show_history and self.pose_history:
            history_x = [p.x for p in self.pose_history]
            history_y = [p.y for p in self.pose_history]
            ax.plot(history_x, history_y, "b-", linewidth=1, alpha=0.5, label="Path")

        # Plot current pose if requested
        current_pose = self.get_pose()
        if show_pose and current_pose:
            ax.plot(
                current_pose.x, current_pose.y, "go", markersize=8, label="Current Pose"
            )

            # Draw orientation arrow
            arrow_len = 0.4
            dx = arrow_len * math.cos(current_pose.theta)
            dy = arrow_len * math.sin(current_pose.theta)
            ax.arrow(
                current_pose.x,
                current_pose.y,
                dx,
                dy,
                head_width=0.15,
                head_length=0.25,
                fc="g",
                ec="g",
            )

        ax.set_title("SLAM: Map and Robot Pose")

        # Add scale bar
        bar_length = 1.0  # 1 meter
        x_min, x_max = ax.get_xlim()
        y_min, y_max = ax.get_ylim()
        bar_x = x_min + (x_max - x_min) * 0.1
        bar_y = y_min + (y_max - y_min) * 0.05
        ax.plot([bar_x, bar_x + bar_length], [bar_y, bar_y], "k-", linewidth=3)
        ax.text(
            bar_x + bar_length / 2,
            bar_y - (y_max - y_min) * 0.02,
            f"{bar_length}m",
            horizontalalignment="center",
        )

        if show:
            plt.tight_layout()
            plt.show()

        return ax
