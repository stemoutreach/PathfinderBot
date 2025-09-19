"""
Coordination algorithms for multi-robot systems.
Implements task allocation, formation control, and collision avoidance.
"""

import numpy as np
import heapq
from typing import Dict, List, Tuple, Any, Optional, Callable
import logging
import math
import time
import random
from enum import Enum
from dataclasses import dataclass


class TaskPriority(Enum):
    """Priority levels for tasks"""

    LOW = 0
    MEDIUM = 1
    HIGH = 2
    CRITICAL = 3


@dataclass
class Position:
    """Position in 2D space."""

    x: float
    y: float

    def distance_to(self, other: "Position") -> float:
        """Calculate Euclidean distance between positions."""
        return math.sqrt((self.x - other.x) ** 2 + (self.y - other.y) ** 2)

    def to_tuple(self) -> Tuple[float, float]:
        """Convert position to tuple."""
        return (self.x, self.y)


@dataclass
class Pose:
    """Pose (position and orientation) in 2D space."""

    position: Position
    orientation: float  # radians

    def distance_to(self, other: "Pose") -> float:
        """Calculate Euclidean distance between poses."""
        return self.position.distance_to(other.position)

    def orientation_difference(self, other: "Pose") -> float:
        """Calculate the smallest angle between orientations."""
        diff = abs(self.orientation - other.orientation)
        return min(diff, 2 * math.pi - diff)


