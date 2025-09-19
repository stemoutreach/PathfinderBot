"""
Code Templates for PathfinderBot Educational Framework

This module provides code templates for different skill levels and learning objectives.
Templates can be filled in by students to learn specific concepts and complete
educational activities.
"""

import os
import json
from dataclasses import dataclass, field
from typing import Dict, List, Optional
from enum import Enum

from pathfinder_pkg.utils.logging import get_logger
from pathfinder_pkg.education.learning_levels import DifficultyLevel

logger = get_logger(__name__)


class TemplateCategory(Enum):
    """Categories of code templates."""

    ROBOT_CONTROL = "robot_control"
    COMPUTER_VISION = "computer_vision"
    SENSORS = "sensors"
    PATH_PLANNING = "path_planning"
    OBJECT_MANIPULATION = "object_manipulation"
    WEB_INTERFACE = "web_interface"


@dataclass
class CodeTemplate:
    """Represents a code template for educational purposes."""

    id: str
    name: str
    description: str
    difficulty: DifficultyLevel
    category: TemplateCategory
    template_code: str
    solution_code: str
    hints: List[str] = field(default_factory=list)
    prerequisites: List[str] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)

    def get_with_placeholders_filled(self, replacements: Dict[str, str]) -> str:
        """Get the template with placeholders filled in."""
        result = self.template_code
        for key, value in replacements.items():
            placeholder = f"{{{{ {key} }}}}"
            result = result.replace(placeholder, value)
        return result

    def get_diff_with_solution(self, student_code: str) -> List[str]:
        """Compare student code with solution and return differences."""
        # This is a simple implementation; in a real system, you'd use a proper diff algorithm
        student_lines = student_code.strip().split("\n")
        solution_lines = self.solution_code.strip().split("\n")

        diffs = []
        for i, (student, solution) in enumerate(zip(student_lines, solution_lines)):
            if student.strip() != solution.strip():
                diffs.append(
                    f"Line {i+1}: Expected '{solution.strip()}', got '{student.strip()}'"
                )

        # Check for length differences
        if len(student_lines) < len(solution_lines):
            diffs.append(
                f"Missing lines: expected {len(solution_lines)} lines, got {len(student_lines)}"
            )
        elif len(student_lines) > len(solution_lines):
            diffs.append(
                f"Extra lines: expected {len(solution_lines)} lines, got {len(student_lines)}"
            )

        return diffs


class TemplateManager:
    """Manages code templates for the educational framework."""

    def __init__(self, templates_dir: str = None):
        """Initialize the template manager."""
        if templates_dir is None:
            base_dir = os.path.dirname(os.path.abspath(__file__))
            templates_dir = os.path.join(base_dir, "templates")

        self.templates_dir = templates_dir
        self.templates: Dict[str, CodeTemplate] = {}

        # Ensure templates directory exists
        os.makedirs(self.templates_dir, exist_ok=True)

        logger.info(
            f"Initialized TemplateManager with templates directory: {self.templates_dir}"
        )

    def load_templates(self) -> None:
        """Load templates from the templates directory."""
        template_files = [
            f for f in os.listdir(self.templates_dir) if f.endswith(".json")
        ]

        for template_file in template_files:
            try:
                with open(os.path.join(self.templates_dir, template_file), "r") as f:
                    template_data = json.load(f)

                # Process each template in the file
                for template_entry in template_data:
                    try:
                        template = CodeTemplate(
                            id=template_entry["id"],
                            name=template_entry["name"],
                            description=template_entry["description"],
                            difficulty=DifficultyLevel(template_entry["difficulty"]),
                            category=TemplateCategory(template_entry["category"]),
                            template_code=template_entry["template_code"],
                            solution_code=template_entry["solution_code"],
                            hints=template_entry.get("hints", []),
                            prerequisites=template_entry.get("prerequisites", []),
                            tags=template_entry.get("tags", []),
                        )
                        self.templates[template.id] = template
                        logger.info(f"Loaded template: {template.name}")
                    except KeyError as e:
                        logger.error(f"Missing required field in template: {str(e)}")
                    except Exception as e:
                        logger.error(f"Error processing template: {str(e)}")

            except Exception as e:
                logger.error(f"Error loading templates from {template_file}: {str(e)}")

        logger.info(f"Loaded {len(self.templates)} templates")

    def get_template(self, template_id: str) -> Optional[CodeTemplate]:
        """Get a template by ID."""
        return self.templates.get(template_id)

    def get_templates_by_difficulty(
        self, difficulty: DifficultyLevel
    ) -> List[CodeTemplate]:
        """Get templates by difficulty level."""
        return [t for t in self.templates.values() if t.difficulty == difficulty]

    def get_templates_by_category(
        self, category: TemplateCategory
    ) -> List[CodeTemplate]:
        """Get templates by category."""
        return [t for t in self.templates.values() if t.category == category]

    def search_templates(self, query: str) -> List[CodeTemplate]:
        """Search templates by name, description, or tags."""
        query = query.lower()
        results = []

        for template in self.templates.values():
            if (
                query in template.name.lower()
                or query in template.description.lower()
                or any(query in tag.lower() for tag in template.tags)
            ):
                results.append(template)

        return results


