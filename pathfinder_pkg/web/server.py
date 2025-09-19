"""
Web server for PathfinderBot navigation interface.

This module provides a Flask-based web server with WebSocket support
for real-time communication between the robot and web clients.
"""

import os
import time
import json
import threading
import logging
from typing import Dict, List, Optional, Any, Callable, Union
from flask import Flask, render_template, request, jsonify, send_from_directory
from flask_socketio import SocketIO, emit
import numpy as np
import base64

from pathfinder_pkg.utils.logging import get_logger
from pathfinder_pkg.navigation.map import OccupancyGridMap
from pathfinder_pkg.navigation.localization import Pose
from pathfinder_pkg.navigation.slam.slam import SLAM
from pathfinder_pkg.navigation.behaviors.navigator import (
    NavigationController,
    NavigationQueue,
    NavigationStatus,
)
from pathfinder_pkg.navigation.visualization.visualizer import WebVisualizer

# Initialize logger
logger = get_logger(__name__)

# Declare global variables
app = Flask(__name__)
app.config["SECRET_KEY"] = "pathfinderbot-secret!"
socketio = SocketIO(app, cors_allowed_origins="*", async_mode="threading")

# Global objects
slam_system: Optional[SLAM] = None
nav_controller: Optional[NavigationController] = None
nav_queue: Optional[NavigationQueue] = None
visualizer: Optional[WebVisualizer] = None
robot_controller: Optional[Any] = None  # This would be the actual robot controller

# Status tracking
update_interval: float = 0.5
status_thread: Optional[threading.Thread] = None
status_running: bool = False


class WebInterface:
    """
    Web interface manager for PathfinderBot.

    This class provides methods for initializing and controlling the web interface
    for the PathfinderBot navigation system.
    """

    def __init__(
        self,
        slam_system_instance: SLAM,
        navigation_controller: NavigationController,
        robot_ctrl: Any,
        host: str = "0.0.0.0",
        port: int = 5000,
        debug: bool = False,
        update_rate: float = 0.5,
    ):
        """
        Initialize the web interface.

        Args:
            slam_system_instance: SLAM system for localization and mapping
            navigation_controller: Navigation controller for robot movement
            robot_ctrl: Robot controller for direct hardware control
            host: Host address to bind the server to
            port: Port to run the server on
            debug: Whether to run in debug mode
            update_rate: Rate to update status information (seconds)
        """
        global slam_system, nav_controller, nav_queue, robot_controller, update_interval

        # Store global references
        slam_system = slam_system_instance
        nav_controller = navigation_controller
        robot_controller = robot_ctrl
        update_interval = update_rate

        # Create navigation queue
        nav_queue = NavigationQueue(nav_controller)

        # Create web visualizer
        global visualizer
        visualizer = WebVisualizer(
            slam_system=slam_system,
            navigation_controller=nav_controller,
            update_interval=update_rate,
            width=640,
            height=480,
        )

        # Store server parameters
        self.host = host
        self.port = port
        self.debug = debug

        # Initialize static directory
        static_dir = os.path.join(os.path.dirname(__file__), "static")
        if not os.path.exists(static_dir):
            os.makedirs(static_dir)

        # Initialize templates directory
        template_dir = os.path.join(os.path.dirname(__file__), "templates")
        if not os.path.exists(template_dir):
            os.makedirs(template_dir)

        logger.info(f"Web interface initialized at http://{host}:{port}")

    def start(self):
        """Start the web server and background threads."""
        # Start the status update thread
        self._start_status_updates()

        # Start the visualizer
        if visualizer:
            visualizer.start()

        # Start the web server
        socketio.run(app, host=self.host, port=self.port, debug=self.debug)

    def stop(self):
        """Stop the web server and background threads."""
        # Stop the status update thread
        self._stop_status_updates()

        # Stop the visualizer
        if visualizer:
            visualizer.stop()

    def _start_status_updates(self):
        """Start the status update thread."""
        global status_thread, status_running

        if status_thread and status_thread.is_alive():
            logger.warning("Status update thread is already running")
            return

        status_running = True
        status_thread = threading.Thread(target=_status_update_loop, daemon=True)
        status_thread.start()
        logger.info("Status update thread started")

    def _stop_status_updates(self):
        """Stop the status update thread."""
        global status_thread, status_running

        status_running = False
        if status_thread:
            status_thread.join(timeout=2.0)
        logger.info("Status update thread stopped")