class Task:
    """Base class for robot tasks."""

    def __init__(
        self,
        task_id: str,
        task_type: str,
        priority: TaskPriority = TaskPriority.MEDIUM,
        required_capabilities: List[str] = None,
        estimated_duration: float = None,  # seconds
        location: Position = None,
        deadline: float = None,  # timestamp
    ):
        self.task_id = task_id
        self.task_type = task_type
        self.priority = priority
        self.required_capabilities = required_capabilities or []
        self.estimated_duration = estimated_duration
        self.location = location
        self.deadline = deadline

        self.assigned_robot = None
        self.status = "pending"  # pending, assigned, in_progress, completed, failed
        self.start_time = None
        self.completion_time = None
        self.progress = 0.0  # 0.0 to 1.0

    def to_dict(self) -> Dict[str, Any]:
        """Convert task to dictionary."""
        return {
            "task_id": self.task_id,
            "task_type": self.task_type,
            "priority": self.priority.name,
            "required_capabilities": self.required_capabilities,
            "estimated_duration": self.estimated_duration,
            "location": self.location.to_tuple() if self.location else None,
            "deadline": self.deadline,
            "assigned_robot": self.assigned_robot,
            "status": self.status,
            "start_time": self.start_time,
            "completion_time": self.completion_time,
            "progress": self.progress,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Task":
        """Create task from dictionary."""
        task = cls(
            task_id=data["task_id"],
            task_type=data["task_type"],
            priority=TaskPriority[data["priority"]],
            required_capabilities=data.get("required_capabilities"),
            estimated_duration=data.get("estimated_duration"),
            location=Position(*data["location"]) if data.get("location") else None,
            deadline=data.get("deadline"),
        )
        task.assigned_robot = data.get("assigned_robot")
        task.status = data.get("status", "pending")
        task.start_time = data.get("start_time")
        task.completion_time = data.get("completion_time")
        task.progress = data.get("progress", 0.0)
        return task

    def assign(self, robot_id: str):
        """Assign task to a robot."""
        self.assigned_robot = robot_id
        self.status = "assigned"

    def start(self):
        """Start task execution."""
        self.start_time = time.time()
        self.status = "in_progress"

    def complete(self):
        """Mark task as completed."""
        self.completion_time = time.time()
        self.status = "completed"
        self.progress = 1.0

    def fail(self):
        """Mark task as failed."""
        self.completion_time = time.time()
        self.status = "failed"

    def update_progress(self, progress: float):
        """Update task progress."""
        self.progress = max(0.0, min(1.0, progress))
        if self.progress >= 1.0:
            self.complete()


class RobotState:
    """Represents the state of a robot."""

    def __init__(
        self,
        robot_id: str,
        pose: Pose,
        velocity: Tuple[float, float] = (0.0, 0.0),  # vx, vy in m/s
        angular_velocity: float = 0.0,  # rad/s
        capabilities: List[str] = None,
        current_task: str = None,  # task_id
        battery_level: float = 1.0,  # 0.0 to 1.0
    ):
        self.robot_id = robot_id
        self.pose = pose
        self.velocity = velocity
        self.angular_velocity = angular_velocity
        self.capabilities = capabilities or []
        self.current_task = current_task
        self.battery_level = battery_level
        self.last_updated = time.time()

    def to_dict(self) -> Dict[str, Any]:
        """Convert robot state to dictionary."""
        return {
            "robot_id": self.robot_id,
            "pose": {
                "position": self.pose.position.to_tuple(),
                "orientation": self.pose.orientation,
            },
            "velocity": self.velocity,
            "angular_velocity": self.angular_velocity,
            "capabilities": self.capabilities,
            "current_task": self.current_task,
            "battery_level": self.battery_level,
            "last_updated": self.last_updated,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "RobotState":
        """Create robot state from dictionary."""
        pose_data = data["pose"]
        return cls(
            robot_id=data["robot_id"],
            pose=Pose(
                position=Position(*pose_data["position"]),
                orientation=pose_data["orientation"],
            ),
            velocity=data.get("velocity", (0.0, 0.0)),
            angular_velocity=data.get("angular_velocity", 0.0),
            capabilities=data.get("capabilities"),
            current_task=data.get("current_task"),
            battery_level=data.get("battery_level", 1.0),
        )

    def update_pose(self, pose: Pose):
        """Update robot pose."""
        self.pose = pose
        self.last_updated = time.time()

    def update_velocity(self, velocity: Tuple[float, float], angular_velocity: float):
        """Update robot velocity."""
        self.velocity = velocity
        self.angular_velocity = angular_velocity
        self.last_updated = time.time()

    def update_task(self, task_id: Optional[str]):
        """Update robot current task."""
        self.current_task = task_id
        self.last_updated = time.time()

    def is_idle(self) -> bool:
        """Check if robot is idle (not performing a task)."""
        return self.current_task is None

    def has_capability(self, capability: str) -> bool:
        """Check if robot has a specific capability."""
        return capability in self.capabilities

    def has_all_capabilities(self, capabilities: List[str]) -> bool:
        """Check if robot has all specified capabilities."""
        return all(capability in self.capabilities for capability in capabilities)

    def estimated_travel_time(self, target_position: Position) -> float:
        """Estimate travel time to a target position."""
        distance = self.pose.position.distance_to(target_position)
        # Assuming average speed of 0.5 m/s
        average_speed = 0.5
        return distance / average_speed


class TaskAllocator:
    """
    Allocates tasks to robots using auction-based algorithms.
    """

    def __init__(self, logger=None):
        self.tasks: Dict[str, Task] = {}
        self.robot_states: Dict[str, RobotState] = {}
        self.logger = logger or logging.getLogger("TaskAllocator")

    def add_task(self, task: Task) -> bool:
        """Add a task to the allocator."""
        if task.task_id in self.tasks:
            return False

        self.tasks[task.task_id] = task
        self.logger.info(f"Added task {task.task_id} of type {task.task_type}")
        return True

    def update_robot_state(self, robot_state: RobotState) -> None:
        """Update the state of a robot."""
        self.robot_states[robot_state.robot_id] = robot_state

    def get_available_robots(self) -> List[str]:
        """Get IDs of robots available for task allocation."""
        return [
            robot_id for robot_id, state in self.robot_states.items() if state.is_idle()
        ]

    def get_pending_tasks(self) -> List[str]:
        """Get IDs of pending tasks."""
        return [
            task_id for task_id, task in self.tasks.items() if task.status == "pending"
        ]

    def allocate_tasks(self) -> Dict[str, str]:
        """
        Allocate pending tasks to available robots using auction-based algorithm.
        Returns a mapping of task_id to robot_id.
        """
        allocations = {}
        pending_tasks = sorted(
            [self.tasks[task_id] for task_id in self.get_pending_tasks()],
            key=lambda t: t.priority.value,
            reverse=True,
        )
        available_robots = self.get_available_robots()

        if not pending_tasks or not available_robots:
            return allocations

        # Calculate bids (lower is better)
        bids = {}
        for robot_id in available_robots:
            robot_state = self.robot_states[robot_id]
            for task in pending_tasks:
                if robot_state.has_all_capabilities(task.required_capabilities):
                    # Calculate bid based on distance and battery level
                    distance_cost = 0
                    if task.location and robot_state.pose.position:
                        distance = robot_state.pose.position.distance_to(task.location)
                        distance_cost = distance * 2  # Weight factor for distance

                    # Battery penalty increases as battery depletes
                    battery_penalty = (1.0 - robot_state.battery_level) * 5

                    # Priority bonus (negative cost for high priority)
                    priority_bonus = -task.priority.value * 10

                    # Deadline pressure
                    deadline_pressure = 0
                    if task.deadline:
                        time_remaining = max(0, task.deadline - time.time())
                        if time_remaining > 0:
                            # Increase pressure as deadline approaches
                            deadline_pressure = -20 / time_remaining
                        else:
                            # Past deadline
                            deadline_pressure = -100

                    # Calculate final bid value
                    bid = (
                        distance_cost
                        + battery_penalty
                        + priority_bonus
                        + deadline_pressure
                    )

                    bids[(robot_id, task.task_id)] = bid

        # Greedy assignment based on bids
        assigned_robots = set()
        assigned_tasks = set()

        # Sort bids by value (lower is better)
        sorted_bids = sorted(bids.items(), key=lambda x: x[1])

        for (robot_id, task_id), bid in sorted_bids:
            if robot_id not in assigned_robots and task_id not in assigned_tasks:
                allocations[task_id] = robot_id
                assigned_robots.add(robot_id)
                assigned_tasks.add(task_id)

                # Update task status
                self.tasks[task_id].assign(robot_id)
                self.logger.info(f"Allocated task {task_id} to robot {robot_id}")

        return allocations

    def get_task_status(self, task_id: str) -> str:
        """Get the status of a specific task."""
        if task_id not in self.tasks:
            return "unknown"
        return self.tasks[task_id].status

    def complete_task(self, task_id: str) -> bool:
        """Mark a task as completed."""
        if task_id not in self.tasks:
            return False

        task = self.tasks[task_id]
        task.complete()

        # Update robot state
        if task.assigned_robot and task.assigned_robot in self.robot_states:
            robot_state = self.robot_states[task.assigned_robot]
            robot_state.update_task(None)

        self.logger.info(f"Task {task_id} completed")
        return True

    def fail_task(self, task_id: str, reason: str = None) -> bool:
        """Mark a task as failed."""
        if task_id not in self.tasks:
            return False

        task = self.tasks[task_id]
        task.fail()

        # Update robot state
        if task.assigned_robot and task.assigned_robot in self.robot_states:
            robot_state = self.robot_states[task.assigned_robot]
            robot_state.update_task(None)

        if reason:
            self.logger.warning(f"Task {task_id} failed: {reason}")
        else:
            self.logger.warning(f"Task {task_id} failed")
        return True

    def reassign_task(self, task_id: str) -> bool:
        """
        Reassign a task (e.g., if the previously assigned robot failed).
        Returns True if the task was successfully reassigned.
        """
        if task_id not in self.tasks:
            return False

        task = self.tasks[task_id]
        old_robot = task.assigned_robot

        # Reset task status
        task.assigned_robot = None
        task.status = "pending"

        # Update robot state if the old robot still exists
        if old_robot and old_robot in self.robot_states:
            robot_state = self.robot_states[old_robot]
            if robot_state.current_task == task_id:
                robot_state.update_task(None)

        # Attempt to allocate the task
        allocations = self.allocate_tasks()

        # Check if the task was reassigned
        was_reassigned = task_id in allocations

        if was_reassigned:
            new_robot = allocations[task_id]
            self.logger.info(
                f"Reassigned task {task_id} from robot {old_robot} to robot {new_robot}"
            )
        else:
            self.logger.warning(f"Failed to reassign task {task_id}")
            # If not reassigned, mark as pending again
            task.status = "pending"

        return was_reassigned


class FormationControl:
    """
    Controls robot formations for coordinated movement.
    """

    class FormationType(Enum):
        """Types of formations supported."""

        LINE = "line"
        COLUMN = "column"
        WEDGE = "wedge"
        ECHELON_LEFT = "echelon_left"
        ECHELON_RIGHT = "echelon_right"
        VEE = "vee"
        CIRCLE = "circle"
        GRID = "grid"

    def __init__(self):
        self.robots: Dict[str, RobotState] = {}
        self.formation_type = self.FormationType.LINE
        self.formation_center = Position(0, 0)
        self.formation_orientation = 0.0  # radians
        self.robot_spacing = 1.0  # meters
        self.leader_id = None
        self.logger = logging.getLogger("FormationControl")

    def set_formation(
        self,
        formation_type: FormationType,
        center: Position = None,
        orientation: float = None,
        spacing: float = None,
        leader_id: str = None,
    ) -> None:
        """Set the formation parameters."""
        self.formation_type = formation_type
        if center is not None:
            self.formation_center = center
        if orientation is not None:
            self.formation_orientation = orientation
        if spacing is not None:
            self.robot_spacing = spacing
        if leader_id is not None:
            self.leader_id = leader_id
            if leader_id in self.robots:
                # Update formation center to leader's position
                self.formation_center = self.robots[leader_id].pose.position

    def update_robot_state(self, robot_id: str, state: RobotState) -> None:
        """Update the state of a robot in the formation."""
        self.robots[robot_id] = state

        # If this is the leader, update the formation center
        if robot_id == self.leader_id:
            self.formation_center = state.pose.position
            self.formation_orientation = state.pose.orientation

    def get_formation_positions(self) -> Dict[str, Position]:
        """
        Calculate the target positions for each robot in the formation.
        Returns a mapping of robot_id to target position.
        """
        if not self.robots:
            return {}

        target_positions = {}
        robot_ids = list(self.robots.keys())

        # If leader specified, put at the front of the list
        if self.leader_id in self.robots:
            robot_ids.remove(self.leader_id)
            robot_ids.insert(0, self.leader_id)

        n_robots = len(robot_ids)

        # Cosine and sine of formation orientation
        cos_theta = math.cos(self.formation_orientation)
        sin_theta = math.sin(self.formation_orientation)

        if self.formation_type == self.FormationType.LINE:
            # Robots in a horizontal line, perpendicular to orientation
            for i, robot_id in enumerate(robot_ids):
                offset = (i - (n_robots - 1) / 2) * self.robot_spacing
                x = self.formation_center.x - offset * sin_theta
                y = self.formation_center.y + offset * cos_theta
                target_positions[robot_id] = Position(x, y)

        elif self.formation_type == self.FormationType.COLUMN:
            # Robots in a vertical line, parallel to orientation
            for i, robot_id in enumerate(robot_ids):
                offset = i * self.robot_spacing
                x = self.formation_center.x + offset * cos_theta
                y = self.formation_center.y + offset * sin_theta
                target_positions[robot_id] = Position(x, y)

        elif self.formation_type == self.FormationType.WEDGE:
            # Wedge formation (V shape pointing forward)
            for i, robot_id in enumerate(robot_ids):
                if i == 0:  # Leader at the point
                    target_positions[robot_id] = Position(
                        self.formation_center.x,
                        self.formation_center.y,
                    )
                else:
                    row = (i - 1) // 2 + 1
                    col = -1 if (i % 2 == 1) else 1
                    offset_x = (
                        row * self.robot_spacing * cos_theta
                        - col * row * self.robot_spacing * sin_theta
                    )
                    offset_y = (
                        row * self.robot_spacing * sin_theta
                        + col * row * self.robot_spacing * cos_theta
                    )
                    target_positions[robot_id] = Position(
                        self.formation_center.x + offset_x,
                        self.formation_center.y + offset_y,
                    )

        elif self.formation_type == self.FormationType.ECHELON_LEFT:
            # Left echelon formation
            for i, robot_id in enumerate(robot_ids):
                x = (
                    self.formation_center.x
                    + i * self.robot_spacing * cos_theta
                    - i * self.robot_spacing * sin_theta
                )
                y = (
                    self.formation_center.y
                    + i * self.robot_spacing * sin_theta
                    + i * self.robot_spacing * cos_theta
                )
                target_positions[robot_id] = Position(x, y)

        elif self.formation_type == self.FormationType.ECHELON_RIGHT:
            # Right echelon formation
            for i, robot_id in enumerate(robot_ids):
                x = (
                    self.formation_center.x
                    + i * self.robot_spacing * cos_theta
                    + i * self.robot_spacing * sin_theta
                )
                y = (
                    self.formation_center.y
                    + i * self.robot_spacing * sin_theta
                    - i * self.robot_spacing * cos_theta
                )
                target_positions[robot_id] = Position(x, y)

        elif self.formation_type == self.FormationType.VEE:
            # Vee formation (V shape pointing backward)
            for i, robot_id in enumerate(robot_ids):
                if i == 0:  # Leader at the front
                    target_positions[robot_id] = Position(
                        self.formation_center.x,
                        self.formation_center.y,
                    )
                else:
                    row = (i - 1) // 2 + 1
                    col = 1 if (i % 2 == 1) else -1
                    offset_x = (
                        row * self.robot_spacing * cos_theta
                        - col * row * self.robot_spacing * sin_theta
                    )
                    offset_y = (
                        row * self.robot_spacing * sin_theta
                        + col * row * self.robot_spacing * cos_theta
                    )
                    target_positions[robot_id] = Position(
                        self.formation_center.x + offset_x,
                        self.formation_center.y + offset_y,
                    )

        elif self.formation_type == self.FormationType.CIRCLE:
            # Circle formation
            radius = self.robot_spacing
            for i, robot_id in enumerate(robot_ids):
                angle = 2 * math.pi * i / n_robots
                x = self.formation_center.x + radius * math.cos(angle)
                y = self.formation_center.y + radius * math.sin(angle)
                target_positions[robot_id] = Position(x, y)

        elif self.formation_type == self.FormationType.GRID:
            # Grid formation
            side_length = math.ceil(math.sqrt(n_robots))
            for i, robot_id in enumerate(robot_ids):
                row = i // side_length
                col = i % side_length
                center_offset = (side_length - 1) / 2
                offset_x = (col - center_offset) * self.robot_spacing
                offset_y = (row - center_offset) * self.robot_spacing
                x = (
                    self.formation_center.x
                    + offset_x * cos_theta
                    - offset_y * sin_theta
                )
                y = (
                    self.formation_center.y
                    + offset_x * sin_theta
                    + offset_y * cos_theta
                )
                target_positions[robot_id] = Position(x, y)

        return target_positions

    def calculate_formation_error(self) -> Dict[str, float]:
        """
        Calculate the error between current and target positions.
        Returns a mapping of robot_id to error distance.
        """
        target_positions = self.get_formation_positions()
        errors = {}

        for robot_id, target_pos in target_positions.items():
            if robot_id in self.robots:
                current_pos = self.robots[robot_id].pose.position
                error = current_pos.distance_to(target_pos)
                errors[robot_id] = error

        return errors

    def get_velocity_commands(self) -> Dict[str, Tuple[Tuple[float, float], float]]:
        """
        Calculate velocity commands for each robot to maintain formation.
        Returns a mapping of robot_id to (linear_velocity, angular_velocity).
        Linear velocity is a tuple (vx, vy) in m/s, angular velocity in rad/s.
        """
        target_positions = self.get_formation_positions()
        commands = {}

        max_linear_speed = 0.5  # m/s
        max_angular_speed = math.pi / 2  # rad/s

        for robot_id, target_pos in target_positions.items():
            if robot_id in self.robots:
                robot_state = self.robots[robot_id]
                current_pos = robot_state.pose.position
                current_orient = robot_state.pose.orientation

                # Calculate position error
                dx = target_pos.x - current_pos.x
                dy = target_pos.y - current_pos.y
                distance = math.sqrt(dx * dx + dy * dy)

                # Calculate orientation error
                target_orient = self.formation_orientation
                orient_diff = target_orient - current_orient
                while orient_diff > math.pi:
                    orient_diff -= 2 * math.pi
                while orient_diff < -math.pi:
                    orient_diff += 2 * math.pi

                # Calculate proportional control commands
                # For position
                kp_pos = 0.5  # Proportional gain for position
                vx = kp_pos * dx
                vy = kp_pos * dy

                # Limit linear velocity
                v_mag = math.sqrt(vx * vx + vy * vy)
                if v_mag > max_linear_speed:
                    scale = max_linear_speed / v_mag
                    vx *= scale
                    vy *= scale

                # For orientation
                kp_orient = 1.0  # Proportional gain for orientation
                angular_v = kp_orient * orient_diff

                # Limit angular velocity
                if abs(angular_v) > max_angular_speed:
                    angular_v = (
                        max_angular_speed if angular_v > 0 else -max_angular_speed
                    )

                # Don't move if already at target position
                if distance < 0.05:  # 5 cm threshold
                    vx, vy = 0.0, 0.0

                # Don't rotate if already at target orientation
                if abs(orient_diff) < 0.05:  # ~3 degrees threshold
                    angular_v = 0.0

                commands[robot_id] = ((vx, vy), angular_v)

        return commands

    def maintain_formation(self) -> Dict[str, Tuple[Tuple[float, float], float]]:
        """Calculate commands for all robots to maintain the formation."""
        # Update formation center if leader is moving
        if self.leader_id in self.robots:
            leader_state = self.robots[self.leader_id]
            self.formation_center = leader_state.pose.position
            self.formation_orientation = leader_state.pose.orientation

        return self.get_velocity_commands()


class CollisionAvoidance:
    """
    Handles collision avoidance between robots.
    Uses velocity obstacles approach to avoid collisions while robots move.
    """

    def __init__(self, safety_distance: float = 0.3):
        self.robots: Dict[str, RobotState] = {}
        self.safety_distance = safety_distance  # meters
        self.logger = logging.getLogger("CollisionAvoidance")

    def update_robot_state(self, robot_id: str, state: RobotState) -> None:
        """Update the state of a robot."""
        self.robots[robot_id] = state

    def check_collision_risk(self, robot_id1: str, robot_id2: str) -> bool:
        """
        Check if there is a risk of collision between two robots.
        Returns True if the robots are at risk of collision.
        """
        if robot_id1 not in self.robots or robot_id2 not in self.robots:
            return False

        robot1 = self.robots[robot_id1]
        robot2 = self.robots[robot_id2]

        # Calculate distance between robots
        distance = robot1.pose.position.distance_to(robot2.pose.position)

        # Check if robots are too close
        if distance < self.safety_distance:
            return True

        # Calculate relative velocity
        vx1, vy1 = robot1.velocity
        vx2, vy2 = robot2.velocity
        rel_vx = vx1 - vx2
        rel_vy = vy1 - vy2

        # Calculate time to closest approach
        x1, y1 = robot1.pose.position.x, robot1.pose.position.y
        x2, y2 = robot2.pose.position.x, robot2.pose.position.y
        dx = x2 - x1
        dy = y2 - y1

        # Check if robots are moving toward each other
        dot_product = dx * rel_vx + dy * rel_vy
        if dot_product >= 0:
            # Not approaching each other
            return False

        # Calculate closest approach distance
        rel_v_squared = rel_vx * rel_vx + rel_vy * rel_vy
        if rel_v_squared < 1e-6:  # Almost stationary relative to each other
            return False

        # Time to closest approach
        t_closest = -dot_product / rel_v_squared

        # Check if closest approach is in the future
        if t_closest < 0:
            return False

        # Check if closest approach happens within 3 seconds
        if t_closest > 3.0:
            return False

        # Calculate closest approach distance
        closest_x = x1 + vx1 * t_closest - (x2 + vx2 * t_closest)
        closest_y = y1 + vy1 * t_closest - (y2 + vy2 * t_closest)
        closest_distance = math.sqrt(closest_x * closest_x + closest_y * closest_y)

        # Check if closest approach distance is less than safety distance
        return closest_distance < self.safety_distance

    def get_avoidance_velocity(
        self, robot_id: str, desired_velocity: Tuple[float, float]
    ) -> Tuple[float, float]:
        """
        Calculate a safe velocity that avoids collisions.
        Args:
            robot_id: ID of the robot to calculate avoidance for
            desired_velocity: The velocity the robot wants to move at (vx, vy)

        Returns:
            A safe velocity that avoids collisions (vx, vy)
        """
        if robot_id not in self.robots:
            return desired_velocity

        robot = self.robots[robot_id]

        # If no other robots, just return the desired velocity
        if len(self.robots) <= 1:
            return desired_velocity

        # Check for collision risks with other robots
        collision_risks = []
        for other_id, other_robot in self.robots.items():
            if other_id == robot_id:
                continue

            if self.check_collision_risk(robot_id, other_id):
                collision_risks.append(other_id)

        # If no collision risks, return the desired velocity
        if not collision_risks:
            return desired_velocity

        # Calculate avoidance velocity using velocity obstacles
        vx_desired, vy_desired = desired_velocity
        vx_safe, vy_safe = vx_desired, vy_desired

        for other_id in collision_risks:
            other_robot = self.robots[other_id]

            # Calculate relative position
            dx = other_robot.pose.position.x - robot.pose.position.x
            dy = other_robot.pose.position.y - robot.pose.position.y
            distance = math.sqrt(dx * dx + dy * dy)

            # Normalize direction vector from robot to other robot
            if distance > 0:
                nx = dx / distance
                ny = dy / distance
            else:
                # If robots are at the same position, use a random direction
                angle = random.uniform(0, 2 * math.pi)
                nx = math.cos(angle)
                ny = math.sin(angle)

            # Calculate repulsive velocity component
            # Strength increases as distance decreases
            strength = (
                max(0, self.safety_distance / distance - 0.5) if distance > 0 else 1.0
            )
            repulse_vx = -nx * strength
            repulse_vy = -ny * strength

            # Blend desired velocity with repulsive velocity
            blend_factor = min(1.0, strength)
            vx_safe = vx_safe * (1 - blend_factor) + repulse_vx * blend_factor
            vy_safe = vy_safe * (1 - blend_factor) + repulse_vy * blend_factor

        # Maintain the same speed as the desired velocity if possible
        desired_speed = math.sqrt(vx_desired * vx_desired + vy_desired * vy_desired)
        safe_speed = math.sqrt(vx_safe * vx_safe + vy_safe * vy_safe)

        if safe_speed > 0:
            vx_safe = vx_safe * desired_speed / safe_speed
            vy_safe = vy_safe * desired_speed / safe_speed

        return vx_safe, vy_safe

    def process_velocity_commands(
        self, velocity_commands: Dict[str, Tuple[Tuple[float, float], float]]
    ) -> Dict[str, Tuple[Tuple[float, float], float]]:
        """
        Process velocity commands to avoid collisions.
        Args:
            velocity_commands: A map of robot_id to ((vx, vy), angular_velocity)

        Returns:
            Modified velocity commands that avoid collisions
        """
        safe_commands = {}

        for robot_id, (linear_vel, angular_vel) in velocity_commands.items():
            # Apply collision avoidance to the linear velocity component
            safe_linear_vel = self.get_avoidance_velocity(robot_id, linear_vel)

            # Keep the original angular velocity
            safe_commands[robot_id] = (safe_linear_vel, angular_vel)

        return safe_commands
