"""
Communication infrastructure for multi-robot coordination.
Enables robot-to-robot and robot-to-server communication.
"""

import json
import asyncio
import websockets
from typing import Dict, List, Callable, Any, Optional
import logging
from threading import Thread
import time
import ssl
import uuid


class Message:
    """Base message class for robot communication."""

    def __init__(
        self,
        sender_id: str,
        message_type: str,
        payload: Dict[str, Any],
        target_id: Optional[str] = None,
    ):
        self.id = str(uuid.uuid4())
        self.sender_id = sender_id
        self.target_id = target_id  # None for broadcast
        self.message_type = message_type
        self.payload = payload
        self.timestamp = time.time()

    def to_dict(self) -> Dict[str, Any]:
        """Convert message to dictionary for serialization."""
        return {
            "id": self.id,
            "sender_id": self.sender_id,
            "target_id": self.target_id,
            "message_type": self.message_type,
            "payload": self.payload,
            "timestamp": self.timestamp,
        }

    def to_json(self) -> str:
        """Convert message to JSON string."""
        return json.dumps(self.to_dict())

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Message":
        """Create message from dictionary."""
        msg = cls(
            sender_id=data["sender_id"],
            message_type=data["message_type"],
            payload=data["payload"],
            target_id=data.get("target_id"),
        )
        msg.id = data["id"]
        msg.timestamp = data["timestamp"]
        return msg

    @classmethod
    def from_json(cls, json_str: str) -> "Message":
        """Create message from JSON string."""
        data = json.loads(json_str)
        return cls.from_dict(data)


class RobotCommunicator:
    """Handles communication between robots and the central server."""

    def __init__(self, robot_id: str, server_url: str):
        self.robot_id = robot_id
        self.server_url = server_url
        self.websocket = None
        self.connected = False
        self.message_handlers: Dict[str, List[Callable]] = {}
        self._event_loop = None
        self._thread = None
        self.reconnect_delay = 2  # seconds
        self.heartbeat_interval = 10  # seconds
        self.last_heartbeat = 0
        self.logger = logging.getLogger(f"RobotCommunicator-{robot_id}")

    async def connect(self) -> bool:
        """Connect to the central coordination server."""
        try:
            self.logger.info(f"Connecting to server at {self.server_url}")
            self.websocket = await websockets.connect(self.server_url)
            self.connected = True
            self.logger.info("Connected to server")

            # Register with server
            registration_msg = Message(
                sender_id=self.robot_id,
                message_type="registration",
                payload={"capabilities": self._get_robot_capabilities()},
            )
            await self.send_message(registration_msg)

            # Start heartbeat
            self._start_heartbeat()

            return True
        except Exception as e:
            self.logger.error(f"Failed to connect: {e}")
            self.connected = False
            return False

    async def disconnect(self):
        """Disconnect from the server."""
        if self.websocket:
            try:
                await self.websocket.close()
            except:
                pass
        self.connected = False
        self.logger.info("Disconnected from server")

    async def send_message(self, message: Message) -> bool:
        """Send a message to the server."""
        if not self.connected:
            self.logger.error("Not connected to server")
            return False

        try:
            await self.websocket.send(message.to_json())
            return True
        except Exception as e:
            self.logger.error(f"Failed to send message: {e}")
            self.connected = False
            return False

    async def _receive_loop(self):
        """Loop to receive and process messages."""
        while self.connected:
            try:
                json_str = await self.websocket.recv()
                message = Message.from_json(json_str)
                await self._process_message(message)
            except websockets.exceptions.ConnectionClosed:
                self.logger.warning("Connection closed")
                self.connected = False
                break
            except Exception as e:
                self.logger.error(f"Error processing message: {e}")

    async def _process_message(self, message: Message):
        """Process a received message."""
        # Check if message is intended for this robot or is a broadcast
        if message.target_id and message.target_id != self.robot_id:
            return

        # Handle heartbeat responses
        if message.message_type == "heartbeat_response":
            self.last_heartbeat = time.time()
            return

        # Dispatch to registered handlers
        handlers = self.message_handlers.get(message.message_type, [])
        for handler in handlers:
            try:
                await handler(message)
            except Exception as e:
                self.logger.error(f"Error in message handler: {e}")

    async def _heartbeat(self):
        """Send periodic heartbeats to server."""
        while self.connected:
            try:
                heartbeat_msg = Message(
                    sender_id=self.robot_id,
                    message_type="heartbeat",
                    payload={"status": "active"},
                )
                await self.send_message(heartbeat_msg)
                await asyncio.sleep(self.heartbeat_interval)
            except:
                break

    def _start_heartbeat(self):
        """Start the heartbeat task."""
        if self._event_loop:
            asyncio.run_coroutine_threadsafe(self._heartbeat(), self._event_loop)

    def register_handler(self, message_type: str, handler: Callable):
        """Register a handler for a specific message type."""
        if message_type not in self.message_handlers:
            self.message_handlers[message_type] = []
        self.message_handlers[message_type].append(handler)

    def start(self):
        """Start the communication thread."""
        if self._thread:
            return

        def run_async_loop():
            self._event_loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self._event_loop)

            async def connect_and_receive():
                while True:
                    if not self.connected:
                        success = await self.connect()
                        if not success:
                            await asyncio.sleep(self.reconnect_delay)
                            continue

                    await self._receive_loop()
                    await asyncio.sleep(self.reconnect_delay)

            self._event_loop.run_until_complete(connect_and_receive())

        self._thread = Thread(target=run_async_loop, daemon=True)
        self._thread.start()
        self.logger.info("Communication thread started")

    def stop(self):
        """Stop the communication thread."""
        if self._event_loop:
            asyncio.run_coroutine_threadsafe(self.disconnect(), self._event_loop)
        self.logger.info("Communication stopped")

    def _get_robot_capabilities(self) -> Dict[str, Any]:
        """Get the capabilities of this robot."""
        # This should be overridden with actual robot capabilities
        return {
            "sensors": ["camera", "ultrasonic"],
            "actuators": ["motors", "arm"],
            "max_speed": 0.5,  # m/s
            "battery_level": 0.8,  # 80%
        }