def _status_update_loop():
    """Background thread function for sending status updates to clients."""
    global status_running, update_interval

    logger.info("Status update loop started")

    while status_running:
        try:
            # Get current status
            status_data = _get_current_status()

            # Send status to clients
            socketio.emit("status_update", status_data)

            # Send map image if available
            if visualizer:
                map_image = visualizer.get_current_frame()
                if map_image:
                    map_base64 = base64.b64encode(map_image).decode("utf-8")
                    socketio.emit("map_update", {"image": map_base64})

            # Sleep until next update
            time.sleep(update_interval)

        except Exception as e:
            logger.error(f"Error in status update loop: {e}")
            time.sleep(1.0)


def _get_current_status() -> Dict[str, Any]:
    """
    Get the current status of the robot.

    Returns:
        Dictionary with status information
    """
    status = {
        "timestamp": time.time(),
        "pose": None,
        "battery": None,
        "navigation": {
            "status": "IDLE",
            "goal": None,
            "path_length": 0,
            "distance_to_goal": None,
        },
        "sensors": {},
    }

    # Get pose if available
    if slam_system:
        pose = slam_system.get_pose()
        if pose:
            status["pose"] = {"x": pose.x, "y": pose.y, "theta": pose.theta}

    # Get battery status if available
    if robot_controller and hasattr(robot_controller, "get_battery_level"):
        status["battery"] = robot_controller.get_battery_level()
    else:
        # Mock battery level for testing
        status["battery"] = {"level": 85, "charging": False}

    # Get navigation status if available
    if nav_controller:
        nav_status = nav_controller.navigation_status.name
        status["navigation"]["status"] = nav_status

        # Get goal if available
        if nav_controller.goal_pose:
            status["navigation"]["goal"] = {
                "x": nav_controller.goal_pose.x,
                "y": nav_controller.goal_pose.y,
                "theta": nav_controller.goal_pose.theta,
            }

        # Get path length if available
        if hasattr(nav_controller, "current_path") and nav_controller.current_path:
            status["navigation"]["path_length"] = len(nav_controller.current_path)

        # Calculate distance to goal if both pose and goal are available
        if status["pose"] and status["navigation"]["goal"]:
            dx = status["navigation"]["goal"]["x"] - status["pose"]["x"]
            dy = status["navigation"]["goal"]["y"] - status["pose"]["y"]
            status["navigation"]["distance_to_goal"] = np.sqrt(dx * dx + dy * dy)

    # Get sensor data if available
    if robot_controller:
        # Sonar sensors
        if hasattr(robot_controller, "get_sonar_readings"):
            status["sensors"]["sonar"] = robot_controller.get_sonar_readings()

        # Camera status
        if hasattr(robot_controller, "get_camera_status"):
            status["sensors"]["camera"] = robot_controller.get_camera_status()

        # IMU data
        if hasattr(robot_controller, "get_imu_data"):
            status["sensors"]["imu"] = robot_controller.get_imu_data()

    return status


# Flask routes
@app.route("/")
def index():
    """Serve the main page."""
    return render_template("index.html")


@app.route("/static/<path:path>")
def serve_static(path):
    """Serve static files."""
    return send_from_directory("static", path)


@app.route("/api/status", methods=["GET"])
def get_status():
    """Get the current status of the robot."""
    return jsonify(_get_current_status())


@app.route("/api/map", methods=["GET"])
def get_map():
    """Get the current map."""
    if slam_system:
        grid_map = slam_system.get_map()
        if grid_map:
            return jsonify(
                {
                    "width": grid_map.width,
                    "height": grid_map.height,
                    "resolution": grid_map.resolution,
                    "origin_x": grid_map.origin_x,
                    "origin_y": grid_map.origin_y,
                    "grid": grid_map.get_grid().tolist(),
                }
            )

    return jsonify({"error": "Map not available"}), 404


