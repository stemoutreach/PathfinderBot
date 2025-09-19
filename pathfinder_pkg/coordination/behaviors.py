"""
Collaborative behaviors for multi-robot systems.
Implements cooperative actions like object transport, area coverage, and collaborative games.
"""

import numpy as np
import math
import time
import uuid
import random
import logging
from typing import Dict, List, Tuple, Any, Optional, Set, Callable
from enum import Enum
from dataclasses import dataclass

from .algorithms import (
    Position,
    Pose,
    RobotState,
    Task,
    TaskPriority,
    CollisionAvoidance,
)


class TransportRole(Enum):
    """Roles for robots during collaborative transport."""

    LEADER = "leader"
    FOLLOWER = "follower"
    SUPPORT = "support"


class CoverageStatus(Enum):
    """Status of an area in coverage tasks."""

    UNKNOWN = "unknown"
    ASSIGNED = "assigned"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"


class GameRole(Enum):
    """Roles for robots in collaborative games."""

    OFFENSE = "offense"
    DEFENSE = "defense"
    GOALKEEPER = "goalkeeper"
    RELAY_RUNNER = "relay_runner"
    PUZZLE_SOLVER = "puzzle_solver"


@dataclass
class AreaCell:
    """Represents a cell in a grid for area coverage."""

    x: int
    y: int
    status: CoverageStatus = CoverageStatus.UNKNOWN
    assigned_robot: Optional[str] = None
    last_updated: float = 0.0

    def assign(self, robot_id: str):
        """Assign a robot to this cell."""
        self.assigned_robot = robot_id
        self.status = CoverageStatus.ASSIGNED
        self.last_updated = time.time()

    def mark_in_progress(self):
        """Mark cell as in progress."""
        self.status = CoverageStatus.IN_PROGRESS
        self.last_updated = time.time()

    def mark_completed(self):
        """Mark cell as completed."""
        self.status = CoverageStatus.COMPLETED
        self.last_updated = time.time()

    def reset(self):
        """Reset cell to unknown state."""
        self.status = CoverageStatus.UNKNOWN
        self.assigned_robot = None
        self.last_updated = time.time()


