#!/usr/bin/env python3
"""
Multi-Robot Coordination Demo
============================

This script demonstrates the multi-robot coordination capabilities
of PathfinderBot by simulating multiple robots and running the coordination dashboard.

To run:
    python coordination_demo.py
"""

import time
import threading
import random
import math
import logging
from pathfinder_pkg.coordination import (
    Position,
    Pose,
    RobotState,
    Task,
    TaskPriority,
    CoordinationServer,
    launch_dashboard,
)

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("CoordinationDemo")


class SimulatedRobot:
    """Simulates a robot for demonstration purposes."""

    def __init__(self, robot_id, initial_pose=None):
        self.robot_id = robot_id
        self.pose = initial_pose or Pose(
            Position(random.uniform(-5, 5), random.uniform(-5, 5)),
            random.uniform(0, 2 * math.pi),
        )
        self.velocity = (0.0, 0.0)
        self.angular_velocity = 0.0
        self.battery_level = random.uniform(0.7, 1.0)
        self.capabilities = ["move", "sense"]
        self.current_task = None
        self.stop_event = threading.Event()

        # Add random capabilities
        if random.random() > 0.5:
            self.capabilities.append("lift")
        if random.random() > 0.7:
            self.capabilities.append("camera")

        self.state = RobotState(
            robot_id=self.robot_id,
            pose=self.pose,
            velocity=self.velocity,
            angular_velocity=self.angular_velocity,
            capabilities=self.capabilities,
            current_task=self.current_task,
            battery_level=self.battery_level,
        )

    def start(self):
        """Start the robot simulation thread."""
        self.thread = threading.Thread(target=self._run_loop, daemon=True)
        self.thread.start()

    def stop(self):
        """Stop the robot simulation."""
        self.stop_event.set()
        self.thread.join(timeout=1.0)

    def _run_loop(self):
        """Main robot simulation loop."""
        update_interval = 0.1  # seconds

        while not self.stop_event.is_set():
            # Simulate movement
            self._update_position(update_interval)

            # Update state
            self._update_state()

            # Simulate battery drain
            self.battery_level = max(0.0, self.battery_level - 0.0001)

            time.sleep(update_interval)

    def _update_position(self, dt):
        """Update robot position based on current velocity."""
        # Simple physics update
        vx, vy = self.velocity
        self.pose.position.x += vx * dt
        self.pose.position.y += vy * dt
        self.pose.orientation += self.angular_velocity * dt

        # Normalize orientation to [0, 2π]
        self.pose.orientation = self.pose.orientation % (2 * math.pi)

        # Random changes to velocity
        if random.random() < 0.05:
            self.velocity = (random.uniform(-0.2, 0.2), random.uniform(-0.2, 0.2))
            self.angular_velocity = random.uniform(-0.1, 0.1)

    def _update_state(self):
        """Update the robot state object."""
        self.state = RobotState(
            robot_id=self.robot_id,
            pose=self.pose,
            velocity=self.velocity,
            angular_velocity=self.angular_velocity,
            capabilities=self.capabilities,
            current_task=self.current_task,
            battery_level=self.battery_level,
        )

    def set_task(self, task_id):
        """Set the current task for this robot."""
        self.current_task = task_id
        logger.info(f"Robot {self.robot_id} assigned to task {task_id}")


class DemoCoordinationServer(CoordinationServer):
    """Extended coordination server for demo purposes."""

    def __init__(self):
        super().__init__(server_port=9000)
        self.simulated_robots = {}
        self.tasks = {}

    def add_robot(self, robot):
        """Add a simulated robot to the server."""
        self.simulated_robots[robot.robot_id] = robot

    def add_task(self, task):
        """Add a task to the server."""
        self.tasks[task.task_id] = task
        logger.info(f"Added task {task.task_id}: {task.task_type}")

    def start(self):
        """Start the coordination server."""
        super().start()
        # Start robot simulations
        for robot in self.simulated_robots.values():
            robot.start()

    def stop(self):
        """Stop the coordination server."""
        super().stop()
        # Stop robot simulations
        for robot in self.simulated_robots.values():
            robot.stop()

    def get_connected_robots(self):
        """Get a list of connected robot IDs."""
        return list(self.simulated_robots.keys())

    def get_robot_state(self, robot_id):
        """Get the current state of a robot."""
        if robot_id in self.simulated_robots:
            return self.simulated_robots[robot_id].state
        return None


def create_demo_tasks():
    """Create some demo tasks."""
    tasks = [
        Task(
            task_id="task1",
            task_type="patrol",
            priority=TaskPriority.MEDIUM,
            required_capabilities=["move"],
            location=Position(2.0, 3.0),
            deadline=time.time() + 600,
        ),
        Task(
            task_id="task2",
            task_type="transport",
            priority=TaskPriority.HIGH,
            required_capabilities=["move", "lift"],
            location=Position(-3.0, 2.0),
            deadline=time.time() + 300,
        ),
        Task(
            task_id="task3",
            task_type="observe",
            priority=TaskPriority.LOW,
            required_capabilities=["camera"],
            location=Position(0.0, -4.0),
            deadline=time.time() + 1200,
        ),
        Task(
            task_id="task4",
            task_type="coverage",
            priority=TaskPriority.HIGH,
            required_capabilities=["move", "sense"],
            location=Position(-2.0, -2.0),
            deadline=time.time() + 450,
        ),
    ]
    return tasks


def main():
    """Main function to run the coordination demo."""
    # Create the coordination server
    server = DemoCoordinationServer()

    # Create simulated robots
    for i in range(5):
        robot = SimulatedRobot(f"robot{i+1}")
        server.add_robot(robot)

    # Create tasks
    tasks = create_demo_tasks()
    for task in tasks:
        server.add_task(task)

    # Start the server and robot simulations
    server.start()
    logger.info("Coordination server started with 5 simulated robots")

    try:
        # Launch the dashboard
        launch_dashboard(server)
    except Exception as e:
        logger.error(f"Error in dashboard: {e}")
    finally:
        # Stop everything
        server.stop()
        logger.info("Coordination server stopped")


if __name__ == "__main__":
    main()
