# PathfinderBot Multi-Robot Coordination

This module provides tools and capabilities for coordinating multiple PathfinderBots, enabling them to work together, communicate, and solve problems collaboratively.

## Features

- **Robot-to-Robot Communication**: Reliable message passing between robots
- **Task Allocation**: Efficient distribution of tasks among available robots
- **Formation Control**: Various formation patterns with obstacle avoidance
- **Collaborative Behaviors**: Object transport, area coverage, and collaborative games
- **Dashboard UI**: Comprehensive visualization and control interface

## Architecture

The coordination module consists of several key components:

- `communication.py`: Implements the messaging protocol and server infrastructure
- `algorithms.py`: Core coordination algorithms for task allocation, formation control, etc.
- `behaviors.py`: Implementation of collaborative behaviors
- `ui.py`: User interface components for the coordination dashboard

## Getting Started

### Basic Usage

```python
from pathfinder_pkg.coordination import launch_dashboard, CoordinationServer

# Create a coordination server
server = CoordinationServer()

# Connect robots to the server
# (This happens automatically when robots run with coordination enabled)

# Launch the coordination dashboard
launch_dashboard(server)
```

### Running the Demo

A demonstration script is provided to showcase the multi-robot coordination capabilities:

```bash
python -m pathfinder_pkg.coordination_demo
```

This will simulate multiple robots and launch the coordination dashboard.

## Dashboard Usage

The coordination dashboard provides multiple views:

1. **Main Dashboard**: Overview of all robots and their status
2. **Task Allocation**: Interface for assigning tasks to robots
3. **Formation Control**: Tools for creating and maintaining robot formations
4. **Area Coverage**: Dashboard for efficient area coverage operations
5. **Object Transport**: Interface for coordinating object transport
6. **Collaborative Games**: Dashboard for robot games and competitions

## Implementation Details

### Communication Protocol

The communication system provides:

- Reliable message delivery
- Robot discovery
- Heartbeat monitoring
- Encrypted communication

### Coordination Algorithms

- **Task Allocation**: Auction-based and consensus algorithms
- **Formation Control**: Leader-follower and virtual structure approaches
- **Collision Avoidance**: Velocity obstacles and priority-based resolution

### Collaborative Behaviors

- **Object Transport**: Coordinated lifting and carrying of large objects
- **Area Coverage**: Efficient multi-robot exploration and mapping
- **Collaborative Games**: Robot soccer, relay races, and cooperative puzzles

## Integration with Robot Controllers

To enable coordination on a robot:

```python
from pathfinder_pkg.coordination import CoordinationClient
from pathfinder_pkg.core.robot import Robot

robot = Robot()
coordination_client = CoordinationClient(robot, server_address="192.168.1.100")
coordination_client.start()

# Robot will now participate in coordination activities
```

## Future Enhancements

- Improved fault tolerance
- Dynamic role assignment
- Learning-based coordination strategies
- Enhanced visualization tools
