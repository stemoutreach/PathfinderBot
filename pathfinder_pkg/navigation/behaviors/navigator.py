"""
Navigator module for PathfinderBot.

This module provides high-level navigation behaviors that use path planning,
localization, and SLAM to move the robot through its environment.
"""

import time
import math
import numpy as np
from typing import List, Optional, Dict, Any, Tuple, Union, Callable
from enum import Enum
import threading

from pathfinder_pkg.utils.logging import get_logger
from pathfinder_pkg.navigation.map import OccupancyGridMap
from pathfinder_pkg.navigation.localization import Pose
from pathfinder_pkg.navigation.slam.slam import SLAM
from pathfinder_pkg.navigation.path_planning.planner import PathPlanner, Waypoint
from pathfinder_pkg.navigation.path_planning.a_star import AStarPlanner
from pathfinder_pkg.navigation.path_planning.planner import (
    SimplePlanner,
    PotentialFieldPlanner,
)

logger = get_logger(__name__)


class NavigationStatus(Enum):
    """Status of the navigation process."""

    IDLE = 0
    PLANNING = 1
    MOVING = 2
    PAUSED = 3
    SUCCEEDED = 4
    FAILED = 5
    CANCELLED = 6


class NavigationController:
    """
    High-level navigation controller for the robot.

    This class provides methods for planning and executing navigation tasks,
    with support for different planning algorithms, obstacle avoidance, and
    path replanning.
    """

    def __init__(
        self,
        slam_system: SLAM,
        robot_controller: Any,  # This would be replaced with actual robot controller type
        default_planner: str = "a_star",
        planning_rate: float = 1.0,
        control_rate: float = 10.0,
        replanning_threshold: float = 0.5,
        obstacle_threshold: float = 0.2,
        goal_tolerance_position: float = 0.1,
        goal_tolerance_angle: float = 0.1,
    ):
        """
        Initialize the navigation controller.

        Args:
            slam_system: SLAM system for localization and mapping
            robot_controller: Controller for the robot hardware
            default_planner: Default planning algorithm to use
            planning_rate: Rate for path planning updates (Hz)
            control_rate: Rate for control loop updates (Hz)
            replanning_threshold: Distance threshold for replanning (meters)
            obstacle_threshold: Distance threshold for obstacle avoidance (meters)
            goal_tolerance_position: Position tolerance for reaching the goal (meters)
            goal_tolerance_angle: Orientation tolerance for reaching the goal (radians)
        """
        self.slam = slam_system
        self.robot_controller = robot_controller
        self.default_planner_name = default_planner
        self.planning_rate = planning_rate
        self.control_rate = control_rate
        self.replanning_threshold = replanning_threshold
        self.obstacle_threshold = obstacle_threshold
        self.goal_tolerance_position = goal_tolerance_position
        self.goal_tolerance_angle = goal_tolerance_angle

        # Initialize planners
        self.planners = {
            "simple": SimplePlanner(),
            "potential_field": PotentialFieldPlanner(),
            "a_star": AStarPlanner(),
        }

        # Current navigation state
        self.current_pose: Optional[Pose] = None
        self.current_path: List[Waypoint] = []
        self.current_waypoint_index = 0
        self.goal_pose: Optional[Pose] = None
        self.navigation_status = NavigationStatus.IDLE

        # Control threads
        self.planning_thread: Optional[threading.Thread] = None
        self.control_thread: Optional[threading.Thread] = None
        self._stop_threads = False

        # Callback for status changes
        self.status_callback: Optional[Callable[[NavigationStatus], None]] = None

        logger.info("Navigation controller initialized")

    def set_status_callback(self, callback: Callable[[NavigationStatus], None]) -> None:
        """
        Set a callback function for navigation status changes.

        Args:
            callback: Function to call when navigation status changes
        """
        self.status_callback = callback

    def _update_status(self, status: NavigationStatus) -> None:
        """
        Update the navigation status and trigger callback if registered.

        Args:
            status: New navigation status
        """
        self.navigation_status = status
        if self.status_callback:
            self.status_callback(status)
        logger.info(f"Navigation status changed to {status.name}")

    def get_current_pose(self) -> Optional[Pose]:
        """
        Get the current pose of the robot from SLAM system.

        Returns:
            Current pose or None if not available
        """
        return self.slam.get_pose()

    def navigate_to_pose(
        self,
        goal_pose: Pose,
        planner: str = None,
        planning_params: Dict[str, Any] = None,
    ) -> bool:
        """
        Navigate to a target pose.

        Args:
            goal_pose: Goal pose to reach
            planner: Name of the planner to use (default: use default planner)
            planning_params: Additional parameters for the planner

        Returns:
            True if navigation was started successfully, False otherwise
        """
        # Get current pose
        self.current_pose = self.get_current_pose()
        if not self.current_pose:
            logger.error("Cannot navigate: Current pose is unknown")
            return False

        # Set goal
        self.goal_pose = goal_pose

        # Select planner
        planner_name = planner if planner else self.default_planner_name
        if planner_name not in self.planners:
            logger.error(f"Unknown planner: {planner_name}, using default")
            planner_name = self.default_planner_name

        selected_planner = self.planners[planner_name]
        logger.info(f"Using {planner_name} planner for navigation")

        # Initialize planning parameters
        self.planning_params = planning_params or {}

        # Reset navigation state
        self.current_path = []
        self.current_waypoint_index = 0
        self._stop_threads = False

        # Update status
        self._update_status(NavigationStatus.PLANNING)

        # Start planning and control threads
        self.planning_thread = threading.Thread(
            target=self._planning_loop, args=(selected_planner,), daemon=True
        )
        self.planning_thread.start()

        self.control_thread = threading.Thread(target=self._control_loop, daemon=True)
        self.control_thread.start()

        return True

    def _planning_loop(self, planner: PathPlanner) -> None:
        """
        Background thread for path planning and replanning.

        Args:
            planner: Path planner to use
        """
        logger.info("Planning thread started")

        while not self._stop_threads:
            try:
                # Get current map and pose
                current_map = self.slam.get_map()
                current_pose = self.get_current_pose()

                if not current_pose or not self.goal_pose:
                    logger.warning("Missing current or goal pose, skipping planning")
                    time.sleep(1.0 / self.planning_rate)
                    continue

                # Plan path
                logger.info(
                    f"Planning path from ({current_pose.x:.2f}, {current_pose.y:.2f}) to ({self.goal_pose.x:.2f}, {self.goal_pose.y:.2f})"
                )
                path = planner.plan_path(
                    map_data=current_map,
                    start_pose=current_pose,
                    goal_pose=self.goal_pose,
                    **self.planning_params,
                )

                if not path:
                    logger.warning("Failed to plan path")
                    self._update_status(NavigationStatus.FAILED)
                    break

                # Update path
                self.current_path = path
                self.current_waypoint_index = 0
                logger.info(f"Path planned with {len(path)} waypoints")

                # If this is the first plan, update status to MOVING
                if self.navigation_status == NavigationStatus.PLANNING:
                    self._update_status(NavigationStatus.MOVING)

                # Sleep until next planning cycle
                time.sleep(1.0 / self.planning_rate)

            except Exception as e:
                logger.error(f"Error in planning loop: {e}")
                self._update_status(NavigationStatus.FAILED)
                break

    def _control_loop(self) -> None:
        """Background thread for path following and control."""
        logger.info("Control thread started")

        while not self._stop_threads:
            try:
                # Check if we have a path
                if not self.current_path:
                    time.sleep(1.0 / self.control_rate)
                    continue

                # Get current pose
                current_pose = self.get_current_pose()
                if not current_pose:
                    logger.warning("Lost localization during navigation")
                    time.sleep(1.0 / self.control_rate)
                    continue

                # Check if we've reached the goal
                if self._check_goal_reached(current_pose):
                    logger.info("Goal reached")
                    self._update_status(NavigationStatus.SUCCEEDED)
                    break

                # Get current waypoint
                if self.current_waypoint_index >= len(self.current_path):
                    logger.warning("Reached end of path without hitting goal")
                    self._update_status(NavigationStatus.FAILED)
                    break

                current_waypoint = self.current_path[self.current_waypoint_index]

                # Check if we've reached the current waypoint
                if current_waypoint.is_reached(current_pose):
                    logger.debug(f"Reached waypoint {self.current_waypoint_index}")
                    self.current_waypoint_index += 1
                    continue

                # Navigate to current waypoint
                self._navigate_to_waypoint(current_pose, current_waypoint)

                # Sleep until next control cycle
                time.sleep(1.0 / self.control_rate)

            except Exception as e:
                logger.error(f"Error in control loop: {e}")
                self._update_status(NavigationStatus.FAILED)
                break

    def _navigate_to_waypoint(self, current_pose: Pose, waypoint: Waypoint) -> None:
        """
        Navigate to the current waypoint.

        Args:
            current_pose: Current robot pose
            waypoint: Target waypoint
        """
        # Calculate distance and angle to waypoint
        dx = waypoint.x - current_pose.x
        dy = waypoint.y - current_pose.y
        distance = math.sqrt(dx * dx + dy * dy)
        target_angle = math.atan2(dy, dx)

        # Calculate the angle difference (shortest path)
        angle_diff = (target_angle - current_pose.theta + math.pi) % (
            2 * math.pi
        ) - math.pi

        # Determine linear and angular velocity
        max_linear_velocity = 0.5  # m/s
        max_angular_velocity = 1.0  # rad/s

        # Scale velocities based on distance/angle to waypoint
        linear_velocity = max(0.1, min(max_linear_velocity, distance))
        angular_velocity = max_angular_velocity * (angle_diff / math.pi)

        # If the angle is too large, prioritize turning
        if abs(angle_diff) > 0.5:  # ~30 degrees
            linear_velocity *= 0.5

        # Send command to robot controller
        self._send_velocity_command(linear_velocity, angular_velocity)

    def _send_velocity_command(
        self, linear_velocity: float, angular_velocity: float
    ) -> None:
        """
        Send velocity command to the robot controller.

        Args:
            linear_velocity: Linear velocity in m/s
            angular_velocity: Angular velocity in rad/s
        """
        # This would be replaced with actual robot controller interface
        logger.debug(
            f"Sending velocity command: linear={linear_velocity:.2f}, angular={angular_velocity:.2f}"
        )

        # Simulated robot controller interface
        if hasattr(self.robot_controller, "set_velocity"):
            self.robot_controller.set_velocity(linear_velocity, angular_velocity)

    def _check_goal_reached(self, current_pose: Pose) -> bool:
        """
        Check if the goal has been reached.

        Args:
            current_pose: Current robot pose

        Returns:
            True if goal reached, False otherwise
        """
        if not self.goal_pose:
            return False

        # Calculate position distance
        dx = self.goal_pose.x - current_pose.x
        dy = self.goal_pose.y - current_pose.y
        distance = math.sqrt(dx * dx + dy * dy)

        # Calculate orientation difference
        angle_diff = abs(
            (current_pose.theta - self.goal_pose.theta + math.pi) % (2 * math.pi)
            - math.pi
        )

        # Check if within tolerance
        position_reached = distance <= self.goal_tolerance_position
        orientation_reached = angle_diff <= self.goal_tolerance_angle

        return position_reached and orientation_reached

    def pause(self) -> None:
        """Pause the navigation."""
        if self.navigation_status == NavigationStatus.MOVING:
            self._update_status(NavigationStatus.PAUSED)
            # Stop the robot
            self._send_velocity_command(0.0, 0.0)

    def resume(self) -> None:
        """Resume the navigation after pausing."""
        if self.navigation_status == NavigationStatus.PAUSED:
            self._update_status(NavigationStatus.MOVING)

    def cancel(self) -> None:
        """Cancel the current navigation task."""
        self._stop_threads = True

        # Stop the robot
        self._send_velocity_command(0.0, 0.0)

        # Update status
        self._update_status(NavigationStatus.CANCELLED)

        # Wait for threads to terminate
        if self.planning_thread and self.planning_thread.is_alive():
            self.planning_thread.join(timeout=1.0)
        if self.control_thread and self.control_thread.is_alive():
            self.control_thread.join(timeout=1.0)

    def is_navigating(self) -> bool:
        """
        Check if the robot is currently navigating.

        Returns:
            True if robot is navigating (planning, moving, paused), False otherwise
        """
        return self.navigation_status in [
            NavigationStatus.PLANNING,
            NavigationStatus.MOVING,
            NavigationStatus.PAUSED,
        ]