@app.route("/api/waypoints", methods=["GET"])
def get_waypoints():
    """Get the current waypoints."""
    if nav_controller and hasattr(nav_controller, "current_path"):
        waypoints = []
        for wp in nav_controller.current_path:
            waypoints.append(
                {"x": wp.x, "y": wp.y, "theta": wp.theta, "action": wp.action}
            )
        return jsonify(waypoints)

    return jsonify([])


@app.route("/api/set_goal", methods=["POST"])
def set_goal():
    """Set a navigation goal."""
    data = request.json
    if not data:
        return jsonify({"error": "No data provided"}), 400

    # Extract goal coordinates
    x = data.get("x")
    y = data.get("y")
    theta = data.get("theta")

    if x is None or y is None:
        return jsonify({"error": "Missing coordinates"}), 400

    # Add goal to navigation queue
    if nav_queue:
        task_index = nav_queue.add_goal(x, y, theta)
        return jsonify(
            {
                "success": True,
                "task_index": task_index,
                "message": f"Goal added at ({x}, {y})",
            }
        )

    return jsonify({"error": "Navigation system not available"}), 503


@app.route("/api/cancel_navigation", methods=["POST"])
def cancel_navigation():
    """Cancel current navigation."""
    if nav_controller:
        nav_controller.cancel()
        return jsonify({"success": True, "message": "Navigation cancelled"})

    return jsonify({"error": "Navigation system not available"}), 503


@app.route("/api/clear_queue", methods=["POST"])
def clear_queue():
    """Clear the navigation queue."""
    if nav_queue:
        nav_queue.clear_queue()
        return jsonify({"success": True, "message": "Navigation queue cleared"})

    return jsonify({"error": "Navigation queue not available"}), 503


@app.route("/api/control/move", methods=["POST"])
def control_move():
    """Direct control of robot movement."""
    data = request.json
    if not data:
        return jsonify({"error": "No data provided"}), 400

    # Extract velocity commands
    linear_velocity = data.get("linear", 0.0)
    angular_velocity = data.get("angular", 0.0)

    # Send to robot controller
    if robot_controller and hasattr(robot_controller, "set_velocity"):
        robot_controller.set_velocity(linear_velocity, angular_velocity)
        return jsonify({"success": True})

    return jsonify({"error": "Robot controller not available"}), 503


# SocketIO events
@socketio.on("connect")
def handle_connect():
    """Handle client connection."""
    logger.info(f"Client connected: {request.sid}")


@socketio.on("disconnect")
def handle_disconnect():
    """Handle client disconnection."""
    logger.info(f"Client disconnected: {request.sid}")


@socketio.on("control_command")
def handle_control_command(data):
    """Handle control commands from clients."""
    command = data.get("command")
    params = data.get("params", {})

    if not command:
        emit("command_response", {"error": "No command specified"})
        return

    # Direct movement control
    if command == "move":
        linear = params.get("linear", 0.0)
        angular = params.get("angular", 0.0)

        if robot_controller and hasattr(robot_controller, "set_velocity"):
            robot_controller.set_velocity(linear, angular)
            emit("command_response", {"success": True, "command": command})
        else:
            emit("command_response", {"error": "Robot controller not available"})

    # Set navigation goal
    elif command == "set_goal":
        x = params.get("x")
        y = params.get("y")
        theta = params.get("theta")

        if x is None or y is None:
            emit("command_response", {"error": "Missing coordinates"})
            return

        if nav_queue:
            task_index = nav_queue.add_goal(x, y, theta)
            emit(
                "command_response",
                {"success": True, "command": command, "task_index": task_index},
            )
        else:
            emit("command_response", {"error": "Navigation queue not available"})

    # Cancel navigation
    elif command == "cancel_navigation":
        if nav_controller:
            nav_controller.cancel()
            emit("command_response", {"success": True, "command": command})
        else:
            emit("command_response", {"error": "Navigation controller not available"})

    # Clear navigation queue
    elif command == "clear_queue":
        if nav_queue:
            nav_queue.clear_queue()
            emit("command_response", {"success": True, "command": command})
        else:
            emit("command_response", {"error": "Navigation queue not available"})

    # Unknown command
    else:
        emit("command_response", {"error": f"Unknown command: {command}"})
