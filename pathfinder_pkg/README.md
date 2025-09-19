# PathfinderBot Package

This package contains the improved codebase for the PathfinderBot robotics platform, implementing the enhancements outlined in the PathfinderBot Improvement PRD.

## Overview

The PathfinderBot is a sophisticated robotics platform built for STEM outreach and education. It features a mobile robot with mecanum wheels for omnidirectional movement, a 5-DOF robotic arm with gripper, camera system with AprilTag detection, and various sensors.

This package provides a complete, well-organized Python framework for controlling the robot, processing sensor data, detecting objects, and providing web interfaces for remote control.

## Package Structure

The package is organized into several modules:

```
pathfinder_pkg/
├── __init__.py        # Package initialization
├── core/              # Core robot functionality
│   ├── __init__.py
│   ├── robot.py       # Main robot class
│   └── mecanum.py     # Mecanum drive control
├── detectors/         # Computer vision detectors
│   ├── __init__.py
│   ├── base.py        # Base detector class
│   └── block_detector.py  # Enhanced block detector
├── web/               # Web interface components
│   ├── __init__.py
│   ├── server.py      # Flask web server
│   ├── websocket.py   # WebSocket server
│   └── templates/     # HTML templates
│       ├── index.html
│       └── drive.html
├── utils/             # Utility functions
│   ├── __init__.py
│   └── logging.py     # Logging configuration
├── navigation/        # Navigation and mapping
│   └── __init__.py
├── config/            # Configuration files
│   └── __init__.py
└── run.py             # Main entry point
```

## Key Improvements

### 1. Code Organization and Documentation

- Created a proper Python package structure with `__init__.py` files
- Implemented a common logging framework across modules
- Added comprehensive docstrings to all functions, classes, and modules
- Standardized naming conventions across modules

### 2. Enhanced Block Detection and Manipulation

- Improved block detector with better color segmentation and shape analysis
- Added feedback mechanisms during block pickup using the camera
- Implemented retry mechanisms for failed pickup attempts
- Created better tracking of blocks across frames

### 3. Web Interface Enhancements

- Created a unified, responsive web UI that works well on mobile devices
- Implemented WebSockets for real-time communication instead of polling
- Added a telemetry dashboard showing robot state, battery, sensor readings
- Created recording and replay functionality for robot movements

### 4. Navigation and Mapping

*To be implemented in future releases.*

## Usage

### Running the System

To start the PathfinderBot system:

```bash
python -m pathfinder_pkg.run
```

Command line options:

```
--web-port PORT     Port for the web server (default: 5000)
--ws-port PORT      Port for the WebSocket server (default: 8765)
--host HOST         Host address to bind servers to (default: 0.0.0.0)
--debug             Enable debug mode
--no-robot          Run without connecting to robot hardware
--log-level LEVEL   Set the logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
```

### Web Interface

The web interface is available at:

- Main interface: http://localhost:5000/
- Drive control: http://localhost:5000/drive
- Block detection: http://localhost:5000/blocks
- Telemetry dashboard: http://localhost:5000/telemetry

### API Endpoints

The system provides several REST API endpoints:

- `GET /api/status` - Get system status
- `POST /api/robot/move` - Move the robot
- `POST /api/robot/stop` - Stop the robot
- `POST /api/recording/start` - Start recording movements
- `POST /api/recording/stop` - Stop recording
- `GET /api/recording/list` - List available recordings
- `POST /api/recording/play` - Play back a recording

## Development

### Adding New Components

To add a new component to the robot:

1. Create a new class for your component
2. Add it to the robot in `init_robot()` function in `run.py`:

```python
from pathfinder_pkg.your_module import YourComponent

# In init_robot()
your_component = YourComponent()
robot.add_component('your_component_name', your_component)
```

### Adding New Detectors

To create a new detector:

1. Create a new class that inherits from `Detector` in `detectors/base.py`
2. Implement the required `infer()` method
3. Register it in the appropriate place (e.g., `run.py` or a detector manager)

## Dependencies

- Python 3.7+
- OpenCV
- NumPy
- Flask
- Websockets
- Various hardware-specific libraries (depending on your robot configuration)

## Future Work

- Implement SLAM (Simultaneous Localization And Mapping)
- Add multi-robot coordination capabilities
- Create more educational extensions
- Optimize performance for resource-constrained hardware
- Add comprehensive testing suite
