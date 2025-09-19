"""
Path planning module for PathfinderBot navigation.

This module provides the base path planner class and common functionality
for planning paths through the robot's environment.
"""

import numpy as np
from typing import List, Tuple, Dict, Optional, Union, Any
import math
import heapq
from abc import ABC, abstractmethod

from pathfinder_pkg.utils.logging import get_logger
from pathfinder_pkg.navigation.map import OccupancyGridMap
from pathfinder_pkg.navigation.localization import Pose

logger = get_logger(__name__)


class Waypoint:
    """
    Represents a waypoint in a path.

    A waypoint is a target position and orientation for the robot to reach.
    """

    def __init__(
        self,
        x: float,
        y: float,
        theta: Optional[float] = None,
        tolerance_position: float = 0.1,
        tolerance_angle: float = 0.1,
        action: str = "navigate",
        metadata: Optional[Dict[str, Any]] = None,
    ):
        """
        Initialize a waypoint.

        Args:
            x: X coordinate in world frame (meters)
            y: Y coordinate in world frame (meters)
            theta: Orientation in world frame (radians), optional
            tolerance_position: Position tolerance (meters)
            tolerance_angle: Orientation tolerance (radians)
            action: Action to perform at this waypoint (e.g., "navigate", "pickup", "place")
            metadata: Additional metadata for this waypoint
        """
        self.x = x
        self.y = y
        self.theta = theta
        self.tolerance_position = tolerance_position
        self.tolerance_angle = tolerance_angle
        self.action = action
        self.metadata = metadata or {}

    def __str__(self) -> str:
        """String representation of the waypoint."""
        if self.theta is not None:
            return f"Waypoint(x={self.x:.2f}, y={self.y:.2f}, theta={math.degrees(self.theta):.1f}°, action={self.action})"
        else:
            return f"Waypoint(x={self.x:.2f}, y={self.y:.2f}, action={self.action})"

    def distance_to(self, other: "Waypoint") -> float:
        """Calculate the Euclidean distance to another waypoint."""
        return math.sqrt((self.x - other.x) ** 2 + (self.y - other.y) ** 2)

    def angle_to(self, other: "Waypoint") -> float:
        """Calculate the angle to another waypoint."""
        return math.atan2(other.y - self.y, other.x - self.x)

    def is_reached(self, pose: Pose) -> bool:
        """Check if the waypoint is reached by the given pose."""
        # Check position
        position_reached = (
            math.sqrt((self.x - pose.x) ** 2 + (self.y - pose.y) ** 2)
            <= self.tolerance_position
        )

        # If no orientation specified, only check position
        if self.theta is None:
            return position_reached

        # Check orientation
        angle_diff = abs((pose.theta - self.theta + math.pi) % (2 * math.pi) - math.pi)
        orientation_reached = angle_diff <= self.tolerance_angle

        return position_reached and orientation_reached

    def to_pose(self) -> Pose:
        """Convert the waypoint to a Pose object."""
        return Pose(
            x=self.x, y=self.y, theta=self.theta if self.theta is not None else 0.0
        )


