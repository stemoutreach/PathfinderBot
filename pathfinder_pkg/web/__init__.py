"""
Web interface modules for PathfinderBot.

This package provides web interfaces for controlling and monitoring
the PathfinderBot, including HTTP and WebSocket servers.
"""

from .websocket import WebSocketServer, RobotWebSocketServer

__all__ = ["WebSocketServer", "RobotWebSocketServer"]
