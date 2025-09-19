"""
A* path planning algorithm implementation for PathfinderBot navigation.

This module provides an implementation of the A* algorithm for finding optimal
paths through the robot's environment.
"""

import numpy as np
import heapq
from typing import List, Tuple, Dict, Optional, Set, Callable, Any
import math
import time

from pathfinder_pkg.utils.logging import get_logger
from pathfinder_pkg.navigation.map import OccupancyGridMap
from pathfinder_pkg.navigation.localization import Pose
from pathfinder_pkg.navigation.path_planning.planner import PathPlanner, Waypoint

logger = get_logger(__name__)


class Node:
    """A node in the A* search graph."""

    def __init__(
        self, x: int, y: int, g_cost: float = 0.0, h_cost: float = 0.0, parent=None
    ):
        """
        Initialize a node.

        Args:
            x: X coordinate in grid space
            y: Y coordinate in grid space
            g_cost: Cost from start to this node
            h_cost: Heuristic cost from this node to goal
            parent: Parent node
        """
        self.x = x
        self.y = y
        self.g_cost = g_cost
        self.h_cost = h_cost
        self.parent = parent

    @property
    def f_cost(self) -> float:
        """Total cost of the node (g + h)."""
        return self.g_cost + self.h_cost

    def __eq__(self, other) -> bool:
        """Check if two nodes are equal (same position)."""
        if not isinstance(other, Node):
            return False
        return self.x == other.x and self.y == other.y

    def __lt__(self, other) -> bool:
        """Compare nodes by f_cost for priority queue."""
        if self.f_cost == other.f_cost:
            return self.h_cost < other.h_cost
        return self.f_cost < other.f_cost

    def __hash__(self) -> int:
        """Hash function for node to use in sets/dicts."""
        return hash((self.x, self.y))


