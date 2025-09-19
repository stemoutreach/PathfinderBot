"""
WebSocket communication module for PathfinderBot.

This module provides WebSocket server functionality for real-time
communication between the robot and the web interface.
"""

import json
import asyncio
import threading
from pathlib import Path
import websockets
from pathfinder_pkg.utils.logging import get_logger

logger = get_logger(__name__)


class WebSocketServer:
    """
    WebSocket server for real-time communication.

    This class implements a WebSocket server that allows bidirectional
    communication between the robot and web clients.

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
        self.clients = set()
        self.server = None
        self.running = False
        self.loop = None
        self._thread = None

    async def _handler(self, websocket, path):
        """
        Handle WebSocket connections.

        Args:
            websocket: The WebSocket connection.
            path: The connection path.
        """
        # Register client
        self.clients.add(websocket)
        client_id = id(websocket)
        logger.info(f"Client connected: {client_id} from {websocket.remote_address}")

        try:
            async for message in websocket:
                try:
                    # Parse the message as JSON
                    data = json.loads(message)
                    logger.debug(f"Received from client {client_id}: {data}")

                    # Process the message
                    response = await self._process_message(data)

                    # Send response if there is one
                    if response:
                        await websocket.send(json.dumps(response))

                except json.JSONDecodeError:
                    logger.warning(f"Received invalid JSON from client {client_id}")
                    await websocket.send(
                        json.dumps({"status": "error", "message": "Invalid JSON"})
                    )
                except Exception as e:
                    logger.error(
                        f"Error processing message from client {client_id}: {e}"
                    )
                    await websocket.send(
                        json.dumps({"status": "error", "message": str(e)})
                    )
        except websockets.exceptions.ConnectionClosed:
            logger.info(f"Client {client_id} disconnected")
        finally:
            # Unregister client
            self.clients.remove(websocket)

    async def _process_message(self, data):
        """
        Process a message from a client.

        Args:
            data (dict): The message data.

        Returns:
            dict: The response data, or None if no response is needed.
        """
        # Default implementation - override in subclasses
        command = data.get("command")

        if command == "ping":
            return {"status": "ok", "command": "pong"}
        elif command == "status":
            return {"status": "ok", "server_status": "running"}
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

        message_json = json.dumps(message)
        await asyncio.gather(*[client.send(message_json) for client in self.clients])

    async def _server_task(self):
        """Run the WebSocket server in the current event loop."""
        async with websockets.serve(self._handler, self.host, self.port):
            self.running = True
            logger.info(f"WebSocket server started on {self.host}:{self.port}")
            # Keep the server running until stopped
            while self.running:
                await asyncio.sleep(1)

    def start(self):
        """Start the WebSocket server in a separate thread."""
        if self._thread and self._thread.is_alive():
            logger.warning("WebSocket server is already running")
            return

        def run_server():
            self.loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self.loop)
            self.loop.run_until_complete(self._server_task())

        self._thread = threading.Thread(target=run_server, daemon=True)
        self._thread.start()

        # Wait briefly to ensure the server starts
        time.sleep(0.5)

    def stop(self):
        """Stop the WebSocket server."""
        if not self.running:
            logger.warning("WebSocket server is not running")
            return

        logger.info("Stopping WebSocket server")
        self.running = False

        if self.loop:
            asyncio.run_coroutine_threadsafe(self._stop_server(), self.loop)

        if self._thread:
            self._thread.join(timeout=5.0)
            if self._thread.is_alive():
                logger.warning("WebSocket server thread did not terminate properly")

    async def _stop_server(self):
        """Stop the server and close all client connections."""
        if self.clients:
            # Close all client connections
            await asyncio.gather(*[client.close() for client in self.clients])
            self.clients.clear()


class RobotWebSocketServer(WebSocketServer):
    """
    WebSocket server specifically for robot control.

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

    async def _process_message(self, data):
        """
        Process robot-specific messages.

        Args:
            data (dict): The message data.

        Returns:
            dict: The response data, or None if no response is needed.
        """
        command = data.get("command")

        if command == "ping" or command == "status":
            # Handle basic commands from the parent class
            return await super()._process_message(data)

        elif command == "move":
            # Handle movement commands
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

        elif command == "stop":
            # Stop the robot
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

        elif command == "start_telemetry":
            # Start sending telemetry data
            interval = data.get("interval", 1.0)
            self.start_telemetry(interval)
            return {"status": "ok", "command": "start_telemetry", "interval": interval}

        elif command == "stop_telemetry":
            # Stop sending telemetry data
            self.stop_telemetry()
            return {"status": "ok", "command": "stop_telemetry"}

        else:
            logger.warning(f"Unknown command: {command}")
            return {"status": "error", "message": f"Unknown command: {command}"}

    def start_telemetry(self, interval=0.5):
        """
        Start sending telemetry data to clients at regular intervals.

        Args:
            interval (float, optional): The interval in seconds between updates.
        """
        if self._telemetry_task:
            logger.warning("Telemetry is already running")
            return

        async def telemetry_loop():
            while self.running:
                try:
                    # Get telemetry data
                    data = self._get_telemetry_data()
                    if data:
                        # Broadcast to all clients
                        await self.broadcast({"type": "telemetry", "data": data})
                except Exception as e:
                    logger.error(f"Error in telemetry loop: {e}")

                await asyncio.sleep(interval)

        if self.loop:
            self._telemetry_task = asyncio.run_coroutine_threadsafe(
                telemetry_loop(), self.loop
            )

    def _get_telemetry_data(self):
        """
        Get telemetry data from the robot.

        Returns:
            dict: The telemetry data, or None if not available.
        """
        if not self.robot:
            return None

        data = {"timestamp": time.time()}

        # Add robot-specific data
        if hasattr(self.robot, "get_motor_positions"):
            data["motor_positions"] = self.robot.get_motor_positions()

        if hasattr(self.robot, "get_component"):
            # Try to get sensor data from various components
            for sensor_name in ["camera", "sonar", "imu"]:
                sensor = self.robot.get_component(sensor_name)
                if sensor:
                    try:
                        if hasattr(sensor, "get_data"):
                            data[sensor_name] = sensor.get_data()
                        elif hasattr(sensor, "get_reading"):
                            data[sensor_name] = sensor.get_reading()
                        elif hasattr(sensor, "read"):
                            data[sensor_name] = sensor.read()
                    except Exception as e:
                        logger.debug(f"Error getting data from {sensor_name}: {e}")

        return data

    def stop_telemetry(self):
        """Stop sending telemetry data."""
        if self._telemetry_task:
            self._telemetry_task.cancel()
            self._telemetry_task = None

    def stop(self):
        """Stop the WebSocket server and telemetry."""
        self.stop_telemetry()
        super().stop()


# Add support for importing the time module which was referenced but not imported
import time