class ObjectTransportBehavior:
    """
    Implements collaborative object transport behavior where multiple
    robots work together to move a large object.
    """

    def __init__(self, safety_distance: float = 0.3, logger=None):
        self.robots: Dict[str, RobotState] = {}
        self.robot_roles: Dict[str, TransportRole] = {}
        self.leader_id: Optional[str] = None
        self.target_position: Optional[Position] = None
        self.object_position: Optional[Position] = None
        self.object_orientation: float = 0.0  # radians
        self.safety_distance = safety_distance
        self.formation_distance = 0.5  # Distance between robots and object
        self.logger = logger or logging.getLogger("ObjectTransportBehavior")
        self.collision_avoidance = CollisionAvoidance(safety_distance)

    def set_object_pose(self, position: Position, orientation: float):
        """Set the current object pose."""
        self.object_position = position
        self.object_orientation = orientation

    def set_target_position(self, position: Position):
        """Set the target position for the object."""
        self.target_position = position

    def update_robot_state(self, robot_id: str, state: RobotState) -> None:
        """Update the state of a robot."""
        self.robots[robot_id] = state
        self.collision_avoidance.update_robot_state(robot_id, state)

    def assign_roles(self) -> Dict[str, TransportRole]:
        """
        Assign roles to robots based on their positions and capabilities.
        Returns a mapping of robot_id to role.
        """
        if not self.robots or not self.object_position:
            return {}

        # Sort robots by distance to object
        sorted_robots = sorted(
            self.robots.items(),
            key=lambda item: item[1].pose.position.distance_to(self.object_position),
        )

        # First robot becomes the leader
        leader_id, leader = sorted_robots[0]
        self.leader_id = leader_id
        self.robot_roles[leader_id] = TransportRole.LEADER

        # Determine capacity requirements based on estimated object weight
        # For simplicity, assume 2 robots are needed for small objects, more for larger ones
        min_support_robots = min(len(sorted_robots) - 1, 3)  # At most 3 support robots

        # Assign roles to other robots
        support_count = 0
        for robot_id, robot in sorted_robots[1:]:
            if support_count < min_support_robots:
                self.robot_roles[robot_id] = TransportRole.SUPPORT
                support_count += 1
            else:
                self.robot_roles[robot_id] = TransportRole.FOLLOWER

        self.logger.info(f"Assigned transport roles: {self.robot_roles}")
        return dict(self.robot_roles)

    def get_robot_positions(self) -> Dict[str, Position]:
        """
        Calculate desired positions for robots around the object.
        Returns a mapping of robot_id to target position.
        """
        if not self.robots or not self.object_position:
            return {}

        positions = {}
        robot_ids = list(self.robot_roles.keys())
        n_robots = len(robot_ids)

        if n_robots == 0:
            return positions

        # Calculate positions around the object
        for robot_id, role in self.robot_roles.items():
            if role == TransportRole.LEADER:
                # Leader position: in front of the object in the direction of movement
                if self.target_position:
                    # Calculate direction from object to target
                    dx = self.target_position.x - self.object_position.x
                    dy = self.target_position.y - self.object_position.y
                    distance = math.sqrt(dx**2 + dy**2)

                    if distance > 0:
                        # Normalize and place leader in front of object
                        nx, ny = dx / distance, dy / distance
                        leader_pos_x = (
                            self.object_position.x + nx * self.formation_distance
                        )
                        leader_pos_y = (
                            self.object_position.y + ny * self.formation_distance
                        )
                        positions[robot_id] = Position(leader_pos_x, leader_pos_y)
                    else:
                        # If at target, place leader at current position
                        positions[robot_id] = Position(
                            self.robots[robot_id].pose.position.x,
                            self.robots[robot_id].pose.position.y,
                        )
                else:
                    # No target, place leader at front of object based on orientation
                    front_x = (
                        self.object_position.x
                        + math.cos(self.object_orientation) * self.formation_distance
                    )
                    front_y = (
                        self.object_position.y
                        + math.sin(self.object_orientation) * self.formation_distance
                    )
                    positions[robot_id] = Position(front_x, front_y)
            else:
                # Place support and follower robots around the object
                # Calculate even distribution around the object
                support_robots = [
                    r
                    for r, role in self.robot_roles.items()
                    if role == TransportRole.SUPPORT
                ]
                support_count = len(support_robots)

                if role == TransportRole.SUPPORT:
                    # Place support robots evenly around object
                    support_idx = support_robots.index(robot_id)
                    angle = 2 * math.pi * support_idx / support_count
                    if self.target_position:
                        # Calculate direction from object to target
                        dx = self.target_position.x - self.object_position.x
                        dy = self.target_position.y - self.object_position.y
                        target_angle = math.atan2(dy, dx)

                        # Adjust angles to be perpendicular to movement direction
                        adjusted_angle = (
                            target_angle
                            + math.pi / 2
                            + (
                                math.pi * support_idx / (support_count - 1)
                                if support_count > 1
                                else 0
                            )
                        )
                        pos_x = (
                            self.object_position.x
                            + math.cos(adjusted_angle) * self.formation_distance
                        )
                        pos_y = (
                            self.object_position.y
                            + math.sin(adjusted_angle) * self.formation_distance
                        )
                    else:
                        # No target, distribute evenly
                        pos_x = (
                            self.object_position.x
                            + math.cos(angle) * self.formation_distance
                        )
                        pos_y = (
                            self.object_position.y
                            + math.sin(angle) * self.formation_distance
                        )

                    positions[robot_id] = Position(pos_x, pos_y)
                else:  # FOLLOWER
                    # Followers stay behind the object
                    followers = [
                        r
                        for r, role in self.robot_roles.items()
                        if role == TransportRole.FOLLOWER
                    ]
                    follower_count = len(followers)
                    follower_idx = followers.index(robot_id)

                    if self.target_position:
                        # Place followers behind the object relative to movement direction
                        dx = self.target_position.x - self.object_position.x
                        dy = self.target_position.y - self.object_position.y
                        distance = math.sqrt(dx**2 + dy**2)

                        if distance > 0:
                            # Normalize and place followers behind object
                            nx, ny = (
                                -dx / distance,
                                -dy / distance,
                            )  # Opposite direction
                            offset = self.formation_distance * (1 + 0.5 * follower_idx)
                            follower_pos_x = self.object_position.x + nx * offset
                            follower_pos_y = self.object_position.y + ny * offset
                            positions[robot_id] = Position(
                                follower_pos_x, follower_pos_y
                            )
                        else:
                            # If at target, place at current position
                            positions[robot_id] = Position(
                                self.robots[robot_id].pose.position.x,
                                self.robots[robot_id].pose.position.y,
                            )
                    else:
                        # No target, place behind based on orientation
                        back_angle = self.object_orientation + math.pi
                        offset = self.formation_distance * (1 + 0.3 * follower_idx)
                        back_x = self.object_position.x + math.cos(back_angle) * offset
                        back_y = self.object_position.y + math.sin(back_angle) * offset
                        positions[robot_id] = Position(back_x, back_y)

        return positions

    def get_velocity_commands(self) -> Dict[str, Tuple[Tuple[float, float], float]]:
        """
        Calculate velocity commands for robots to move the object.
        Returns a mapping of robot_id to ((vx, vy), angular_velocity).
        """
        if not self.robots or not self.object_position or not self.target_position:
            return {}

        # Calculate desired positions
        desired_positions = self.get_robot_positions()
        commands = {}

        # Calculate object movement vector
        obj_to_target_x = self.target_position.x - self.object_position.x
        obj_to_target_y = self.target_position.y - self.object_position.y
        obj_to_target_dist = math.sqrt(obj_to_target_x**2 + obj_to_target_y**2)

        # Calculate target orientation for object based on movement direction
        target_orientation = (
            math.atan2(obj_to_target_y, obj_to_target_x)
            if obj_to_target_dist > 0
            else self.object_orientation
        )

        # Normalize object direction vector
        if obj_to_target_dist > 0:
            obj_dir_x, obj_dir_y = (
                obj_to_target_x / obj_to_target_dist,
                obj_to_target_y / obj_to_target_dist,
            )
        else:
            obj_dir_x, obj_dir_y = math.cos(self.object_orientation), math.sin(
                self.object_orientation
            )

        for robot_id, robot_state in self.robots.items():
            if robot_id in desired_positions:
                desired_pos = desired_positions[robot_id]
                current_pos = robot_state.pose.position

                # Calculate position error
                dx = desired_pos.x - current_pos.x
                dy = desired_pos.y - current_pos.y
                dist_to_desired = math.sqrt(dx**2 + dy**2)

                # Calculate orientation error
                # For leader, orient toward target; for others, orient toward object
                if self.robot_roles.get(robot_id) == TransportRole.LEADER:
                    target_orient = target_orientation
                else:
                    # Orient toward the object
                    dx_to_obj = self.object_position.x - current_pos.x
                    dy_to_obj = self.object_position.y - current_pos.y
                    target_orient = math.atan2(dy_to_obj, dx_to_obj)

                orient_diff = target_orient - robot_state.pose.orientation
                # Normalize to [-pi, pi]
                while orient_diff > math.pi:
                    orient_diff -= 2 * math.pi
                while orient_diff < -math.pi:
                    orient_diff += 2 * math.pi

                # Proportional controller for position
                kp_pos = 0.5  # Position gain
                vx = kp_pos * dx
                vy = kp_pos * dy

                # Limit velocity
                max_linear_speed = 0.3  # m/s, slower for safety
                v_mag = math.sqrt(vx**2 + vy**2)
                if v_mag > max_linear_speed:
                    scale = max_linear_speed / v_mag
                    vx *= scale
                    vy *= scale

                # Proportional controller for orientation
                kp_orient = 1.0
                angular_v = kp_orient * orient_diff

                # Limit angular velocity
                max_angular_speed = math.pi / 4  # rad/s
                if abs(angular_v) > max_angular_speed:
                    angular_v = (
                        max_angular_speed if angular_v > 0 else -max_angular_speed
                    )

                # For coordinated movement, adjust velocities based on roles
                role = self.robot_roles.get(robot_id)
                if role == TransportRole.LEADER:
                    # Leader moves toward target when close to desired position
                    if dist_to_desired < 0.1 and obj_to_target_dist > 0.1:
                        # Start moving toward target, pulling the object
                        vx = max_linear_speed * obj_dir_x
                        vy = max_linear_speed * obj_dir_y
                elif role == TransportRole.SUPPORT:
                    # Support robots help move the object
                    if dist_to_desired < 0.1 and obj_to_target_dist > 0.1:
                        # Push in the direction of the target
                        push_factor = 0.7  # Slightly slower than leader
                        vx = push_factor * max_linear_speed * obj_dir_x
                        vy = push_factor * max_linear_speed * obj_dir_y
                else:  # FOLLOWER
                    # Followers just follow their assigned positions
                    pass

                commands[robot_id] = ((vx, vy), angular_v)

        # Apply collision avoidance
        return self.collision_avoidance.process_velocity_commands(commands)

    def is_transport_complete(self) -> bool:
        """
        Check if the object transport task is complete.
        Returns True if the object is at the target position.
        """
        if not self.object_position or not self.target_position:
            return False

        # Check if object is close to target
        distance = self.object_position.distance_to(self.target_position)
        return distance < 0.2  # 20 cm threshold


