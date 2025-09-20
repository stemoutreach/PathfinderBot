"""
WebSocket communication module for PathfinderBot.

This module provides WebSocket server functionality for real-time
communication between the robot and the web interface.
"""

import json
import time
import asyncio
import threading
import logging
from typing import Dict, List, Set, Any, Optional, Callable, Union
import numpy as np

try:
    from websockets.server import serve
    import websockets
except ImportError:
    try:
        from websockets import serve
        import websockets
    except ImportError:
        logging.error(
            "Could not import websockets package. Install with: pip install websockets"
        )
        raise

from pathfinder_pkg.utils.logging import get_logger
from pathfinder_pkg.utils.performance import PerformanceTimer, get_performance_monitor

logger = get_logger(__name__)


class WebSocketServer:
    """
    WebSocket server for real-time communication.

    This class implements a WebSocket server that allows bidirectional
    communication between the robot and web clients with improved
    performance, error handling, and recovery mechanisms.

    Attributes:
        host (str): Host address to bind the server to.
        port (int): Port to listen on.
        clients (set): Set of connected WebSocket clients.
        server (websockets.WebSocketServer): The WebSocket server instance.
        running (bool): Whether the server is running.
    """

    def __init__(self, host="0.0.0.0", port=8765):
        """
        Initialize the WebSocket server.

        Args:
            host (str, optional): Host address to bind the server to.
            port (int, optional): Port to listen on.
        """
        self.host = host
        self.port = port
        self.clients: Set[websockets.WebSocketServerProtocol] = set()
        self.client_info: Dict[websockets.WebSocketServerProtocol, Dict[str, Any]] = {}
        self.server = None
        self.running = False
        self.loop = None
        self._thread = None
        self._lock = threading.RLock()
        self._message_handlers: Dict[str, Callable] = {}
        self._shutdown_event = threading.Event()
        self._reconnection_attempts = 0
        self._max_reconnection_attempts = 5
        self._performance_monitor = get_performance_monitor()

        # Register default message handlers
        self._register_default_handlers()

    def _register_default_handlers(self):
        """Register default message handlers."""
        self._message_handlers["ping"] = self._handle_ping
        self._message_handlers["status"] = self._handle_status

    def register_handler(self, command: str, handler: Callable):
        """
        Register a handler for a specific command.

        Args:
            command: The command name.
            handler: The handler function that takes a message and returns a response.
        """
        with self._lock:
            self._message_handlers[command] = handler
            logger.debug(f"Registered handler for command '{command}'")

    def _handle_ping(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle ping messages.

        Args:
            message: The ping message.

        Returns:
            The pong response.
        """
        return {
            "status": "ok",
            "command": "pong",
            "timestamp": time.time(),
            "server_time": time.time(),
        }

    def _handle_status(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle status request messages.

        Args:
            message: The status request message.

        Returns:
            The status response.
        """
        return {
            "status": "ok",
            "server_status": "running",
            "uptime": (
                time.time() - self._start_time if hasattr(self, "_start_time") else 0
            ),
            "clients": len(self.clients),
            "timestamp": time.time(),
        }

    async def _handler(self, websocket, path=None):
        """
        Handle WebSocket connections.

        Args:
            websocket: The WebSocket connection.
            path: The connection path.
        """
        if path is None:
            path = getattr(websocket, "path", "/")

        # Get client information
        client_addr = getattr(websocket, "remote_address", ("unknown", 0))
        client_id = id(websocket)

        # Register client with performance monitoring
        with self._lock:
            self.clients.add(websocket)
            self.client_info[websocket] = {
                "id": client_id,
                "address": client_addr,
                "connected_at": time.time(),
                "messages_received": 0,
                "messages_sent": 0,
                "errors": 0,
                "path": path,
            }

        logger.info(f"Client connected: {client_id} from {client_addr}")
        self._performance_monitor.increment_counter("websocket_connections")

        try:
            # Send welcome message
            welcome_msg = {
                "type": "server_info",
                "message": "Welcome to PathfinderBot WebSocket server",
                "timestamp": time.time(),
            }
            await websocket.send(json.dumps(welcome_msg))

            with self._lock:
                if websocket in self.client_info:
                    self.client_info[websocket]["messages_sent"] += 1

            # Process incoming messages
            async for message in websocket:
                with PerformanceTimer("websocket_message_processing"):
                    try:
                        # Parse the message as JSON
                        data = json.loads(message)

                        with self._lock:
                            if websocket in self.client_info:
                                self.client_info[websocket]["messages_received"] += 1

                        logger.debug(f"Received from client {client_id}: {data}")
                        self._performance_monitor.increment_counter(
                            "websocket_messages_received"
                        )

                        # Process the message
                        response = await self._process_message(data)

                        # Send response if there is one
                        if response:
                            await websocket.send(json.dumps(response))
                            with self._lock:
                                if websocket in self.client_info:
                                    self.client_info[websocket]["messages_sent"] += 1
                            self._performance_monitor.increment_counter(
                                "websocket_messages_sent"
                            )

                    except json.JSONDecodeError:
                        logger.warning(f"Received invalid JSON from client {client_id}")
                        with self._lock:
                            if websocket in self.client_info:
                                self.client_info[websocket]["errors"] += 1
                        self._performance_monitor.increment_counter("websocket_errors")

                        await websocket.send(
                            json.dumps({"status": "error", "message": "Invalid JSON"})
                        )
                    except Exception as e:
                        logger.error(
                            f"Error processing message from client {client_id}: {e}"
                        )
                        with self._lock:
                            if websocket in self.client_info:
                                self.client_info[websocket]["errors"] += 1
                        self._performance_monitor.increment_counter("websocket_errors")

                        await websocket.send(
                            json.dumps({"status": "error", "message": str(e)})
                        )
        except websockets.exceptions.ConnectionClosed as e:
            logger.info(f"Client {client_id} disconnected: {e}")
            self._performance_monitor.increment_counter("websocket_disconnections")
        except Exception as e:
            logger.error(f"Error handling WebSocket client {client_id}: {e}")
            self._performance_monitor.increment_counter("websocket_errors")
        finally:
            # Unregister client
            with self._lock:
                if websocket in self.clients:
                    self.clients.remove(websocket)
                if websocket in self.client_info:
                    del self.client_info[websocket]

    async def _process_message(self, data):
        """
        Process a message from a client.

        Args:
            data (dict): The message data.

        Returns:
            dict: The response data, or None if no response is needed.
        """
        # Extract command
        command = data.get("command")
        if not command:
            logger.warning("Message has no command field")
            return {"status": "error", "message": "No command specified"}

        # Look up handler for this command
        with self._lock:
            handler = self._message_handlers.get(command)

        if handler:
            try:
                # Measure handler execution time
                start_time = time.perf_counter()
                result = handler(data)
                # If handler returns an awaitable, await it
                if asyncio.iscoroutine(result):
                    result = await result
                elapsed_ms = (time.perf_counter() - start_time) * 1000

                # Record handler timing
                self._performance_monitor.record_metric(
                    f"handler_{command}_time", elapsed_ms
                )

                return result
            except Exception as e:
                logger.error(f"Error in handler for '{command}': {e}")
                return {"status": "error", "message": f"Handler error: {str(e)}"}
        else:
            logger.warning(f"Unknown command: {command}")
            return {"status": "error", "message": f"Unknown command: {command}"}

    async def broadcast(self, message):
        """
        Broadcast a message to all connected clients.

        Args:
            message (dict): The message to broadcast.
        """
        if not self.clients:
            return

        with PerformanceTimer("websocket_broadcast"):
            message_json = json.dumps(message)

            # Use a copy of clients to avoid modification during iteration
            with self._lock:
                clients_copy = set(self.clients)

            # Create broadcast tasks
            send_tasks = []
            for client in clients_copy:
                # Skip clients that are closing or closed
                if client.closed:
                    continue

                # Create task for sending to this client
                send_tasks.append(self._safe_send(client, message_json))

            # Execute all send tasks concurrently
            if send_tasks:
                self._performance_monitor.record_metric(
                    "broadcast_clients", len(send_tasks)
                )
                await asyncio.gather(*send_tasks, return_exceptions=True)

    async def _safe_send(self, websocket, message_json):
        """
        Safely send a message to a client, handling any exceptions.

        Args:
            websocket: The WebSocket connection.
            message_json: The JSON message to send.
        """
        try:
            await websocket.send(message_json)
            with self._lock:
                if websocket in self.client_info:
                    self.client_info[websocket]["messages_sent"] += 1
            return True
        except websockets.exceptions.ConnectionClosed:
            # Connection already closed, will be cleaned up in the main handler
            return False
        except Exception as e:
            logger.error(f"Error sending to client: {e}")
            self._performance_monitor.increment_counter("websocket_errors")
            return False

    async def _server_task(self):
        """Run the WebSocket server in the current event loop."""
        try:
            self._start_time = time.time()
            logger.info(f"Starting WebSocket server on {self.host}:{self.port}")

            # Set up server and start serving
            async with serve(self._handler, self.host, self.port):
                self.running = True
                logger.info(f"WebSocket server started on {self.host}:{self.port}")

                # Keep the server running until stopped
                while self.running and not self._shutdown_event.is_set():
                    await asyncio.sleep(1)

                    # Periodic tasks could be added here

        except OSError as e:
            logger.error(f"Failed to start WebSocket server: {e}")
            self._reconnection_attempts += 1

            if self._reconnection_attempts < self._max_reconnection_attempts:
                wait_time = min(
                    30, 2**self._reconnection_attempts
                )  # Exponential backoff
                logger.info(
                    f"Attempting to restart WebSocket server in {wait_time} seconds..."
                )
                await asyncio.sleep(wait_time)

                # Try to restart the server
                asyncio.create_task(self._server_task())
            else:
                logger.error(
                    f"Maximum reconnection attempts ({self._max_reconnection_attempts}) reached"
                )
                self._performance_monitor.increment_counter("websocket_failed_restarts")
        except Exception as e:
            logger.error(f"Error in WebSocket server: {e}")
            self._performance_monitor.increment_counter("websocket_errors")

    def start(self):
        """Start the WebSocket server in a separate thread."""
        if self._thread and self._thread.is_alive():
            logger.warning("WebSocket server is already running")
            return

        def run_server():
            self.loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self.loop)
            self._shutdown_event.clear()
            self._reconnection_attempts = 0
            self.loop.run_until_complete(self._server_task())

        self._thread = threading.Thread(
            target=run_server, daemon=True, name="WebSocketServer"
        )
        self._thread.start()
        logger.info(f"WebSocket server thread started")

        # Wait briefly to ensure the server starts
        time.sleep(0.5)

    def stop(self):
        """Stop the WebSocket server."""
        if not self.running and not self._thread:
            logger.warning("WebSocket server is not running")
            return

        logger.info("Stopping WebSocket server")
        self.running = False
        self._shutdown_event.set()

        if self.loop:
            asyncio.run_coroutine_threadsafe(self._stop_server(), self.loop)

        if self._thread:
            self._thread.join(timeout=5.0)
            if self._thread and self._thread.is_alive():
                logger.warning("WebSocket server thread did not terminate properly")
                self._performance_monitor.increment_counter(
                    "websocket_unclean_shutdowns"
                )

    async def _stop_server(self):
        """Stop the server and close all client connections."""
        logger.info(f"Closing connections to {len(self.clients)} clients")

        try:
            if self.clients:
                # Send close message to all clients
                close_msg = {
                    "type": "server_shutdown",
                    "message": "Server is shutting down",
                }
                await self.broadcast(close_msg)

                # Close all client connections
                close_tasks = []
                with self._lock:
                    for client in list(self.clients):
                        if not client.closed:
                            close_tasks.append(client.close())

                if close_tasks:
                    await asyncio.gather(*close_tasks, return_exceptions=True)

                self.clients.clear()
                self.client_info.clear()
                logger.info("All client connections closed")
        except Exception as e:
            logger.error(f"Error during WebSocket server shutdown: {e}")