class AStarPlanner(PathPlanner):
    """
    A* path planning algorithm implementation.

    This planner uses the A* algorithm to find the shortest path from the start
    to the goal while avoiding obstacles.
    """

    def __init__(self):
        """Initialize the A* planner."""
        super().__init__()

    def plan_path(
        self, map_data: OccupancyGridMap, start_pose: Pose, goal_pose: Pose, **kwargs
    ) -> List[Waypoint]:
        """
        Plan a path using A* algorithm.

        Args:
            map_data: Occupancy grid map of the environment
            start_pose: Starting pose of the robot
            goal_pose: Goal pose to reach
            **kwargs: Additional parameters:
                - heuristic: Heuristic function to use ('manhattan', 'euclidean', 'diagonal')
                - robot_radius: Radius of the robot in meters
                - allow_diagonal: Whether to allow diagonal movements
                - max_iterations: Maximum number of iterations
                - smooth_path: Whether to smooth the resulting path
                - weight_smooth: Weight for path smoothing

        Returns:
            List of waypoints representing the planned path
        """
        # Get parameters
        heuristic = kwargs.get("heuristic", "euclidean")
        robot_radius = kwargs.get("robot_radius", 0.2)
        allow_diagonal = kwargs.get("allow_diagonal", True)
        max_iterations = kwargs.get("max_iterations", 10000)
        smooth_path = kwargs.get("smooth_path", True)

        # Convert start and goal poses to grid coordinates
        start_x, start_y = map_data.world_to_grid(start_pose.x, start_pose.y)
        goal_x, goal_y = map_data.world_to_grid(goal_pose.x, goal_pose.y)

        # Create start and goal nodes
        start_node = Node(start_x, start_y)
        goal_node = Node(goal_x, goal_y)

        # Check if start or goal is out of bounds
        if not (0 <= start_x < map_data.width and 0 <= start_y < map_data.height):
            logger.error(
                f"Start position ({start_pose.x}, {start_pose.y}) is out of bounds"
            )
            return []

        if not (0 <= goal_x < map_data.width and 0 <= goal_y < map_data.height):
            logger.error(
                f"Goal position ({goal_pose.x}, {goal_pose.y}) is out of bounds"
            )
            return []

        # Check if start or goal is in collision
        if self._is_collision(map_data, start_x, start_y, robot_radius):
            logger.error(
                f"Start position ({start_pose.x}, {start_pose.y}) is in collision"
            )
            return []

        if self._is_collision(map_data, goal_x, goal_y, robot_radius):
            logger.error(
                f"Goal position ({goal_pose.x}, {goal_pose.y}) is in collision"
            )
            return []

        # Select heuristic function
        h_func = self._get_heuristic(heuristic)

        # Calculate initial h-cost for start node
        start_node.h_cost = h_func(start_x, start_y, goal_x, goal_y)

        # Initialize open and closed sets
        open_set = []
        heapq.heappush(open_set, start_node)
        closed_set = set()

        # Define node lookup dictionary for faster retrieval
        node_lookup = {(start_node.x, start_node.y): start_node}

        # Define movement directions
        if allow_diagonal:
            directions = [
                (0, 1),
                (1, 0),
                (0, -1),
                (-1, 0),  # 4-connected neighbors
                (1, 1),
                (1, -1),
                (-1, -1),
                (-1, 1),  # Diagonal neighbors
            ]
            movement_costs = [1.0, 1.0, 1.0, 1.0, 1.414, 1.414, 1.414, 1.414]
        else:
            directions = [(0, 1), (1, 0), (0, -1), (-1, 0)]  # 4-connected neighbors
            movement_costs = [1.0, 1.0, 1.0, 1.0]

        # Start A* search
        iterations = 0
        path_found = False

        logger.info(
            f"Starting A* search from ({start_x}, {start_y}) to ({goal_x}, {goal_y})"
        )

        while open_set and iterations < max_iterations:
            # Get node with lowest f_cost
            current_node = heapq.heappop(open_set)

            # Check if we reached the goal
            if current_node.x == goal_node.x and current_node.y == goal_node.y:
                path_found = True
                goal_node = current_node  # Update goal node with the path information
                break

            # Add current node to closed set
            closed_set.add((current_node.x, current_node.y))

            # Check neighbors
            for i, (dx, dy) in enumerate(directions):
                # Calculate neighbor coordinates
                nx, ny = current_node.x + dx, current_node.y + dy

                # Check if neighbor is valid
                if not (0 <= nx < map_data.width and 0 <= ny < map_data.height):
                    continue

                # Skip if neighbor is in closed set
                if (nx, ny) in closed_set:
                    continue

                # Check if neighbor is in collision
                if self._is_collision(map_data, nx, ny, robot_radius):
                    continue

                # If using diagonal movement, check if path to neighbor is blocked
                if dx != 0 and dy != 0:
                    # Check if horizontal and vertical paths are free
                    if self._is_collision(
                        map_data, current_node.x + dx, current_node.y, robot_radius
                    ) or self._is_collision(
                        map_data, current_node.x, current_node.y + dy, robot_radius
                    ):
                        continue

                # Calculate g_cost for neighbor
                movement_cost = movement_costs[i]
                new_g_cost = current_node.g_cost + movement_cost

                # Calculate h_cost for neighbor
                h_cost = h_func(nx, ny, goal_x, goal_y)

                # Get or create neighbor node
                neighbor_key = (nx, ny)
                if neighbor_key in node_lookup:
                    neighbor_node = node_lookup[neighbor_key]
                    # Skip if current path to neighbor is worse
                    if new_g_cost >= neighbor_node.g_cost:
                        continue
                    # Update neighbor's g_cost and parent
                    neighbor_node.g_cost = new_g_cost
                    neighbor_node.parent = current_node
                else:
                    # Create new neighbor node
                    neighbor_node = Node(nx, ny, new_g_cost, h_cost, current_node)
                    node_lookup[neighbor_key] = neighbor_node
                    heapq.heappush(open_set, neighbor_node)

            iterations += 1

        # Check if path was found
        if not path_found:
            logger.warning(f"No path found after {iterations} iterations")
            return []

        logger.info(f"Path found in {iterations} iterations")

        # Reconstruct path
        grid_path = []
        current = goal_node
        while current:
            grid_path.append((current.x, current.y))
            current = current.parent
        grid_path.reverse()  # Reverse to get path from start to goal

        # Convert grid path to world coordinates and create waypoints
        waypoints = []
        for i, (gx, gy) in enumerate(grid_path):
            wx, wy = map_data.grid_to_world(gx, gy)

            # Determine action for waypoint
            action = "navigate"
            if i == 0:
                action = "start"
                # Use start pose orientation
                theta = start_pose.theta
            elif i == len(grid_path) - 1:
                action = "goal"
                # Use goal pose orientation
                theta = goal_pose.theta
            else:
                # Calculate orientation based on movement direction
                next_x, next_y = (
                    grid_path[i + 1] if i + 1 < len(grid_path) else grid_path[i]
                )
                prev_x, prev_y = grid_path[i - 1] if i - 1 >= 0 else grid_path[i]

                # Average direction between previous and next points
                dx = next_x - prev_x
                dy = next_y - prev_y

                if dx == 0 and dy == 0:
                    # If no movement, use previous orientation or default to 0
                    theta = waypoints[-1].theta if waypoints else 0
                else:
                    theta = math.atan2(dy, dx)

            waypoints.append(Waypoint(x=wx, y=wy, theta=theta, action=action))

        # Smooth path if requested
        if smooth_path and len(waypoints) > 2:
            weight_smooth = kwargs.get("weight_smooth", 0.1)
            waypoints = self.smooth_path(waypoints, weight_smooth=weight_smooth)

        logger.info(f"A* planner generated path with {len(waypoints)} waypoints")

        return waypoints

    def _is_collision(
        self, map_data: OccupancyGridMap, x: int, y: int, robot_radius: float
    ) -> bool:
        """
        Check if a grid cell is in collision with obstacles.

        Args:
            map_data: Occupancy grid map
            x: X coordinate in grid space
            y: Y coordinate in grid space
            robot_radius: Radius of the robot in meters

        Returns:
            True if in collision, False otherwise
        """
        # Check if the cell itself is occupied
        if map_data.is_occupied(x, y):
            return True

        # Convert robot radius to grid cells
        radius_cells = int(robot_radius / map_data.resolution) + 1

        # Check surrounding cells within robot radius
        for dx in range(-radius_cells, radius_cells + 1):
            for dy in range(-radius_cells, radius_cells + 1):
                # Skip if distance is beyond radius
                if dx * dx + dy * dy > radius_cells * radius_cells:
                    continue

                # Calculate check coordinates
                check_x, check_y = x + dx, y + dy

                # Skip if out of bounds
                if not (
                    0 <= check_x < map_data.width and 0 <= check_y < map_data.height
                ):
                    continue

                # Check if occupied
                if map_data.is_occupied(check_x, check_y):
                    return True

        return False

    def _get_heuristic(
        self, heuristic_type: str
    ) -> Callable[[int, int, int, int], float]:
        """
        Get the heuristic function based on type.

        Args:
            heuristic_type: Type of heuristic ('manhattan', 'euclidean', 'diagonal')

        Returns:
            Heuristic function
        """
        if heuristic_type == "manhattan":
            return lambda x1, y1, x2, y2: abs(x1 - x2) + abs(y1 - y2)
        elif heuristic_type == "euclidean":
            return lambda x1, y1, x2, y2: math.sqrt((x1 - x2) ** 2 + (y1 - y2) ** 2)
        elif heuristic_type == "diagonal":
            return lambda x1, y1, x2, y2: (
                max(abs(x1 - x2), abs(y1 - y2))
                + 0.414 * min(abs(x1 - x2), abs(y1 - y2))
            )
        else:
            logger.warning(f"Unknown heuristic type: {heuristic_type}, using euclidean")
            return lambda x1, y1, x2, y2: math.sqrt((x1 - x2) ** 2 + (y1 - y2) ** 2)