class CoordinationServer:
    """Central server for coordinating multiple robots."""

    def __init__(
        self,
        host: str = "0.0.0.0",
        port: int = 8765,
        ssl_context: ssl.SSLContext = None,
    ):
        self.host = host
        self.port = port
        self.ssl_context = ssl_context
        self.connected_robots: Dict[str, websockets.WebSocketServerProtocol] = {}
        self.robot_capabilities: Dict[str, Dict[str, Any]] = {}
        self.logger = logging.getLogger("CoordinationServer")
        self.server = None
        self.message_handlers: Dict[str, List[Callable]] = {}
        self._task = None
        self.last_heartbeat: Dict[str, float] = {}
        self.heartbeat_timeout = 30  # seconds

    async def start_server(self):
        """Start the coordination server."""
        self.server = await websockets.serve(
            self.handle_connection, self.host, self.port, ssl=self.ssl_context
        )
        self.logger.info(f"Server started on {self.host}:{self.port}")

        # Start heartbeat monitoring
        asyncio.create_task(self._monitor_heartbeats())

    async def handle_connection(
        self, websocket: websockets.WebSocketServerProtocol, path
    ):
        """Handle a new connection from a robot."""
        robot_id = None

        try:
            # Wait for registration message
            json_str = await websocket.recv()
            message = Message.from_json(json_str)

            if message.message_type != "registration":
                await websocket.close()
                return

            robot_id = message.sender_id
            self.connected_robots[robot_id] = websocket
            self.robot_capabilities[robot_id] = message.payload.get("capabilities", {})
            self.last_heartbeat[robot_id] = time.time()

            self.logger.info(
                f"Robot {robot_id} registered with capabilities: {self.robot_capabilities[robot_id]}"
            )

            # Handle messages in a loop
            async for json_str in websocket:
                try:
                    message = Message.from_json(json_str)

                    # Update heartbeat time for heartbeat messages
                    if message.message_type == "heartbeat":
                        self.last_heartbeat[robot_id] = time.time()
                        response = Message(
                            sender_id="server",
                            target_id=robot_id,
                            message_type="heartbeat_response",
                            payload={},
                        )
                        await websocket.send(response.to_json())
                        continue

                    # Process other messages
                    await self._process_message(message)

                    # Forward to target if specified
                    if (
                        message.target_id
                        and message.target_id != "server"
                        and message.target_id in self.connected_robots
                    ):
                        target_ws = self.connected_robots[message.target_id]
                        await target_ws.send(json_str)

                except Exception as e:
                    self.logger.error(f"Error processing message from {robot_id}: {e}")

        except websockets.exceptions.ConnectionClosed:
            self.logger.info(f"Connection with robot {robot_id} closed")
        except Exception as e:
            self.logger.error(f"Error handling connection: {e}")
        finally:
            if robot_id:
                if robot_id in self.connected_robots:
                    del self.connected_robots[robot_id]
                if robot_id in self.robot_capabilities:
                    del self.robot_capabilities[robot_id]
                if robot_id in self.last_heartbeat:
                    del self.last_heartbeat[robot_id]
                self.logger.info(f"Robot {robot_id} disconnected")

    async def _process_message(self, message: Message):
        """Process a received message."""
        # Dispatch to registered handlers
        handlers = self.message_handlers.get(message.message_type, [])
        for handler in handlers:
            try:
                await handler(message)
            except Exception as e:
                self.logger.error(f"Error in message handler: {e}")

    async def _monitor_heartbeats(self):
        """Monitor robot heartbeats and disconnect inactive robots."""
        while True:
            current_time = time.time()
            inactive_robots = []

            for robot_id, last_time in self.last_heartbeat.items():
                if current_time - last_time > self.heartbeat_timeout:
                    inactive_robots.append(robot_id)

            for robot_id in inactive_robots:
                self.logger.warning(f"Robot {robot_id} is inactive, disconnecting")
                if robot_id in self.connected_robots:
                    try:
                        await self.connected_robots[robot_id].close()
                    except:
                        pass
                    del self.connected_robots[robot_id]
                if robot_id in self.robot_capabilities:
                    del self.robot_capabilities[robot_id]
                if robot_id in self.last_heartbeat:
                    del self.last_heartbeat[robot_id]

            await asyncio.sleep(10)  # Check every 10 seconds

    async def broadcast_message(
        self, message_type: str, payload: Dict[str, Any]
    ) -> bool:
        """Broadcast a message to all connected robots."""
        if not self.connected_robots:
            return False

        message = Message(
            sender_id="server",
            message_type=message_type,
            payload=payload,
            target_id=None,  # broadcast
        )

        success = True
        for robot_id, websocket in self.connected_robots.items():
            try:
                await websocket.send(message.to_json())
            except Exception as e:
                self.logger.error(f"Failed to send message to {robot_id}: {e}")
                success = False

        return success

    async def send_message(
        self, target_id: str, message_type: str, payload: Dict[str, Any]
    ) -> bool:
        """Send a message to a specific robot."""
        if target_id not in self.connected_robots:
            return False

        message = Message(
            sender_id="server",
            message_type=message_type,
            payload=payload,
            target_id=target_id,
        )

        try:
            await self.connected_robots[target_id].send(message.to_json())
            return True
        except Exception as e:
            self.logger.error(f"Failed to send message to {target_id}: {e}")
            return False

    def register_handler(self, message_type: str, handler: Callable):
        """Register a handler for a specific message type."""
        if message_type not in self.message_handlers:
            self.message_handlers[message_type] = []
        self.message_handlers[message_type].append(handler)

    def get_connected_robots(self) -> List[str]:
        """Get a list of connected robot IDs."""
        return list(self.connected_robots.keys())

    def get_robot_capability(self, robot_id: str, capability_name: str) -> Any:
        """Get a specific capability of a robot."""
        if robot_id not in self.robot_capabilities:
            return None

        capabilities = self.robot_capabilities[robot_id]
        return capabilities.get(capability_name)

    async def stop_server(self):
        """Stop the coordination server."""
        if self.server:
            self.server.close()
            await self.server.wait_closed()
            self.logger.info("Server stopped")