class PathPlanner(ABC):
    """
    Abstract base class for path planners.

    Path planners compute paths through the environment from a start pose to
    a goal pose while avoiding obstacles.
    """

    def __init__(self):
        """Initialize the path planner."""
        pass

    @abstractmethod
    def plan_path(
        self, map_data: OccupancyGridMap, start_pose: Pose, goal_pose: Pose, **kwargs
    ) -> List[Waypoint]:
        """
        Plan a path from the start pose to the goal pose.

        Args:
            map_data: Occupancy grid map of the environment
            start_pose: Starting pose of the robot
            goal_pose: Goal pose to reach
            **kwargs: Additional algorithm-specific parameters

        Returns:
            List of waypoints representing the planned path
        """
        pass

    def interpolate_path(
        self, path: List[Waypoint], max_segment_length: float = 0.2
    ) -> List[Waypoint]:
        """
        Interpolate a path to ensure waypoints are not too far apart.

        Args:
            path: Original path as a list of waypoints
            max_segment_length: Maximum distance between consecutive waypoints

        Returns:
            Interpolated path
        """
        if not path or len(path) < 2:
            return path

        interpolated_path = [path[0]]

        for i in range(1, len(path)):
            prev = path[i - 1]
            current = path[i]

            # Calculate distance between waypoints
            distance = prev.distance_to(current)

            # If distance is small enough, just add the current waypoint
            if distance <= max_segment_length:
                interpolated_path.append(current)
                continue

            # Otherwise, interpolate
            num_segments = math.ceil(distance / max_segment_length)
            dx = (current.x - prev.x) / num_segments
            dy = (current.y - prev.y) / num_segments

            # Add interpolated waypoints
            for j in range(1, num_segments):
                x = prev.x + j * dx
                y = prev.y + j * dy

                # If both waypoints have orientation, interpolate that too
                theta = None
                if prev.theta is not None and current.theta is not None:
                    # Ensure we interpolate along the shortest arc
                    diff = (current.theta - prev.theta + math.pi) % (
                        2 * math.pi
                    ) - math.pi
                    theta = (prev.theta + j * diff / num_segments) % (2 * math.pi)

                interpolated_path.append(
                    Waypoint(
                        x=x,
                        y=y,
                        theta=theta,
                        tolerance_position=prev.tolerance_position,
                        tolerance_angle=prev.tolerance_angle,
                        action="navigate",
                    )
                )

            # Add the current waypoint
            interpolated_path.append(current)

        return interpolated_path

    def smooth_path(
        self,
        path: List[Waypoint],
        weight_data: float = 0.5,
        weight_smooth: float = 0.1,
        tolerance: float = 0.00001,
    ) -> List[Waypoint]:
        """
        Smooth a path using gradient descent.

        Args:
            path: Original path as a list of waypoints
            weight_data: Weight for original data
            weight_smooth: Weight for smoothing
            tolerance: Convergence tolerance

        Returns:
            Smoothed path
        """
        if not path or len(path) < 3:
            return path

        # Make a deep copy of the path
        smoothed_path = [
            Waypoint(
                x=wp.x,
                y=wp.y,
                theta=wp.theta,
                tolerance_position=wp.tolerance_position,
                tolerance_angle=wp.tolerance_angle,
                action=wp.action,
                metadata=wp.metadata.copy() if wp.metadata else None,
            )
            for wp in path
        ]

        # Don't modify the first and last waypoints
        n_points = len(smoothed_path)

        # Extract x and y coordinates
        path_x = np.array([wp.x for wp in smoothed_path])
        path_y = np.array([wp.y for wp in smoothed_path])

        # Initialize change values
        change = tolerance + 1.0

        while change > tolerance:
            change = 0.0

            # Smooth all internal waypoints
            for i in range(1, n_points - 1):
                # Save original values
                orig_x, orig_y = path_x[i], path_y[i]

                # Update x
                path_x[i] += weight_data * (path[i].x - path_x[i])
                path_x[i] += weight_smooth * (
                    path_x[i - 1] + path_x[i + 1] - 2 * path_x[i]
                )

                # Update y
                path_y[i] += weight_data * (path[i].y - path_y[i])
                path_y[i] += weight_smooth * (
                    path_y[i - 1] + path_y[i + 1] - 2 * path_y[i]
                )

                # Calculate change for convergence check
                change += abs(path_x[i] - orig_x) + abs(path_y[i] - orig_y)

        # Update smoothed path with new coordinates
        for i in range(1, n_points - 1):
            smoothed_path[i].x = path_x[i]
            smoothed_path[i].y = path_y[i]

            # Update theta based on adjacent waypoints
            if i > 0 and i < n_points - 1:
                dx = smoothed_path[i + 1].x - smoothed_path[i - 1].x
                dy = smoothed_path[i + 1].y - smoothed_path[i - 1].y
                smoothed_path[i].theta = math.atan2(dy, dx)

        return smoothed_path

    def check_collision(
        self,
        map_data: OccupancyGridMap,
        path: List[Waypoint],
        robot_radius: float = 0.2,
    ) -> List[bool]:
        """
        Check for collisions along a path.

        Args:
            map_data: Occupancy grid map of the environment
            path: Path as a list of waypoints
            robot_radius: Radius of the robot in meters

        Returns:
            List of booleans indicating collision status for each waypoint
        """
        collision_status = []

        # Calculate robot radius in grid cells
        robot_radius_cells = int(robot_radius / map_data.resolution) + 1

        for waypoint in path:
            # Convert waypoint to grid coordinates
            grid_x, grid_y = map_data.world_to_grid(waypoint.x, waypoint.y)

            # Check if the waypoint is within map bounds
            if (
                grid_x < 0
                or grid_x >= map_data.width
                or grid_y < 0
                or grid_y >= map_data.height
            ):
                collision_status.append(True)  # Out of bounds counts as collision
                continue

            # Check if the waypoint itself is occupied
            if map_data.is_occupied(grid_x, grid_y):
                collision_status.append(True)
                continue

            # Check surrounding area within robot radius
            collision = False
            for dx in range(-robot_radius_cells, robot_radius_cells + 1):
                for dy in range(-robot_radius_cells, robot_radius_cells + 1):
                    # Skip points outside the circle
                    if dx * dx + dy * dy > robot_radius_cells * robot_radius_cells:
                        continue

                    # Check this grid cell
                    check_x, check_y = grid_x + dx, grid_y + dy
                    if 0 <= check_x < map_data.width and 0 <= check_y < map_data.height:
                        if map_data.is_occupied(check_x, check_y):
                            collision = True
                            break

                if collision:
                    break

            collision_status.append(collision)

        return collision_status


