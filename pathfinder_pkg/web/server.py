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
import struct
from typing import Dict, List, Optional, Any, Callable, Union

try:
    from flask import Flask, render_template, request, jsonify, send_from_directory
except ImportError:
    logging.error("Could not import Flask. Install with: pip install flask")

try:
    import numpy as np
except ImportError:
    logging.error("Could not import numpy. Install with: pip install numpy")
    import math

    # Simple fallback for numpy
    class np:
        @staticmethod
        def sqrt(x):
            return math.sqrt(x)


import base64

from pathfinder_pkg.utils.logging import get_logger
from pathfinder_pkg.utils.performance import (
    PerformanceTimer,
    get_performance_monitor,
    start_monitoring,
)
from pathfinder_pkg.navigation.map import OccupancyGridMap
from pathfinder_pkg.navigation.localization import Pose
from pathfinder_pkg.navigation.slam.slam import SLAM
from pathfinder_pkg.navigation.behaviors.navigator import (
    NavigationController,
    NavigationQueue,
    NavigationStatus,
)
from pathfinder_pkg.navigation.visualization.visualizer import WebVisualizer
from pathfinder_pkg.web.websocket import RobotWebSocketServer

# Initialize logger
logger = get_logger(__name__)

# Initialize performance monitoring
perf_monitor = start_monitoring(
    sample_interval=1.0, buffer_size=100, metrics_file="logs/performance_metrics.json"
)

# Declare global variables
try:
    app = Flask(__name__)
    app.config["SECRET_KEY"] = "pathfinderbot-secret!"
except NameError:
    # Create a placeholder for Flask if not available
    class MockApp:
        def __init__(self):
            self.config = {}
            self.routes = {}

        def route(self, route, methods=None):
            def decorator(f):
                self.routes[route] = (f, methods)
                return f

            return decorator

    app = MockApp()
    logger.warning("Flask not available, using mock implementation")

# Global objects
slam_system: Optional[SLAM] = None
nav_controller: Optional[NavigationController] = None
nav_queue: Optional[NavigationQueue] = None
visualizer: Optional[WebVisualizer] = None
robot_controller: Optional[Any] = None  # This would be the actual robot controller
ws_server: Optional[RobotWebSocketServer] = None


