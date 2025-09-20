"""
WebSocket handler for telemetry data.

This module provides a WebSocket handler for serving telemetry data to clients.
"""

import asyncio
import json
import logging
import time
import traceback
from typing import Dict, List, Any, Set, Optional
import weakref

import websockets
from websockets.server import WebSocketServerProtocol

from pathfinder_pkg.diagnostics.telemetry.telemetry_collector import (
    get_telemetry_collector,
    TelemetryPoint,
    register_error,
    SoftwareError,
    ErrorSeverity,
)

# Setup module logger
logger = logging.getLogger(__name__)


class TelemetryWebSocketHandler:
    """WebSocket handler for telemetry data."""

    def __init__(self, host: str = "localhost", port: int = 8765):
        """
        Initialize the WebSocket handler.

        Args:
            host: Host to bind to
            port: Port to bind to
        """
        self.host = host
        self.port = port
        self.server = None
        self.clients: Set[WebSocketServerProtocol] = set()
        self.subscriptions: Dict[WebSocketServerProtocol, Set[str]] = {}
        self.running = False
        self._stop_event = asyncio.Event()

    async def handler(self, websocket: WebSocketServerProtocol, path: str) -> None:
        """
        Handle a WebSocket connection.

        Args:
            websocket: WebSocket connection
            path: Connection path
        """
        # Register the client
        self.clients.add(websocket)
        self.subscriptions[websocket] = set()

        logger.info(f"Client connected: {websocket.remote_address}")

        try:
            async for message in websocket:
                try:
                    data = json.loads(message)
                    await self.handle_message(websocket, data)
                except json.JSONDecodeError:
                    logger.warning(f"Received invalid JSON: {message}")
                    await websocket.send(json.dumps({"error": "Invalid JSON"}))
                except Exception as e:
                    logger.error(f"Error handling message: {e}")
                    logger.error(traceback.format_exc())
                    await websocket.send(json.dumps({"error": str(e)}))
        except websockets.exceptions.ConnectionClosed:
            logger.info(f"Client disconnected: {websocket.remote_address}")
        finally:
            # Remove the client
            self.clients.remove(websocket)
            if websocket in self.subscriptions:
                del self.subscriptions[websocket]

    async def handle_message(
        self, websocket: WebSocketServerProtocol, data: Dict[str, Any]
    ) -> None:
        """
        Handle a message from a client.

        Args:
            websocket: WebSocket connection
            data: Message data
        """
        if "command" not in data:
            logger.warning(f"Received message with no command: {data}")
            await websocket.send(json.dumps({"error": "No command specified"}))
            return

        command = data["command"]

        if command == "ping":
            await websocket.send(
                json.dumps({"command": "pong", "timestamp": time.time()})
            )
        elif command == "subscribe":
            await self.handle_subscribe(websocket, data)
        elif command == "unsubscribe":
            await self.handle_unsubscribe(websocket, data)
        elif command == "get_metrics":
            await self.handle_get_metrics(websocket, data)
        elif command == "custom_metrics":
            await self.handle_custom_metrics(websocket, data)
        else:
            logger.warning(f"Received unknown command: {command}")
            await websocket.send(json.dumps({"error": f"Unknown command: {command}"}))

    async def handle_subscribe(
        self, websocket: WebSocketServerProtocol, data: Dict[str, Any]
    ) -> None:
        """
        Handle a subscribe command.

        Args:
            websocket: WebSocket connection
            data: Message data
        """
        if "metrics" not in data or not isinstance(data["metrics"], list):
            logger.warning(f"Received subscribe command with invalid metrics: {data}")
            await websocket.send(json.dumps({"error": "Invalid metrics specified"}))
            return

        metrics = data["metrics"]
        if websocket in self.subscriptions:
            self.subscriptions[websocket].update(metrics)
        else:
            self.subscriptions[websocket] = set(metrics)

        logger.info(
            f"Client {websocket.remote_address} subscribed to metrics: {metrics}"
        )

        await websocket.send(
            json.dumps(
                {
                    "command": "subscribed",
                    "metrics": list(self.subscriptions[websocket]),
                }
            )
        )

    async def handle_unsubscribe(
        self, websocket: WebSocketServerProtocol, data: Dict[str, Any]
    ) -> None:
        """
        Handle an unsubscribe command.

        Args:
            websocket: WebSocket connection
            data: Message data
        """
        if "metrics" not in data or not isinstance(data["metrics"], list):
            logger.warning(f"Received unsubscribe command with invalid metrics: {data}")
            await websocket.send(json.dumps({"error": "Invalid metrics specified"}))
            return

        metrics = data["metrics"]
        if websocket in self.subscriptions:
            self.subscriptions[websocket].difference_update(metrics)

        logger.info(
            f"Client {websocket.remote_address} unsubscribed from metrics: {metrics}"
        )

        await websocket.send(
            json.dumps(
                {
                    "command": "unsubscribed",
                    "metrics": list(self.subscriptions.get(websocket, set())),
                }
            )
        )

    async def handle_get_metrics(
        self, websocket: WebSocketServerProtocol, data: Dict[str, Any]
    ) -> None:
        """
        Handle a get_metrics command.

        Args:
            websocket: WebSocket connection
            data: Message data
        """
        collector = get_telemetry_collector()
        if collector is None:
            logger.warning("Telemetry collector not initialized")
            await websocket.send(
                json.dumps({"error": "Telemetry collector not initialized"})
            )
            return

        # Get the list of metrics to retrieve
        metrics = data.get("metrics", [])
        if not metrics:
            # If no metrics specified, get all metrics
            metrics = (
                list(collector.metrics.keys()) if hasattr(collector, "metrics") else []
            )

        result = {}
        for metric_name in metrics:
            points = collector.query(metric_name=metric_name, limit=1)
            if points:
                result[metric_name] = points[0].value
            else:
                result[metric_name] = None

        await websocket.send(
            json.dumps(
                {"command": "metrics", "timestamp": time.time(), "metrics": result}
            )
        )

    async def handle_custom_metrics(
        self, websocket: WebSocketServerProtocol, data: Dict[str, Any]
    ) -> None:
        """
        Handle custom metrics sent by a client.

        Args:
            websocket: WebSocket connection
            data: Message data
        """
        if "data" not in data or not isinstance(data["data"], dict):
            logger.warning(f"Received custom_metrics command with invalid data: {data}")
            await websocket.send(json.dumps({"error": "Invalid custom metrics data"}))
            return

        # Record the custom metrics
        collector = get_telemetry_collector()
        if collector is None:
            logger.warning("Telemetry collector not initialized")
            await websocket.send(
                json.dumps({"error": "Telemetry collector not initialized"})
            )
            return

        custom_data = data["data"]
        for metric_name, value in custom_data.items():
            # Use the client's IP as a source identifier
            source = f"client:{websocket.remote_address[0]}"
            collector.record(
                metric_name=f"custom.{metric_name}", value=value, source=source
            )

        await websocket.send(
            json.dumps(
                {
                    "command": "custom_metrics_received",
                    "timestamp": time.time(),
                    "count": len(custom_data),
                }
            )
        )

    async def broadcast_metrics(self) -> None:
        """Broadcast metrics to subscribed clients."""
        # Get the telemetry collector
        collector = get_telemetry_collector()
        if collector is None:
            logger.warning("Telemetry collector not initialized")
            return

        # Get metrics for all clients
        all_metrics = set()
        for subscriptions in self.subscriptions.values():
            all_metrics.update(subscriptions)

        if not all_metrics:
            return

        # Query the metrics
        metric_values = {}
        for metric_name in all_metrics:
            points = collector.query(metric_name=metric_name, limit=1)
            if points:
                metric_values[metric_name] = points[0].value

        # Send to each client based on their subscriptions
        for websocket, subscriptions in self.subscriptions.items():
            if not subscriptions:
                continue

            # Filter metrics for this client
            client_metrics = {
                name: value
                for name, value in metric_values.items()
                if name in subscriptions
            }

            if not client_metrics:
                continue

            try:
                await websocket.send(
                    json.dumps(
                        {
                            "command": "metrics_update",
                            "timestamp": time.time(),
                            "metrics": client_metrics,
                        }
                    )
                )
            except websockets.exceptions.ConnectionClosed:
                # The client will be removed in the handler
                continue

    async def broadcast_loop(self) -> None:
        """Background task that periodically broadcasts metrics to clients."""
        while not self._stop_event.is_set():
            try:
                await self.broadcast_metrics()
            except Exception as e:
                logger.error(f"Error broadcasting metrics: {e}")
                logger.error(traceback.format_exc())
                register_error(
                    SoftwareError(
                        "Error broadcasting metrics",
                        severity=ErrorSeverity.MEDIUM,
                        cause=e,
                    )
                )

            # Wait for the next broadcast interval or until stopped
            try:
                await asyncio.wait_for(self._stop_event.wait(), 1.0)
            except asyncio.TimeoutError:
                pass

    async def run(self) -> None:
        """Run the WebSocket server."""
        logger.info(f"Starting telemetry WebSocket server on {self.host}:{self.port}")

        # Reset the stop event
        self._stop_event.clear()

        # Start the server
        async with websockets.serve(self.handler, self.host, self.port):
            # Start the broadcast loop
            broadcast_task = asyncio.create_task(self.broadcast_loop())

            # Wait for the stop event
            await self._stop_event.wait()

            # Cancel the broadcast task
            broadcast_task.cancel()

    def start(self) -> None:
        """Start the WebSocket server in a separate thread."""
        if self.running:
            logger.warning("WebSocket server already running")
            return

        self.running = True

        def run_server():
            # Create a new event loop
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

            try:
                # Run the server
                loop.run_until_complete(self.run())
            except Exception as e:
                logger.error(f"Error running WebSocket server: {e}")
                logger.error(traceback.format_exc())
                register_error(
                    SoftwareError(
                        "Error running WebSocket server",
                        severity=ErrorSeverity.HIGH,
                        cause=e,
                    )
                )
            finally:
                loop.close()
                self.running = False

        # Start the server in a separate thread
        import threading

        self.thread = threading.Thread(target=run_server, daemon=True)
        self.thread.start()

        logger.info("WebSocket server started")

    def stop(self) -> None:
        """Stop the WebSocket server."""
        if not self.running:
            logger.warning("WebSocket server not running")
            return

        # Set the stop event
        if self._stop_event:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                loop.call_soon_threadsafe(self._stop_event.set)
            else:
                self._stop_event.set()

        # Wait for the server to stop
        if hasattr(self, "thread") and self.thread is not None:
            self.thread.join(timeout=5.0)
            if self.thread.is_alive():
                logger.warning("WebSocket server thread did not stop")

        logger.info("WebSocket server stopped")


# Global WebSocket handler
_websocket_handler = None


def get_telemetry_websocket_handler() -> TelemetryWebSocketHandler:
    """
    Get the global telemetry WebSocket handler.

    Returns:
        The global telemetry WebSocket handler
    """
    global _websocket_handler
    if _websocket_handler is None:
        _websocket_handler = TelemetryWebSocketHandler()
    return _websocket_handler


def start_telemetry_websocket() -> None:
    """Start the telemetry WebSocket server."""
    handler = get_telemetry_websocket_handler()
    handler.start()


def stop_telemetry_websocket() -> None:
    """Stop the telemetry WebSocket server."""
    global _websocket_handler
    if _websocket_handler:
        _websocket_handler.stop()
        _websocket_handler = None