class SimplePlanner(PathPlanner):
    """
    A simple direct path planner that creates a straight-line path.

    This planner doesn't avoid obstacles and is mainly used for testing or
    in environments known to be obstacle-free.
    """

    def __init__(self):
        """Initialize the simple planner."""
        super().__init__()

    def plan_path(
        self, map_data: OccupancyGridMap, start_pose: Pose, goal_pose: Pose, **kwargs
    ) -> List[Waypoint]:
        """
        Plan a straight-line path from the start pose to the goal pose.

        Args:
            map_data: Occupancy grid map of the environment
            start_pose: Starting pose of the robot
            goal_pose: Goal pose to reach
            **kwargs: Additional parameters (ignored)

        Returns:
            List of waypoints representing the planned path
        """
        # Create start and end waypoints
        start_waypoint = Waypoint(
            x=start_pose.x, y=start_pose.y, theta=start_pose.theta, action="start"
        )

        goal_waypoint = Waypoint(
            x=goal_pose.x, y=goal_pose.y, theta=goal_pose.theta, action="goal"
        )

        # Create a simple path with just the start and goal
        path = [start_waypoint, goal_waypoint]

        # Interpolate to create a smoother path
        max_segment_length = kwargs.get("max_segment_length", 0.2)
        path = self.interpolate_path(path, max_segment_length)

        logger.info(
            f"Planned simple path with {len(path)} waypoints from ({start_pose.x:.2f}, {start_pose.y:.2f}) to ({goal_pose.x:.2f}, {goal_pose.y:.2f})"
        )

        return path


