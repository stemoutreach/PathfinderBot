"""
Multi-Robot Coordination Package
===============================

This package provides tools for coordinating multiple PathfinderBot robots,
enabling collaborative behaviors, formation control, and task allocation.

Components:
- communication: Robot-to-robot and robot-to-server communication
- algorithms: Core coordination algorithms (task allocation, formation control, etc.)
- behaviors: Collaborative behaviors (object transport, area coverage, etc.)
- ui: User interface for controlling and visualizing multi-robot systems
"""

from .communication import Message, CoordinationServer
from .algorithms import (
    Position,
    Pose,
    RobotState,
    Task,
    TaskPriority,
    TaskAllocator,
    FormationControl,
    CollisionAvoidance,
)
from .behaviors import (
    TransportRole,
    CoverageStatus,
    GameRole,
    ObjectTransportBehavior,
    AreaCoverageBehavior,
    CollaborativeGameBehavior,
)
from .ui import CoordinationDashboard, launch_dashboard

__version__ = "0.1.0"