class RobotWebSocketServer(WebSocketServer):
    """
    WebSocket server specifically for robot control with improved performance and reliability.

    This class extends the base WebSocket server with robot-specific
    functionality for controlling the robot and receiving sensor data.
    """

    def __init__(self, robot=None, **kwargs):
        """
        Initialize the robot WebSocket server.

        Args:
            robot: The robot instance to control.
            **kwargs: Additional arguments to pass to the parent constructor.
        """
        super().__init__(**kwargs)
        self.robot = robot
        self._telemetry_task = None
        self._telemetry_running = False
        self._telemetry_interval = 0.5
        self._last_telemetry_time = 0
        self._adaptive_telemetry = True  # Enable adaptive telemetry rate
        self._min_telemetry_interval = 0.1  # Minimum interval between telemetry updates

        # Register command handlers
        self.register_handler("move", self._handle_move)
        self.register_handler("stop", self._handle_stop)
        self.register_handler("start_telemetry", self._handle_start_telemetry)
        self.register_handler("stop_telemetry", self._handle_stop_telemetry)
        self.register_handler(
            "set_telemetry_interval", self._handle_set_telemetry_interval
        )

    def _handle_move(self, data):
        """
        Handle movement commands.

        Args:
            data: The command data.

        Returns:
            Response data.
        """
        x = data.get("x", 0)
        y = data.get("y", 0)
        rotation = data.get("rotation", 0)

        if self.robot:
            try:
                if hasattr(self.robot, "set_velocity"):
                    self.robot.set_velocity(x, y, rotation)
                elif hasattr(self.robot, "translation"):
                    self.robot.translation(x, y)
                    if rotation != 0:
                        self.robot.rotation(rotation)
                return {"status": "ok", "command": "move"}
            except Exception as e:
                logger.error(f"Error executing move command: {e}")
                return {"status": "error", "message": str(e)}
        else:
            return {"status": "error", "message": "Robot not available"}

    def _handle_stop(self, data):
        """
        Handle stop commands.

        Args:
            data: The command data.

        Returns:
            Response data.
        """
        if self.robot:
            try:
                if hasattr(self.robot, "stop"):
                    self.robot.stop()
                elif hasattr(self.robot, "reset_motors"):
                    self.robot.reset_motors()
                return {"status": "ok", "command": "stop"}
            except Exception as e:
                logger.error(f"Error executing stop command: {e}")
                return {"status": "error", "message": str(e)}
        else:
            return {"status": "error", "message": "Robot not available"}

    def _handle_start_telemetry(self, data):
        """
        Handle start telemetry commands.

        Args:
            data: The command data.

        Returns:
            Response data.
        """
        interval = data.get("interval", 0.5)
        self.start_telemetry(interval)
        return {"status": "ok", "command": "start_telemetry", "interval": interval}

    def _handle_stop_telemetry(self, data):
        """
        Handle stop telemetry commands.

        Args:
            data: The command data.

        Returns:
            Response data.
        """
        self.stop_telemetry()
        return {"status": "ok", "command": "stop_telemetry"}

    def _handle_set_telemetry_interval(self, data):
        """
        Handle set telemetry interval commands.

        Args:
            data: The command data with new interval.

        Returns:
            Response data.
        """
        interval = data.get("interval", 0.5)
        if interval < self._min_telemetry_interval:
            interval = self._min_telemetry_interval

        self._telemetry_interval = interval
        return {
            "status": "ok",
            "command": "set_telemetry_interval",
            "interval": interval,
        }

    def start_telemetry(self, interval=0.5):
        """
        Start sending telemetry data to clients at regular intervals.

        Args:
            interval (float, optional): The interval in seconds between updates.
        """
        if self._telemetry_task:
            logger.warning("Telemetry is already running")
            return

        if interval < self._min_telemetry_interval:
            interval = self._min_telemetry_interval

        self._telemetry_interval = interval
        self._telemetry_running = True
        self._last_telemetry_time = 0

        async def telemetry_loop():
            while self.running and self._telemetry_running:
                try:
                    # Check if it's time to send telemetry
                    now = time.time()
                    elapsed = now - self._last_telemetry_time

                    if elapsed >= self._telemetry_interval:
                        # Get telemetry data
                        with PerformanceTimer("telemetry_data_collection"):
                            data = self._get_telemetry_data()

                        if data:
                            # Broadcast to all clients
                            await self.broadcast({"type": "telemetry", "data": data})
                            self._last_telemetry_time = now

                            # Adaptive telemetry: adjust interval based on client count and system load
                            if self._adaptive_telemetry:
                                client_count = len(self.clients)
                                cpu_load = (
                                    self._performance_monitor.get_metric_average(
                                        "cpu_usage"
                                    )
                                    or 50
                                )

                                # Scale interval based on number of clients and CPU load
                                adjusted_interval = max(
                                    self._min_telemetry_interval,
                                    self._telemetry_interval
                                    * (1 + 0.05 * client_count)
                                    * (1 + (cpu_load - 50) / 100),
                                )

                                # Only adjust if it's significantly different
                                if (
                                    abs(adjusted_interval - self._telemetry_interval)
                                    > 0.05
                                ):
                                    self._telemetry_interval = adjusted_interval
                                    logger.debug(
                                        f"Adjusted telemetry interval to {self._telemetry_interval:.2f}s"
                                    )

                    # Dynamic sleep time based on time until next telemetry update
                    sleep_time = max(
                        0.01,
                        min(
                            0.1,
                            max(
                                0,
                                self._telemetry_interval
                                - (time.time() - self._last_telemetry_time),
                            ),
                        ),
                    )
                    await asyncio.sleep(sleep_time)

                except Exception as e:
                    logger.error(f"Error in telemetry loop: {e}")
                    self._performance_monitor.increment_counter("telemetry_errors")
                    await asyncio.sleep(1.0)  # Sleep longer on error

        if self.loop:
            self._telemetry_task = asyncio.run_coroutine_threadsafe(
                telemetry_loop(), self.loop
            )
            logger.info(f"Telemetry started with interval {interval:.2f}s")

    def stop_telemetry(self):
        """Stop sending telemetry data."""
        if not self._telemetry_running:
            logger.warning("Telemetry is not running")
            return

        self._telemetry_running = False

        if self._telemetry_task:
            self._telemetry_task.cancel()
            self._telemetry_task = None

        logger.info("Telemetry stopped")

    def _get_telemetry_data(self):
        """
        Get telemetry data from the robot.

        This method collects various types of data from the robot,
        formats it, and returns it for sending to clients.

        Returns:
            dict: The telemetry data, or None if not available.
        """
        if not self.robot:
            return None

        timestamp = time.time()
        data = {"timestamp": timestamp}

        try:
            # Add robot-specific data based on available components and methods
            # Motor positions
            if hasattr(self.robot, "get_motor_positions"):
                with PerformanceTimer("get_motor_positions"):
                    motor_positions = self.robot.get_motor_positions()
                    if motor_positions is not None:
                        data["motor_positions"] = motor_positions

            # Current pose
            if hasattr(self.robot, "get_pose"):
                with PerformanceTimer("get_pose"):
                    pose = self.robot.get_pose()
                    if pose:
                        data["pose"] = {"x": pose.x, "y": pose.y, "theta": pose.theta}

            # Battery status
            if hasattr(self.robot, "get_battery_level"):
                with PerformanceTimer("get_battery_level"):
                    battery = self.robot.get_battery_level()
                    if battery:
                        data["battery"] = battery

            # Component data - try to get data from different robot components
            if hasattr(self.robot, "get_component"):
                # Try to get sensor data from various components
                for sensor_name in ["camera", "sonar", "imu"]:
                    try:
                        with PerformanceTimer(f"get_{sensor_name}_data"):
                            sensor = self.robot.get_component(sensor_name)
                            if sensor:
                                # Try different methods for getting data
                                sensor_data = None
                                if hasattr(sensor, "get_data"):
                                    sensor_data = sensor.get_data()
                                elif hasattr(sensor, "get_reading"):
                                    sensor_data = sensor.get_reading()
                                elif hasattr(sensor, "read"):
                                    sensor_data = sensor.read()

                                if sensor_data is not None:
                                    data[sensor_name] = sensor_data
                    except Exception as e:
                        logger.debug(f"Error getting data from {sensor_name}: {e}")

            # If the robot has a navigation controller, get its status
            if hasattr(self.robot, "navigation_controller"):
                nav_controller = self.robot.navigation_controller
                if nav_controller:
                    nav_data = {}

                    # Navigation status
                    if hasattr(nav_controller, "navigation_status"):
                        if hasattr(nav_controller.navigation_status, "name"):
                            nav_data["status"] = nav_controller.navigation_status.name
                        else:
                            nav_data["status"] = str(nav_controller.navigation_status)

                    # Goal pose
                    if (
                        hasattr(nav_controller, "goal_pose")
                        and nav_controller.goal_pose
                    ):
                        goal = nav_controller.goal_pose
                        nav_data["goal"] = {
                            "x": goal.x,
                            "y": goal.y,
                            "theta": goal.theta,
                        }

                    # Path information
                    if (
                        hasattr(nav_controller, "current_path")
                        and nav_controller.current_path
                    ):
                        nav_data["path_length"] = len(nav_controller.current_path)
                        # Calculate distance to goal if both pose and goal are available
                        if "pose" in data and "goal" in nav_data:
                            dx = nav_data["goal"]["x"] - data["pose"]["x"]
                            dy = nav_data["goal"]["y"] - data["pose"]["y"]
                            nav_data["distance_to_goal"] = np.sqrt(dx * dx + dy * dy)

                    data["navigation"] = nav_data

            # Add system performance metrics
            system_metrics = {}

            # Get CPU, memory, thread counts
            cpu_usage = self._performance_monitor.get_metric_average("cpu_usage")
            memory_usage = self._performance_monitor.get_metric_average("memory_usage")
            thread_count = self._performance_monitor.get_metric_average("thread_count")

            if cpu_usage is not None:
                system_metrics["cpu_usage"] = cpu_usage
            if memory_usage is not None:
                system_metrics["memory_usage"] = memory_usage
            if thread_count is not None:
                system_metrics["thread_count"] = thread_count

            if system_metrics:
                data["system"] = system_metrics

            return data

        except Exception as e:
            logger.error(f"Error collecting telemetry data: {e}")
            self._performance_monitor.increment_counter("telemetry_errors")
            return {"timestamp": timestamp, "error": str(e)}

    def stop(self):
        """Stop the WebSocket server and telemetry."""
        self.stop_telemetry()
        super().stop()