class CommunicationVisualizer:
    """
    Visualizes the communication between robots.
    Provides tools to monitor message flow and network topology.
    """

    def __init__(self, server: CoordinationServer):
        self.server = server
        self.messages = []
        self.max_messages = 100  # Keep only the last 100 messages
        self.logger = logging.getLogger("CommunicationVisualizer")

    def start_monitoring(self):
        """Start monitoring messages."""
        self.server.register_handler("*", self._message_handler)
        self.logger.info("Started monitoring messages")

    async def _message_handler(self, message: Message):
        """Handle a message for visualization."""
        self.messages.append(
            {
                "id": message.id,
                "sender_id": message.sender_id,
                "target_id": message.target_id,
                "message_type": message.message_type,
                "timestamp": message.timestamp,
            }
        )

        # Limit the number of stored messages
        if len(self.messages) > self.max_messages:
            self.messages = self.messages[-self.max_messages :]

    def get_network_topology(self) -> Dict[str, List[str]]:
        """Get the current network topology."""
        topology = {}

        # Create nodes for each robot and the server
        robots = self.server.get_connected_robots()
        for robot_id in robots:
            topology[robot_id] = []

        topology["server"] = robots

        # Analyze messages to find connections between robots
        for message in self.messages:
            sender = message["sender_id"]
            target = message["target_id"]

            if (
                sender != "server"
                and target
                and target != "server"
                and target in topology
            ):
                if target not in topology[sender]:
                    topology[sender].append(target)

        return topology

    def get_message_stats(self) -> Dict[str, Any]:
        """Get statistics about messages."""
        if not self.messages:
            return {
                "total_messages": 0,
                "messages_per_type": {},
                "messages_per_robot": {},
            }

        total = len(self.messages)
        per_type = {}
        per_robot = {}

        for message in self.messages:
            # Count per type
            msg_type = message["message_type"]
            if msg_type not in per_type:
                per_type[msg_type] = 0
            per_type[msg_type] += 1

            # Count per robot (as sender)
            sender = message["sender_id"]
            if sender not in per_robot:
                per_robot[sender] = 0
            per_robot[sender] += 1

        return {
            "total_messages": total,
            "messages_per_type": per_type,
            "messages_per_robot": per_robot,
        }

    def get_message_timeline(
        self, start_time: float = None, end_time: float = None
    ) -> List[Dict[str, Any]]:
        """Get a timeline of messages in a time range."""
        if not start_time:
            start_time = 0
        if not end_time:
            end_time = time.time()

        return [
            message
            for message in self.messages
            if start_time <= message["timestamp"] <= end_time
        ]

    def get_bandwidth_usage(self, window_seconds: int = 60) -> Dict[str, float]:
        """Estimate bandwidth usage in the last window_seconds."""
        now = time.time()
        start_time = now - window_seconds

        # Count messages in the time window
        messages_in_window = [
            message
            for message in self.messages
            if start_time <= message["timestamp"] <= now
        ]

        # Estimate average message size (in bytes)
        avg_message_size = 200  # Just an estimate

        # Calculate bandwidth
        total_bytes = len(messages_in_window) * avg_message_size
        bytes_per_second = total_bytes / window_seconds if window_seconds > 0 else 0

        return {
            "messages_count": len(messages_in_window),
            "bytes_total": total_bytes,
            "bytes_per_second": bytes_per_second,
            "kbps": bytes_per_second * 8 / 1000,
        }