class AreaCoverageBehavior:
    """
    Implements area coverage behavior where multiple robots
    efficiently explore and cover an area.
    """

    def __init__(
        self,
        grid_size_x: int,
        grid_size_y: int,
        cell_size: float = 1.0,  # meters
        origin: Position = Position(0, 0),
        logger=None,
    ):
        self.grid_size_x = grid_size_x
        self.grid_size_y = grid_size_y
        self.cell_size = cell_size
        self.origin = origin
        self.grid: Dict[Tuple[int, int], AreaCell] = {}
        self.robots: Dict[str, RobotState] = {}
        self.robot_assignments: Dict[str, List[Tuple[int, int]]] = {}
        self.collision_avoidance = CollisionAvoidance(0.3)
        self.logger = logger or logging.getLogger("AreaCoverageBehavior")

        # Initialize grid
        self._initialize_grid()

    def _initialize_grid(self):
        """Initialize the grid cells."""
        for x in range(self.grid_size_x):
            for y in range(self.grid_size_y):
                self.grid[(x, y)] = AreaCell(x, y)

    def update_robot_state(self, robot_id: str, state: RobotState) -> None:
        """Update the state of a robot."""
        self.robots[robot_id] = state
        self.collision_avoidance.update_robot_state(robot_id, state)

        # Update cell status based on robot position
        cell_coords = self._position_to_cell(state.pose.position)
        if self._is_valid_cell(cell_coords):
            # Mark the current cell as completed
            cell = self.grid[cell_coords]
            cell.mark_completed()

            # Mark cells within sensor range as in-progress
            self._update_cells_in_range(state.pose.position, 1.0)  # 1.0m sensor range

    def _position_to_cell(self, position: Position) -> Tuple[int, int]:
        """Convert a world position to grid cell coordinates."""
        x = int((position.x - self.origin.x) / self.cell_size)
        y = int((position.y - self.origin.y) / self.cell_size)
        return (x, y)

    def _cell_to_position(self, cell: Tuple[int, int]) -> Position:
        """Convert grid cell coordinates to world position (center of cell)."""
        x = self.origin.x + (cell[0] + 0.5) * self.cell_size
        y = self.origin.y + (cell[1] + 0.5) * self.cell_size
        return Position(x, y)

    def _is_valid_cell(self, cell: Tuple[int, int]) -> bool:
        """Check if cell coordinates are valid."""
        x, y = cell
        return 0 <= x < self.grid_size_x and 0 <= y < self.grid_size_y

    def _update_cells_in_range(self, position: Position, range_m: float):
        """
        Update status of cells within range of the position.
        Args:
            position: Center position
            range_m: Range in meters
        """
        # Calculate cell range
        cell_range = int(range_m / self.cell_size) + 1
        center_cell = self._position_to_cell(position)

        for dx in range(-cell_range, cell_range + 1):
            for dy in range(-cell_range, cell_range + 1):
                cell_x, cell_y = center_cell[0] + dx, center_cell[1] + dy
                cell_coords = (cell_x, cell_y)

                if self._is_valid_cell(cell_coords):
                    # Calculate distance from position to cell center
                    cell_center = self._cell_to_position(cell_coords)
                    distance = position.distance_to(cell_center)

                    # Update cell status if within range
                    if distance <= range_m:
                        cell = self.grid[cell_coords]
                        if cell.status == CoverageStatus.UNKNOWN:
                            cell.mark_in_progress()

    def divide_area(self) -> Dict[str, List[Tuple[int, int]]]:
        """
        Divide the area among available robots.
        Returns a mapping of robot_id to list of assigned cell coordinates.
        """
        if not self.robots:
            return {}

        # Get uncovered cells (unknown or in-progress)
        uncovered_cells = [
            (x, y)
            for (x, y), cell in self.grid.items()
            if cell.status != CoverageStatus.COMPLETED
        ]

        if not uncovered_cells:
            return {}

        # Divide cells among robots using a simple grid partitioning
        n_robots = len(self.robots)
        assignments = {robot_id: [] for robot_id in self.robots.keys()}
        robot_ids = list(self.robots.keys())

        # Sort cells by distance from current robot positions
        robot_positions = {
            r_id: state.pose.position for r_id, state in self.robots.items()
        }

        for cell_coords in uncovered_cells:
            cell_pos = self._cell_to_position(cell_coords)

            # Find closest robot to this cell
            min_distance = float("inf")
            closest_robot_id = None

            for robot_id, position in robot_positions.items():
                distance = position.distance_to(cell_pos)
                if distance < min_distance:
                    min_distance = distance
                    closest_robot_id = robot_id

            if closest_robot_id:
                assignments[closest_robot_id].append(cell_coords)

        # Store assignments
        self.robot_assignments = assignments

        # Mark cells as assigned
        for robot_id, cells in assignments.items():
            for cell_coords in cells:
                if self._is_valid_cell(cell_coords):
                    self.grid[cell_coords].assign(robot_id)

        self.logger.info(f"Area divided among {n_robots} robots")
        return assignments

    def get_next_cell(self, robot_id: str) -> Optional[Tuple[int, int]]:
        """
        Get the next cell for a robot to visit.
        Args:
            robot_id: Robot ID

        Returns:
            Next cell coordinates, or None if no cells are assigned.
        """
        if (
            robot_id not in self.robot_assignments
            or not self.robot_assignments[robot_id]
        ):
            return None

        # Get robot's current position
        if robot_id not in self.robots:
            return None

        robot_position = self.robots[robot_id].pose.position

        # Find the nearest unvisited cell
        assigned_cells = self.robot_assignments[robot_id]
        unvisited_cells = [
            cell
            for cell in assigned_cells
            if self.grid[cell].status != CoverageStatus.COMPLETED
        ]

        if not unvisited_cells:
            return None

        # Sort by distance to current position
        cell_distances = [
            (cell, robot_position.distance_to(self._cell_to_position(cell)))
            for cell in unvisited_cells
        ]

        nearest_cell = min(cell_distances, key=lambda x: x[1])[0]
        return nearest_cell

    def get_velocity_commands(self) -> Dict[str, Tuple[Tuple[float, float], float]]:
        """
        Calculate velocity commands for robots to cover their assigned areas.
        Returns a mapping of robot_id to ((vx, vy), angular_velocity).
        """
        commands = {}

        for robot_id, state in self.robots.items():
            # Get the next cell to visit
            next_cell = self.get_next_cell(robot_id)

            if not next_cell:
                # No cells to visit, stay in place
                commands[robot_id] = ((0.0, 0.0), 0.0)
                continue

            # Get target position (center of cell)
            target_position = self._cell_to_position(next_cell)
            current_position = state.pose.position

            # Calculate position error
            dx = target_position.x - current_position.x
            dy = target_position.y - current_position.y
            distance = math.sqrt(dx**2 + dy**2)

            # Calculate orientation to target
            target_orient = math.atan2(dy, dx)
            current_orient = state.pose.orientation
            orient_diff = target_orient - current_orient

            # Normalize to [-pi, pi]
            while orient_diff > math.pi:
                orient_diff -= 2 * math.pi
            while orient_diff < -math.pi:
                orient_diff += 2 * math.pi

            # Proportional controller for position
            kp_pos = 0.5  # Position gain
            vx = kp_pos * dx
            vy = kp_pos * dy

            # Limit velocity
            max_linear_speed = 0.5  # m/s
            v_mag = math.sqrt(vx**2 + vy**2)
            if v_mag > max_linear_speed:
                scale = max_linear_speed / v_mag
                vx *= scale
                vy *= scale

            # Proportional controller for orientation
            kp_orient = 1.0
            angular_v = kp_orient * orient_diff

            # Limit angular velocity
            max_angular_speed = math.pi / 2  # rad/s
            if abs(angular_v) > max_angular_speed:
                angular_v = max_angular_speed if angular_v > 0 else -max_angular_speed

            commands[robot_id] = ((vx, vy), angular_v)

        # Apply collision avoidance
        return self.collision_avoidance.process_velocity_commands(commands)

    def get_coverage_percentage(self) -> float:
        """
        Get the percentage of area covered.
        Returns the percentage as a float from 0.0 to 1.0.
        """
        total_cells = self.grid_size_x * self.grid_size_y
        completed_cells = sum(
            1 for cell in self.grid.values() if cell.status == CoverageStatus.COMPLETED
        )

        return completed_cells / total_cells if total_cells > 0 else 0.0

    def is_coverage_complete(self) -> bool:
        """
        Check if the area coverage is complete.
        Returns True if all cells have been covered.
        """
        return self.get_coverage_percentage() >= 0.99  # Allow for small margin of error