class NavigationTask:
    """
    A navigation task that can be added to a navigation queue.

    This class encapsulates a navigation goal and associated parameters.
    """

    def __init__(
        self,
        goal_pose: Pose,
        planner: Optional[str] = None,
        planning_params: Optional[Dict[str, Any]] = None,
        on_complete: Optional[Callable[[NavigationStatus], None]] = None,
    ):
        """
        Initialize a navigation task.

        Args:
            goal_pose: Goal pose to navigate to
            planner: Planner to use (None for default)
            planning_params: Parameters for the planner
            on_complete: Callback function when the task completes
        """
        self.goal_pose = goal_pose
        self.planner = planner
        self.planning_params = planning_params or {}
        self.on_complete = on_complete
        self.status = NavigationStatus.IDLE

    def __str__(self) -> str:
        """String representation of the task."""
        return f"NavigationTask(goal=({self.goal_pose.x:.2f}, {self.goal_pose.y:.2f}, {self.goal_pose.theta:.2f}), status={self.status.name})"


class NavigationQueue:
    """
    A queue of navigation tasks to be executed sequentially.

    This class allows for planning and executing a sequence of navigation tasks.
    """

    def __init__(self, navigation_controller: NavigationController):
        """
        Initialize the navigation queue.

        Args:
            navigation_controller: Controller for executing navigation tasks
        """
        self.nav_controller = navigation_controller
        self.tasks: List[NavigationTask] = []
        self.current_task_index = -1
        self.is_running = False
        self._lock = threading.Lock()

        # Register status callback
        self.nav_controller.set_status_callback(self._on_navigation_status_changed)

    def add_task(self, task: NavigationTask) -> int:
        """
        Add a task to the queue.

        Args:
            task: Navigation task to add

        Returns:
            Index of the added task in the queue
        """
        with self._lock:
            self.tasks.append(task)
            task_index = len(self.tasks) - 1
            logger.info(f"Added task {task_index} to navigation queue: {task}")

            # Start execution if not already running
            if not self.is_running and self.current_task_index == -1:
                self._start_next_task()

            return task_index

    def add_goal(
        self,
        x: float,
        y: float,
        theta: Optional[float] = None,
        planner: Optional[str] = None,
        planning_params: Optional[Dict[str, Any]] = None,
        on_complete: Optional[Callable[[NavigationStatus], None]] = None,
    ) -> int:
        """
        Add a goal to the queue.

        Args:
            x: X coordinate in world frame
            y: Y coordinate in world frame
            theta: Orientation in world frame (optional)
            planner: Planner to use (None for default)
            planning_params: Parameters for the planner
            on_complete: Callback function when the task completes

        Returns:
            Index of the added task in the queue
        """
        # Create pose, using current orientation if not specified
        if theta is None:
            current_pose = self.nav_controller.get_current_pose()
            if current_pose:
                theta = current_pose.theta
            else:
                theta = 0.0

        goal_pose = Pose(x, y, theta)
        task = NavigationTask(
            goal_pose=goal_pose,
            planner=planner,
            planning_params=planning_params,
            on_complete=on_complete,
        )

        return self.add_task(task)

    def clear_queue(self) -> None:
        """Clear all tasks from the queue and cancel current navigation."""
        with self._lock:
            # Cancel current navigation
            if self.is_running:
                self.nav_controller.cancel()
                self.is_running = False

            # Clear queue
            self.tasks = []
            self.current_task_index = -1
            logger.info("Navigation queue cleared")

    def _start_next_task(self) -> bool:
        """
        Start the next task in the queue.

        Returns:
            True if a task was started, False if queue is empty
        """
        with self._lock:
            if not self.tasks or self.current_task_index >= len(self.tasks) - 1:
                self.is_running = False
                self.current_task_index = -1
                return False

            self.current_task_index += 1
            task = self.tasks[self.current_task_index]

            logger.info(f"Starting navigation task {self.current_task_index}: {task}")

            # Start navigation
            success = self.nav_controller.navigate_to_pose(
                goal_pose=task.goal_pose,
                planner=task.planner,
                planning_params=task.planning_params,
            )

            if success:
                task.status = NavigationStatus.PLANNING
                self.is_running = True
            else:
                logger.error(f"Failed to start task {self.current_task_index}")
                task.status = NavigationStatus.FAILED
                if task.on_complete:
                    task.on_complete(NavigationStatus.FAILED)
                # Try next task
                return self._start_next_task()

            return True

    def _on_navigation_status_changed(self, status: NavigationStatus) -> None:
        """
        Handle navigation status changes.

        Args:
            status: New navigation status
        """
        with self._lock:
            if not self.is_running or self.current_task_index < 0:
                return

            current_task = self.tasks[self.current_task_index]

            # Update task status
            current_task.status = status

            # Check for completion
            if status in [
                NavigationStatus.SUCCEEDED,
                NavigationStatus.FAILED,
                NavigationStatus.CANCELLED,
            ]:
                logger.info(
                    f"Task {self.current_task_index} completed with status {status.name}"
                )

                # Call task completion callback if provided
                if current_task.on_complete:
                    current_task.on_complete(status)

                # Move to next task if this one succeeded or failed (not cancelled)
                if status in [NavigationStatus.SUCCEEDED, NavigationStatus.FAILED]:
                    self._start_next_task()