# Example template creation function
def create_example_templates(manager: TemplateManager) -> None:
    """Create example templates for different learning levels."""
    # Create templates directory if it doesn't exist
    os.makedirs(manager.templates_dir, exist_ok=True)

    # Define some example templates
    templates = [
        {
            "id": "basic_movement_1",
            "name": "Basic Robot Movement",
            "description": "Learn how to control basic robot movement using the PathfinderBot API.",
            "difficulty": "beginner",
            "category": "robot_control",
            "template_code": """# Basic Robot Movement
# Fill in the code to make the robot move forward, backward, left, and right

from pathfinder_pkg.core.robot import Robot

def main():
    # Initialize the robot
    robot = Robot()
    
    # TODO: Make the robot move forward for 2 seconds
    # {{ forward_movement }}
    
    # TODO: Make the robot move backward for 2 seconds
    # {{ backward_movement }}
    
    # TODO: Make the robot turn left for 1 second
    # {{ left_turn }}
    
    # TODO: Make the robot turn right for 1 second
    # {{ right_turn }}
    
    # Stop the robot
    robot.stop()
    
if __name__ == "__main__":
    main()""",
            "solution_code": """# Basic Robot Movement
# Fill in the code to make the robot move forward, backward, left, and right

from pathfinder_pkg.core.robot import Robot

def main():
    # Initialize the robot
    robot = Robot()
    
    # Make the robot move forward for 2 seconds
    robot.forward(0.5)  # 50% speed
    robot.sleep(2)
    
    # Make the robot move backward for 2 seconds
    robot.backward(0.5)  # 50% speed
    robot.sleep(2)
    
    # Make the robot turn left for 1 second
    robot.turn_left(0.3)  # 30% speed
    robot.sleep(1)
    
    # Make the robot turn right for 1 second
    robot.turn_right(0.3)  # 30% speed
    robot.sleep(1)
    
    # Stop the robot
    robot.stop()
    
if __name__ == "__main__":
    main()""",
            "hints": [
                "Use robot.forward(speed) to move forward. Speed is a value between 0 and 1.",
                "Use robot.backward(speed) to move backward.",
                "Use robot.turn_left(speed) and robot.turn_right(speed) for turning.",
                "Use robot.sleep(seconds) to wait for a specific duration.",
            ],
            "tags": ["movement", "beginner", "control", "motors"],
        },
        {
            "id": "color_detection_1",
            "name": "Basic Color Detection",
            "description": "Learn how to detect colored objects using the PathfinderBot's camera.",
            "difficulty": "intermediate",
            "category": "computer_vision",
            "template_code": """# Basic Color Detection
# Fill in the code to detect red, green, and blue objects

import cv2
import numpy as np
from pathfinder_pkg.core.robot import Robot
from pathfinder_pkg.detectors.block_detector import BlockDetector

def main():
    # Initialize the robot and camera
    robot = Robot()
    detector = BlockDetector()
    
    # Capture an image
    image = robot.camera.capture()
    
    # TODO: Define color ranges for red, green, and blue in HSV
    # {{ color_ranges }}
    
    # TODO: Create masks for each color
    # {{ create_masks }}
    
    # TODO: Find contours in each mask
    # {{ find_contours }}
    
    # TODO: Draw bounding boxes around detected objects
    # {{ draw_boxes }}
    
    # Display the result
    cv2.imshow("Detected Colors", image)
    cv2.waitKey(0)
    cv2.destroyAllWindows()
    
if __name__ == "__main__":
    main()""",
            "solution_code": """# Basic Color Detection
# Fill in the code to detect red, green, and blue objects

import cv2
import numpy as np
from pathfinder_pkg.core.robot import Robot
from pathfinder_pkg.detectors.block_detector import BlockDetector

def main():
    # Initialize the robot and camera
    robot = Robot()
    detector = BlockDetector()
    
    # Capture an image
    image = robot.camera.capture()
    
    # Convert to HSV color space
    hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
    
    # Define color ranges for red, green, and blue in HSV
    red_lower = np.array([0, 100, 100])
    red_upper = np.array([10, 255, 255])
    
    green_lower = np.array([40, 100, 100])
    green_upper = np.array([80, 255, 255])
    
    blue_lower = np.array([100, 100, 100])
    blue_upper = np.array([140, 255, 255])
    
    # Create masks for each color
    red_mask = cv2.inRange(hsv, red_lower, red_upper)
    green_mask = cv2.inRange(hsv, green_lower, green_upper)
    blue_mask = cv2.inRange(hsv, blue_lower, blue_upper)
    
    # Find contours in each mask
    red_contours, _ = cv2.findContours(red_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    green_contours, _ = cv2.findContours(green_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    blue_contours, _ = cv2.findContours(blue_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    # Draw bounding boxes around detected objects
    for contour in red_contours:
        if cv2.contourArea(contour) > 500:  # Minimum size threshold
            x, y, w, h = cv2.boundingRect(contour)
            cv2.rectangle(image, (x, y), (x + w, y + h), (0, 0, 255), 2)
            cv2.putText(image, "Red", (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 2)
    
    for contour in green_contours:
        if cv2.contourArea(contour) > 500:
            x, y, w, h = cv2.boundingRect(contour)
            cv2.rectangle(image, (x, y), (x + w, y + h), (0, 255, 0), 2)
            cv2.putText(image, "Green", (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
    
    for contour in blue_contours:
        if cv2.contourArea(contour) > 500:
            x, y, w, h = cv2.boundingRect(contour)
            cv2.rectangle(image, (x, y), (x + w, y + h), (255, 0, 0), 2)
            cv2.putText(image, "Blue", (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 0, 0), 2)
    
    # Display the result
    cv2.imshow("Detected Colors", image)
    cv2.waitKey(0)
    cv2.destroyAllWindows()
    
if __name__ == "__main__":
    main()""",
            "hints": [
                "Convert the BGR image to HSV using cv2.cvtColor(image, cv2.COLOR_BGR2HSV).",
                "Red is typically in the range of 0-10 and 160-180 in the H channel.",
                "Green is typically in the range of 40-80 in the H channel.",
                "Blue is typically in the range of 100-140 in the H channel.",
                "Use cv2.inRange(hsv, lower_bound, upper_bound) to create color masks.",
                "Use cv2.findContours() to find shapes in each mask.",
                "Filter contours by area to ignore small noise.",
            ],
            "prerequisites": ["basic_movement_1"],
            "tags": ["vision", "opencv", "color detection", "intermediate"],
        },
    ]

    # Write templates to a JSON file
    with open(os.path.join(manager.templates_dir, "example_templates.json"), "w") as f:
        json.dump(templates, f, indent=2)

    logger.info("Created example templates file")