class WebInterface:
    """
    Web interface manager for PathfinderBot.

    This class provides methods for initializing and controlling the web interface
    for the PathfinderBot navigation system.
    """

    def __init__(
        self,
        slam_system_instance: Optional[SLAM] = None,
        navigation_controller: Optional[NavigationController] = None,
        robot_ctrl: Optional[Any] = None,
        host: str = "0.0.0.0",
        port: int = 5000,
        ws_port: int = 8765,
        debug: bool = False,
        update_rate: float = 0.2,  # Faster update rate for responsive UI
    ):
        """
        Initialize the web interface.

        Args:
            slam_system_instance: SLAM system for localization and mapping
            navigation_controller: Navigation controller for robot movement
            robot_ctrl: Robot controller for direct hardware control
            host: Host address to bind the server to
            port: Port to run the server on
            ws_port: Port to run the WebSocket server on
            debug: Whether to run in debug mode
            update_rate: Rate to update status information (seconds)
        """
        global slam_system, nav_controller, nav_queue, robot_controller, ws_server

        # Store global references
        slam_system = slam_system_instance
        nav_controller = navigation_controller
        robot_controller = robot_ctrl

        # Create navigation queue
        if navigation_controller:
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

        # Create WebSocket server
        ws_server = RobotWebSocketServer(robot=robot_ctrl, host=host, port=ws_port)

        # Register additional handlers
        if ws_server:
            ws_server.register_handler("set_goal", self._handle_ws_set_goal)
            ws_server.register_handler(
                "cancel_navigation", self._handle_ws_cancel_navigation
            )
            ws_server.register_handler("clear_queue", self._handle_ws_clear_queue)
            ws_server.register_handler("get_map", self._handle_ws_get_map)

        # Store server parameters
        self.host = host
        self.port = port
        self.debug = debug
        self.update_rate = update_rate

        # Set default background task priorities
        self._set_thread_priorities()

        # Initialize static directory
        static_dir = os.path.join(os.path.dirname(__file__), "static")
        if not os.path.exists(static_dir):
            os.makedirs(static_dir)

        # Initialize templates directory
        template_dir = os.path.join(os.path.dirname(__file__), "templates")
        if not os.path.exists(template_dir):
            os.makedirs(template_dir)

        logger.info(f"Web interface initialized at http://{host}:{port}")
        logger.info(f"WebSocket server will run on ws://{host}:{ws_port}")

        # Register shutdown handler for clean exit
        import atexit

        atexit.register(self.stop)

    def _set_thread_priorities(self):
        """Set thread priorities for critical operations."""
        # Get the current thread policy
        try:
            import os
            import sys

            # Set real-time priority for navigation controller if available
            if hasattr(os, "sched_setscheduler") and hasattr(os, "SCHED_FIFO"):
                # Only available on Linux/Unix systems
                if nav_controller and hasattr(nav_controller, "_controller_thread"):
                    thread_id = nav_controller._controller_thread.ident
                    if thread_id:
                        try:
                            # Set real-time scheduling policy
                            param = struct.pack("I", 99)  # Max RT priority
                            os.sched_setscheduler(thread_id, os.SCHED_FIFO, param)
                            logger.info(
                                "Set navigation controller thread to real-time priority"
                            )
                        except (OSError, PermissionError) as e:
                            logger.warning(f"Could not set real-time priority: {e}")
        except (ImportError, AttributeError) as e:
            logger.debug(f"Thread priority setting not supported: {e}")

    def _handle_ws_set_goal(self, data):
        """
        WebSocket handler for setting a navigation goal.

        Args:
            data: The message data

        Returns:
            Response data
        """
        x = data.get("x")
        y = data.get("y")
        theta = data.get("theta", 0.0)

        if x is None or y is None:
            return {"status": "error", "message": "Missing coordinates"}

        if nav_queue:
            with PerformanceTimer("add_navigation_goal"):
                task_index = nav_queue.add_goal(x, y, theta)
            return {
                "status": "ok",
                "task_index": task_index,
                "message": f"Goal added at ({x}, {y})",
            }

        return {"status": "error", "message": "Navigation system not available"}

    def _handle_ws_cancel_navigation(self, data):
        """
        WebSocket handler for canceling navigation.

        Args:
            data: The message data

        Returns:
            Response data
        """
        if nav_controller:
            try:
                nav_controller.cancel()
                return {"status": "ok", "message": "Navigation cancelled"}
            except Exception as e:
                logger.error(f"Error canceling navigation: {e}")
                return {"status": "error", "message": f"Error: {str(e)}"}

        return {"status": "error", "message": "Navigation system not available"}

    def _handle_ws_clear_queue(self, data):
        """
        WebSocket handler for clearing the navigation queue.

        Args:
            data: The message data

        Returns:
            Response data
        """
        if nav_queue:
            try:
                nav_queue.clear_queue()
                return {"status": "ok", "message": "Navigation queue cleared"}
            except Exception as e:
                logger.error(f"Error clearing navigation queue: {e}")
                return {"status": "error", "message": f"Error: {str(e)}"}

        return {"status": "error", "message": "Navigation queue not available"}

    def _handle_ws_get_map(self, data):
        """
        WebSocket handler for getting the current map.

        Args:
            data: The message data

        Returns:
            Response data with map information
        """
        if slam_system:
            with PerformanceTimer("get_map_data"):
                try:
                    grid_map = slam_system.get_map()
                    if grid_map:
                        # Convert map to compressed representation for network efficiency
                        try:
                            grid_data = grid_map.get_grid().tolist()
                        except AttributeError:
                            # If tolist() is not available, use a different approach
                            grid_data = list(map(float, grid_map.get_grid().flatten()))

                        return {
                            "status": "ok",
                            "width": grid_map.width,
                            "height": grid_map.height,
                            "resolution": grid_map.resolution,
                            "origin_x": grid_map.origin_x,
                            "origin_y": grid_map.origin_y,
                            "grid": grid_data,
                        }
                except Exception as e:
                    logger.error(f"Error getting map data: {e}")
                    return {"status": "error", "message": f"Error: {str(e)}"}

        return {"status": "error", "message": "Map not available"}

    def start(self):
        """Start the web server and background services."""
        # Start the WebSocket server
        if ws_server:
            ws_server.start()

            # Start telemetry after WebSocket server is running
            ws_server.start_telemetry(self.update_rate)

        # Start the visualizer
        if visualizer:
            visualizer.start()

        # Monitor system resources during server operation
        perf_monitor.register_callback(
            "system_monitoring", self._monitor_system_resources
        )

        # Start the web server (blocking call)
        try:
            # Check if we're using the real Flask or the mock
            if hasattr(app, "run"):
                app.run(host=self.host, port=self.port, debug=self.debug, threaded=True)
            else:
                logger.warning("Flask not available, web server not started")
                # Keep the program running for WebSockets
                import time

                while True:
                    time.sleep(1)
        except KeyboardInterrupt:
            logger.info("Server terminated by user")
            self.stop()
        except Exception as e:
            logger.error(f"Error starting web server: {e}")
            self.stop()

    def stop(self):
        """Stop the web server and background services."""
        logger.info("Stopping web services...")

        # Stop the WebSocket server
        if ws_server:
            try:
                ws_server.stop_telemetry()
                ws_server.stop()
                logger.info("WebSocket server stopped")
            except Exception as e:
                logger.error(f"Error stopping WebSocket server: {e}")

        # Stop the visualizer
        if visualizer:
            try:
                visualizer.stop()
                logger.info("Visualizer stopped")
            except Exception as e:
                logger.error(f"Error stopping visualizer: {e}")

        # Stop performance monitoring
        try:
            perf_monitor.unregister_callback("system_monitoring")
            logger.info("Performance monitoring stopped")
        except Exception as e:
            logger.error(f"Error stopping performance monitoring: {e}")

    def _monitor_system_resources(self):
        """Monitor system resources and adjust parameters if needed."""
        try:
            # Get CPU usage
            cpu_usage = perf_monitor.get_metric_average("cpu_usage") or 0

            # If CPU usage is high, reduce update rates
            if cpu_usage > 80:
                if ws_server and ws_server._telemetry_interval < 0.5:
                    ws_server._telemetry_interval = 0.5
                    logger.warning("High CPU usage detected, reducing telemetry rate")

            # Log memory usage
            memory_usage = perf_monitor.get_metric_average("memory_usage") or 0
            if memory_usage > 90:
                logger.warning(f"High memory usage detected: {memory_usage}%")

        except Exception as e:
            logger.error(f"Error monitoring system resources: {e}")


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
    with PerformanceTimer("api_get_status"):
        try:
            return jsonify(_get_current_status())
        except Exception as e:
            logger.error(f"Error in status API: {e}")
            return jsonify({"error": str(e)}), 500