class CollaborativeGameBehavior:
    """
    Implements collaborative game behaviors for multiple robots.
    Supports robot soccer, relay races, and cooperative puzzles.
    """

    class GameType(Enum):
        """Types of games supported."""

        SOCCER = "soccer"
        RELAY_RACE = "relay_race"
        COOPERATIVE_PUZZLE = "cooperative_puzzle"

    def __init__(self, game_type: GameType, logger=None):
        self.game_type = game_type
        self.robots: Dict[str, RobotState] = {}
        self.robot_roles: Dict[str, GameRole] = {}
        self.game_state: Dict[str, Any] = {}  # Game-specific state
        self.collision_avoidance = CollisionAvoidance(0.3)
        self.logger = logger or logging.getLogger("CollaborativeGameBehavior")

        # Initialize game-specific state
        self._initialize_game_state()

    def _initialize_game_state(self):
        """Initialize game-specific state."""
        if self.game_type == self.GameType.SOCCER:
            self.game_state = {
                "ball_position": Position(0, 0),
                "goals": {"team_a": 0, "team_b": 0},
                "field_dimensions": (10, 7),  # Width, height in meters
                "goal_positions": {"team_a": Position(-5, 0), "team_b": Position(5, 0)},
            }
        elif self.game_type == self.GameType.RELAY_RACE:
            self.game_state = {
                "baton_holder": None,
                "checkpoints": [Position(x, 0) for x in range(-5, 6, 2)],
                "team_progress": 0,
                "lap_count": 0,
                "max_laps": 3,
            }
        elif self.game_type == self.GameType.COOPERATIVE_PUZZLE:
            self.game_state = {
                "puzzle_pieces": {
                    "piece1": {
                        "position": Position(-3, -3),
                        "assigned_robot": None,
                        "in_place": False,
                    },
                    "piece2": {
                        "position": Position(-3, 3),
                        "assigned_robot": None,
                        "in_place": False,
                    },
                    "piece3": {
                        "position": Position(3, -3),
                        "assigned_robot": None,
                        "in_place": False,
                    },
                    "piece4": {
                        "position": Position(3, 3),
                        "assigned_robot": None,
                        "in_place": False,
                    },
                },
                "target_positions": {
                    "piece1": Position(-1, -1),
                    "piece2": Position(-1, 1),
                    "piece3": Position(1, -1),
                    "piece4": Position(1, 1),
                },
                "puzzle_completed": False,
            }

    def update_robot_state(self, robot_id: str, state: RobotState) -> None:
        """Update the state of a robot."""
        self.robots[robot_id] = state
        self.collision_avoidance.update_robot_state(robot_id, state)

    def assign_roles(self) -> Dict[str, GameRole]:
        """
        Assign roles to robots based on game type and robot capabilities.
        Returns a mapping of robot_id to role.
        """
        if not self.robots:
            return {}

        robot_ids = list(self.robots.keys())
        n_robots = len(robot_ids)

        if self.game_type == self.GameType.SOCCER:
            # Simple role assignment for soccer
            if n_robots >= 1:
                self.robot_roles[robot_ids[0]] = GameRole.GOALKEEPER

            remaining_robots = robot_ids[1:] if n_robots > 1 else []

            # Divide remaining robots between offense and defense
            offense_count = len(remaining_robots) // 2
            for i, robot_id in enumerate(remaining_robots):
                if i < offense_count:
                    self.robot_roles[robot_id] = GameRole.OFFENSE
                else:
                    self.robot_roles[robot_id] = GameRole.DEFENSE

        elif self.game_type == self.GameType.RELAY_RACE:
            # All robots are relay runners
            for robot_id in robot_ids:
                self.robot_roles[robot_id] = GameRole.RELAY_RUNNER

        elif self.game_type == self.GameType.COOPERATIVE_PUZZLE:
            # All robots are puzzle solvers
            for robot_id in robot_ids:
                self.robot_roles[robot_id] = GameRole.PUZZLE_SOLVER

            # Assign robots to specific puzzle pieces
            pieces = list(self.game_state["puzzle_pieces"].keys())
            for i, robot_id in enumerate(robot_ids[: len(pieces)]):
                piece_id = pieces[i]
                self.game_state["puzzle_pieces"][piece_id]["assigned_robot"] = robot_id

        self.logger.info(f"Assigned game roles: {self.robot_roles}")
        return dict(self.robot_roles)

    def get_velocity_commands(self) -> Dict[str, Tuple[Tuple[float, float], float]]:
        """
        Calculate velocity commands for robots based on game type and roles.
        Returns a mapping of robot_id to ((vx, vy), angular_velocity).
        """
        commands = {}

        if self.game_type == self.GameType.SOCCER:
            commands = self._soccer_velocity_commands()
        elif self.game_type == self.GameType.RELAY_RACE:
            commands = self._relay_race_velocity_commands()
        elif self.game_type == self.GameType.COOPERATIVE_PUZZLE:
            commands = self._puzzle_velocity_commands()

        # Apply collision avoidance
        return self.collision_avoidance.process_velocity_commands(commands)

    def _soccer_velocity_commands(self) -> Dict[str, Tuple[Tuple[float, float], float]]:
        """Calculate velocity commands for soccer game."""
        commands = {}
        ball_pos = self.game_state["ball_position"]

        for robot_id, state in self.robots.items():
            role = self.robot_roles.get(robot_id)
            if not role:
                continue

            current_pos = state.pose.position

            if role == GameRole.GOALKEEPER:
                # Goalkeeper stays in front of the goal and tries to block the ball
                goal_pos = self.game_state["goal_positions"][
                    "team_a"
                ]  # Assuming robot is on team A

                # Calculate position between ball and goal
                dx_ball_goal = ball_pos.x - goal_pos.x
                dy_ball_goal = ball_pos.y - goal_pos.y
                dist_ball_goal = math.sqrt(dx_ball_goal**2 + dy_ball_goal**2)

                if dist_ball_goal > 0:
                    # Normalize direction vector
                    nx = dx_ball_goal / dist_ball_goal
                    ny = dy_ball_goal / dist_ball_goal

                    # Position slightly in front of goal toward ball
                    target_x = goal_pos.x + nx * 1.0  # 1m in front of goal
                    target_y = goal_pos.y + ny * 0.5  # Limited vertical movement
                    target_pos = Position(target_x, target_y)
                else:
                    target_pos = Position(goal_pos.x, goal_pos.y)

            elif role == GameRole.OFFENSE:
                # Offensive player tries to get the ball and move it to opposing goal
                target_pos = ball_pos

            else:  # DEFENSE
                # Defensive player tries to block opposing team
                goal_pos = self.game_state["goal_positions"]["team_a"]

                # Position between ball and own goal
                dx_ball_goal = ball_pos.x - goal_pos.x
                dy_ball_goal = ball_pos.y - goal_pos.y
                dist_ball_goal = math.sqrt(dx_ball_goal**2 + dy_ball_goal**2)

                if dist_ball_goal > 0:
                    # Normalize direction vector
                    nx = dx_ball_goal / dist_ball_goal
                    ny = dy_ball_goal / dist_ball_goal

                    # Position 2/3 of the way from goal to ball
                    target_x = goal_pos.x + nx * dist_ball_goal * 0.67
                    target_y = goal_pos.y + ny * dist_ball_goal * 0.67
                    target_pos = Position(target_x, target_y)
                else:
                    target_pos = ball_pos

            # Calculate position error
            dx = target_pos.x - current_pos.x
            dy = target_pos.y - current_pos.y
            distance = math.sqrt(dx**2 + dy**2)

            # Calculate orientation to target
            target_orient = math.atan2(dy, dx)
            current_orient = state.pose.orientation
            orient_diff = target_orient - current_orient

            # Normalize to [-pi, pi]
            while orient_diff > math.pi:
                orient_diff -= 2 * math.pi
            while orient_diff < -math.pi:
                orient_diff += 2 * math.pi

            # Proportional controller for position
            kp_pos = 0.5  # Position gain
            vx = kp_pos * dx
            vy = kp_pos * dy

            # Limit velocity
            max_linear_speed = 0.5  # m/s
            v_mag = math.sqrt(vx**2 + vy**2)
            if v_mag > max_linear_speed:
                scale = max_linear_speed / v_mag
                vx *= scale
                vy *= scale

            # Proportional controller for orientation
            kp_orient = 1.0
            angular_v = kp_orient * orient_diff

            # Limit angular velocity
            max_angular_speed = math.pi / 2  # rad/s
            if abs(angular_v) > max_angular_speed:
                angular_v = max_angular_speed if angular_v > 0 else -max_angular_speed

            commands[robot_id] = ((vx, vy), angular_v)

        return commands

    def _relay_race_velocity_commands(
        self,
    ) -> Dict[str, Tuple[Tuple[float, float], float]]:
        """Calculate velocity commands for relay race game."""
        commands = {}
        checkpoints = self.game_state["checkpoints"]
        baton_holder = self.game_state["baton_holder"]
        progress = self.game_state["team_progress"]

        # Current and next checkpoint
        current_checkpoint_idx = progress % len(checkpoints)
        next_checkpoint_idx = (current_checkpoint_idx + 1) % len(checkpoints)

        current_checkpoint = checkpoints[current_checkpoint_idx]
        next_checkpoint = checkpoints[next_checkpoint_idx]

        for robot_id, state in self.robots.items():
            current_pos = state.pose.position

            if robot_id == baton_holder:
                # Baton holder goes to the next checkpoint
                target_pos = next_checkpoint
            else:
                # Others go to the current checkpoint to prepare for handoff
                target_pos = current_checkpoint

            # Calculate position error
            dx = target_pos.x - current_pos.x
            dy = target_pos.y - current_pos.y
            distance = math.sqrt(dx**2 + dy**2)

            # Calculate orientation to target
            target_orient = math.atan2(dy, dx)
            current_orient = state.pose.orientation
            orient_diff = target_orient - current_orient

            # Normalize to [-pi, pi]
            while orient_diff > math.pi:
                orient_diff -= 2 * math.pi
            while orient_diff < -math.pi:
                orient_diff += 2 * math.pi

            # Proportional controller for position
            kp_pos = 0.5  # Position gain
            vx = kp_pos * dx
            vy = kp_pos * dy

            # Limit velocity
            max_linear_speed = 0.5  # m/s
            v_mag = math.sqrt(vx**2 + vy**2)
            if v_mag > max_linear_speed:
                scale = max_linear_speed / v_mag
                vx *= scale
                vy *= scale

            # Proportional controller for orientation
            kp_orient = 1.0
            angular_v = kp_orient * orient_diff

            # Limit angular velocity
            max_angular_speed = math.pi / 2  # rad/s
            if abs(angular_v) > max_angular_speed:
                angular_v = max_angular_speed if angular_v > 0 else -max_angular_speed

            commands[robot_id] = ((vx, vy), angular_v)

        return commands

    def _puzzle_velocity_commands(self) -> Dict[str, Tuple[Tuple[float, float], float]]:
        """Calculate velocity commands for cooperative puzzle game."""
        commands = {}

        for robot_id, state in self.robots.items():
            current_pos = state.pose.position

            # Find the assigned puzzle piece for this robot
            assigned_piece = None
            for piece_id, piece_data in self.game_state["puzzle_pieces"].items():
                if piece_data["assigned_robot"] == robot_id:
                    assigned_piece = piece_id
                    break

            if not assigned_piece:
                # No assigned piece, stay in place
                commands[robot_id] = ((0.0, 0.0), 0.0)
                continue

            piece_data = self.game_state["puzzle_pieces"][assigned_piece]

            if piece_data["in_place"]:
                # Piece is already in place, stay there
                commands[robot_id] = ((0.0, 0.0), 0.0)
                continue

            # Decide on target: piece location or target location
            if current_pos.distance_to(piece_data["position"]) > 0.1:
                # Go to piece first
                target_pos = piece_data["position"]
            else:
                # Then take piece to target position
                target_pos = self.game_state["target_positions"][assigned_piece]

            # Calculate position error
            dx = target_pos.x - current_pos.x
            dy = target_pos.y - current_pos.y
            distance = math.sqrt(dx**2 + dy**2)

            # Calculate orientation to target
            target_orient = math.atan2(dy, dx)
            current_orient = state.pose.orientation
            orient_diff = target_orient - current_orient

            # Normalize to [-pi, pi]
            while orient_diff > math.pi:
                orient_diff -= 2 * math.pi
            while orient_diff < -math.pi:
                orient_diff += 2 * math.pi

            # Proportional controller for position
            kp_pos = 0.5  # Position gain
            vx = kp_pos * dx
            vy = kp_pos * dy

            # Limit velocity
            max_linear_speed = 0.3  # m/s
            v_mag = math.sqrt(vx**2 + vy**2)
            if v_mag > max_linear_speed:
                scale = max_linear_speed / v_mag
                vx *= scale
                vy *= scale

            # Proportional controller for orientation
            kp_orient = 1.0
            angular_v = kp_orient * orient_diff

            # Limit angular velocity
            max_angular_speed = math.pi / 2  # rad/s
            if abs(angular_v) > max_angular_speed:
                angular_v = max_angular_speed if angular_v > 0 else -max_angular_speed

            commands[robot_id] = ((vx, vy), angular_v)

        return commands

    def update_game_state(self, updates: Dict[str, Any]) -> None:
        """
        Update game state with external updates.
        Args:
            updates: Dictionary of state updates
        """
        self.game_state.update(updates)

    def is_game_complete(self) -> bool:
        """
        Check if the game is complete.
        Returns True if the game is complete.
        """
        if self.game_type == self.GameType.SOCCER:
            # Game is complete when one team reaches a certain score
            return (
                self.game_state["goals"]["team_a"] >= 5
                or self.game_state["goals"]["team_b"] >= 5
            )

        elif self.game_type == self.GameType.RELAY_RACE:
            # Game is complete when all laps are done
            return self.game_state["lap_count"] >= self.game_state["max_laps"]

        elif self.game_type == self.GameType.COOPERATIVE_PUZZLE:
            # Game is complete when all puzzle pieces are in place
            return all(
                piece["in_place"] for piece in self.game_state["puzzle_pieces"].values()
            )

        return False
