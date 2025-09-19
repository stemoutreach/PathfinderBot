# PathfinderBot Python Package

This Python package provides a modular and well-organized codebase for the PathfinderBot robotics platform used for STEM outreach and education.

## Package Structure

The package is organized into the following modules:

- `core`: Core functionality for robot control, including the robot class, arm control, and mecanum wheel drive
- `detectors`: Various object detection modules, including AprilTag and block detection
- `web`: Web interface and WebSocket communication for remote control
- `navigation`: Navigation and mapping capabilities
- `utils`: Utility functions and common tools
- `education`: Educational components, including learning tracks, code templates, and challenges
- `config`: Configuration files and settings
- `simulations`: Simulation capabilities for testing without physical hardware

## Getting Started

### Installation

1. Clone the repository:
   ```
   git clone https://github.com/yourusername/PathfinderBot.git
   cd PathfinderBot
   ```

2. Install the required dependencies:
   ```
   pip install -r requirements.txt
   ```

3. Install the package in development mode:
   ```
   pip install -e .
   ```

### Running the PathfinderBot

The main entry point for the package is `run.py`. You can use the following commands to run different components:

```bash
# Start the web interface
python -m pathfinder_pkg.run --web

# Start the robot with AprilTag navigation
python -m pathfinder_pkg.run --apriltag-nav

# Start the robot with block detection
python -m pathfinder_pkg.run --block-detection

# Run a demo sequence
python -m pathfinder_pkg.run --demo

# Launch the Jupyter notebook server for educational content
python -m pathfinder_pkg.run --jupyter
```

Add the `--sim` flag to run in simulation mode without requiring physical hardware.

## Educational Components

The package includes several educational components to help students learn robotics:

### Learning Tracks

Learning tracks provide a structured curriculum with progressive difficulty levels.

```python
from pathfinder_pkg.education.learning_levels import LearningTrackManager

# Load available tracks
manager = LearningTrackManager()
manager.load_tracks()

# Get a specific track
track = manager.get_track("track_id")
```

### Code Templates

Code templates provide scaffolded coding exercises with fill-in-the-blank portions.

```python
from pathfinder_pkg.education.code_templates import TemplateManager

# Load available templates
manager = TemplateManager()
manager.load_templates()

# Get a specific template
template = manager.get_template("template_id")
```

### Challenges

Challenges provide goal-oriented activities with specific success criteria.

```python
from pathfinder_pkg.education.challenge_system import ChallengeManager

# Load available challenges
manager = ChallengeManager()
manager.load_challenges()

# Get a specific challenge
challenge = manager.get_challenge("challenge_id")
```

### Jupyter Notebook Integration

For interactive learning, the package integrates with Jupyter notebooks:

```python
from pathfinder_pkg.education.jupyter_integration import (
    display_robot_controls,
    display_learning_track_selector,
    display_code_template,
    display_challenge_selector
)

# Display interactive robot controls
robot = display_robot_controls(use_simulator=True)

# Display learning track selector
tracks = display_learning_track_selector()

# Display code template selector
templates = display_code_template()

# Display challenge selector
challenges = display_challenge_selector()
```

## Development

### Coding Standards

- Follow PEP 8 style guidelines
- Use Google-style docstrings
- Write unit tests for all new features
- Keep modules focused and cohesive

### Testing

Run the test suite:

```bash
pytest
```

## License

This project is licensed under the MIT License - see the LICENSE file for details.