@app.route("/api/map", methods=["GET"])
def get_map():
    """Get the current map."""
    with PerformanceTimer("api_get_map"):
        try:
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
        except Exception as e:
            logger.error(f"Error in map API: {e}")
            return jsonify({"error": str(e)}), 500


@app.route("/api/waypoints", methods=["GET"])
def get_waypoints():
    """Get the current waypoints."""
    with PerformanceTimer("api_get_waypoints"):
        try:
            if nav_controller and hasattr(nav_controller, "current_path"):
                waypoints = []
                for wp in nav_controller.current_path:
                    waypoints.append(
                        {"x": wp.x, "y": wp.y, "theta": wp.theta, "action": wp.action}
                    )
                return jsonify(waypoints)

            return jsonify([])
        except Exception as e:
            logger.error(f"Error in waypoints API: {e}")
            return jsonify({"error": str(e)}), 500


@app.route("/api/set_goal", methods=["POST"])
def set_goal():
    """Set a navigation goal."""
    with PerformanceTimer("api_set_goal"):
        try:
            data = request.json
            if not data:
                return jsonify({"error": "No data provided"}), 400

            # Extract goal coordinates
            x = data.get("x")
            y = data.get("y")
            theta = data.get("theta", 0.0)

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
        except Exception as e:
            logger.error(f"Error in set goal API: {e}")
            return jsonify({"error": str(e)}), 500