class PotentialFieldPlanner(PathPlanner):
    """
    A path planner using potential fields for obstacle avoidance.

    This planner uses attractive forces toward the goal and repulsive forces
    from obstacles to guide the robot around obstacles.
    """

    def __init__(self):
        """Initialize the potential field planner."""
        super().__init__()

    def plan_path(
        self, map_data: OccupancyGridMap, start_pose: Pose, goal_pose: Pose, **kwargs
    ) -> List[Waypoint]:
        """
        Plan a path using potential fields.

        Args:
            map_data: Occupancy grid map of the environment
            start_pose: Starting pose of the robot
            goal_pose: Goal pose to reach
            **kwargs: Additional parameters:
                - max_iterations: Maximum number of iterations
                - step_size: Step size for path generation
                - goal_weight: Weight of the attractive force
                - obstacle_weight: Weight of the repulsive force
                - obstacle_range: Range of influence of obstacles

        Returns:
            List of waypoints representing the planned path
        """
        # Get parameters
        max_iterations = kwargs.get("max_iterations", 1000)
        step_size = kwargs.get("step_size", 0.1)
        goal_weight = kwargs.get("goal_weight", 1.0)
        obstacle_weight = kwargs.get("obstacle_weight", 0.5)
        obstacle_range = kwargs.get("obstacle_range", 0.5)

        # Initialize path with start position
        path = [
            Waypoint(
                x=start_pose.x, y=start_pose.y, theta=start_pose.theta, action="start"
            )
        ]

        # Current position
        current_x, current_y = start_pose.x, start_pose.y

        # Iterate until we reach the goal or exceed max iterations
        iterations = 0
        goal_reached = False

        while iterations < max_iterations and not goal_reached:
            # Calculate distance to goal
            dist_to_goal = math.sqrt(
                (goal_pose.x - current_x) ** 2 + (goal_pose.y - current_y) ** 2
            )

            # Check if goal is reached
            if dist_to_goal < step_size:
                path.append(
                    Waypoint(
                        x=goal_pose.x,
                        y=goal_pose.y,
                        theta=goal_pose.theta,
                        action="goal",
                    )
                )
                goal_reached = True
                break

            # Calculate attractive force (normalized)
            attr_force_x = goal_weight * (goal_pose.x - current_x) / dist_to_goal
            attr_force_y = goal_weight * (goal_pose.y - current_y) / dist_to_goal

            # Calculate repulsive force from obstacles
            rep_force_x, rep_force_y = 0.0, 0.0

            # Convert current position to grid coordinates
            grid_x, grid_y = map_data.world_to_grid(current_x, current_y)

            # Check nearby cells for obstacles
            search_range = int(obstacle_range / map_data.resolution)
            for dx in range(-search_range, search_range + 1):
                for dy in range(-search_range, search_range + 1):
                    check_x, check_y = grid_x + dx, grid_y + dy

                    # Skip if out of bounds
                    if not (
                        0 <= check_x < map_data.width and 0 <= check_y < map_data.height
                    ):
                        continue

                    # Skip if not occupied
                    if not map_data.is_occupied(check_x, check_y):
                        continue

                    # Calculate world coordinates of this cell
                    obs_x, obs_y = map_data.grid_to_world(check_x, check_y)

                    # Calculate distance to obstacle
                    obs_dist = math.sqrt(
                        (current_x - obs_x) ** 2 + (current_y - obs_y) ** 2
                    )

                    # Skip if too far
                    if obs_dist > obstacle_range:
                        continue

                    # Calculate repulsion (inversely proportional to square of distance)
                    if obs_dist > 0.01:  # Avoid division by zero
                        repulsion = (
                            obstacle_weight
                            * (1.0 / obs_dist - 1.0 / obstacle_range)
                            / (obs_dist * obs_dist)
                        )

                        # Add to total repulsive force
                        rep_force_x += repulsion * (current_x - obs_x) / obs_dist
                        rep_force_y += repulsion * (current_y - obs_y) / obs_dist

            # Combine forces
            total_force_x = attr_force_x + rep_force_x
            total_force_y = attr_force_y + rep_force_y

            # Normalize
            force_magnitude = math.sqrt(total_force_x**2 + total_force_y**2)
            if force_magnitude > 0.01:
                total_force_x /= force_magnitude
                total_force_y /= force_magnitude

            # Update position
            new_x = current_x + step_size * total_force_x
            new_y = current_y + step_size * total_force_y

            # Calculate orientation based on movement direction
            new_theta = math.atan2(total_force_y, total_force_x)

            # Add to path
            path.append(Waypoint(x=new_x, y=new_y, theta=new_theta, action="navigate"))

            # Update current position
            current_x, current_y = new_x, new_y

            iterations += 1

        if goal_reached:
            logger.info(f"Found path with {len(path)} waypoints using potential fields")
        else:
            logger.warning(
                "Failed to find path with potential fields within iteration limit"
            )

        return path