@app.route("/api/cancel_navigation", methods=["POST"])
def cancel_navigation():
    """Cancel current navigation."""
    with PerformanceTimer("api_cancel_navigation"):
        try:
            if nav_controller:
                nav_controller.cancel()
                return jsonify({"success": True, "message": "Navigation cancelled"})

            return jsonify({"error": "Navigation system not available"}), 503
        except Exception as e:
            logger.error(f"Error in cancel navigation API: {e}")
            return jsonify({"error": str(e)}), 500


@app.route("/api/clear_queue", methods=["POST"])
def clear_queue():
    """Clear the navigation queue."""
    with PerformanceTimer("api_clear_queue"):
        try:
            if nav_queue:
                nav_queue.clear_queue()
                return jsonify({"success": True, "message": "Navigation queue cleared"})

            return jsonify({"error": "Navigation queue not available"}), 503
        except Exception as e:
            logger.error(f"Error in clear queue API: {e}")
            return jsonify({"error": str(e)}), 500


@app.route("/api/control/move", methods=["POST"])
def control_move():
    """Direct control of robot movement."""
    with PerformanceTimer("api_control_move"):
        try:
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
        except Exception as e:
            logger.error(f"Error in control move API: {e}")
            return jsonify({"error": str(e)}), 500


@app.route("/api/performance", methods=["GET"])
def get_performance():
    """Get performance metrics."""
    with PerformanceTimer("api_get_performance"):
        try:
            return jsonify(perf_monitor.get_metrics_summary())
        except Exception as e:
            logger.error(f"Error in performance API: {e}")
            return jsonify({"error": str(e)}), 500


def _get_current_status() -> Dict[str, Any]:
    """
    Get the current status of the robot.

    Returns:
        Dictionary with status information
    """
    with PerformanceTimer("get_current_status"):
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

        try:
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
                if (
                    hasattr(nav_controller, "current_path")
                    and nav_controller.current_path
                ):
                    status["navigation"]["path_length"] = len(
                        nav_controller.current_path
                    )

                # Calculate distance to goal if both pose and goal are available
                if status["pose"] and status["navigation"]["goal"]:
                    dx = float(status["navigation"]["goal"]["x"]) - float(
                        status["pose"]["x"]
                    )
                    dy = float(status["navigation"]["goal"]["y"]) - float(
                        status["pose"]["y"]
                    )
                    status["navigation"]["distance_to_goal"] = np.sqrt(
                        dx * dx + dy * dy
                    )

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

            # Add performance metrics
            status["performance"] = {
                "cpu_usage": perf_monitor.get_metric_average("cpu_usage") or 0,
                "memory_usage": perf_monitor.get_metric_average("memory_usage") or 0,
                "websocket_latency": perf_monitor.get_metric_average(
                    "websocket_latency"
                )
                or 0,
            }

            return status

        except Exception as e:
            logger.error(f"Error getting status: {e}")
            # Return a minimal status on error for robustness
            return {"timestamp": time.time(), "error": str(e)}
