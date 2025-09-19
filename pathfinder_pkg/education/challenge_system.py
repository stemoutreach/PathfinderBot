"""
Challenge System for PathfinderBot Educational Framework

This module provides a framework for creating, managing, and tracking progress
on educational robotics challenges using the PathfinderBot platform.
"""

import os
import json
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Any, Callable

from pathfinder_pkg.utils.logging import get_logger
from pathfinder_pkg.education.learning_levels import DifficultyLevel

logger = get_logger(__name__)


class ChallengeStatus(Enum):
    """Status of a challenge attempt."""

    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


class ChallengeCategory(Enum):
    """Categories of challenges."""

    NAVIGATION = "navigation"
    OBJECT_DETECTION = "object_detection"
    OBJECT_MANIPULATION = "object_manipulation"
    MAPPING = "mapping"
    MAZE_SOLVING = "maze_solving"
    OBSTACLE_AVOIDANCE = "obstacle_avoidance"
    LINE_FOLLOWING = "line_following"
    MULTI_ROBOT = "multi_robot"
    CUSTOM = "custom"


@dataclass
class ChallengeStage:
    """A stage within a challenge."""

    id: str
    name: str
    description: str
    success_criteria: str
    hints: List[str] = field(default_factory=list)
    completed: bool = False


@dataclass
class Challenge:
    """Represents a robotics challenge for educational purposes."""

    id: str
    name: str
    description: str
    difficulty: DifficultyLevel
    category: ChallengeCategory
    stages: List[ChallengeStage] = field(default_factory=list)
    prerequisites: List[str] = field(default_factory=list)
    learning_objectives: List[str] = field(default_factory=list)
    resources: Dict[str, str] = field(default_factory=dict)
    tags: List[str] = field(default_factory=list)
    estimated_time_minutes: int = 60
    author: str = ""
    status: ChallengeStatus = ChallengeStatus.NOT_STARTED

    def add_stage(self, stage: ChallengeStage) -> None:
        """Add a stage to the challenge."""
        self.stages.append(stage)
        logger.info(f"Added stage '{stage.name}' to challenge '{self.name}'")

    def complete_stage(self, stage_id: str) -> bool:
        """Mark a stage as completed."""
        for stage in self.stages:
            if stage.id == stage_id:
                stage.completed = True
                logger.info(
                    f"Marked stage '{stage.name}' as completed in challenge '{self.name}'"
                )
                if all(s.completed for s in self.stages):
                    self.status = ChallengeStatus.COMPLETED
                    logger.info(f"Challenge '{self.name}' completed!")
                else:
                    self.status = ChallengeStatus.IN_PROGRESS
                return True
        return False

    def reset(self) -> None:
        """Reset the challenge status and all stages."""
        self.status = ChallengeStatus.NOT_STARTED
        for stage in self.stages:
            stage.completed = False
        logger.info(f"Reset challenge '{self.name}'")

    def get_stage(self, stage_id: str) -> Optional[ChallengeStage]:
        """Get a stage by ID."""
        for stage in self.stages:
            if stage.id == stage_id:
                return stage
        return None

    def completion_percentage(self) -> float:
        """Calculate the percentage of completed stages."""
        if not self.stages:
            return 0.0
        completed = sum(1 for stage in self.stages if stage.completed)
        return (completed / len(self.stages)) * 100


class ChallengeManager:
    """Manages challenges for the educational framework."""

    def __init__(self, challenges_dir: str = None):
        """Initialize the challenge manager."""
        if challenges_dir is None:
            base_dir = os.path.dirname(os.path.abspath(__file__))
            challenges_dir = os.path.join(base_dir, "challenges")

        self.challenges_dir = challenges_dir
        self.challenges: Dict[str, Challenge] = {}

        # Ensure challenges directory exists
        os.makedirs(self.challenges_dir, exist_ok=True)

        logger.info(
            f"Initialized ChallengeManager with challenges directory: {self.challenges_dir}"
        )

    def load_challenges(self) -> None:
        """Load all challenges from the challenges directory."""
        challenge_files = [
            f for f in os.listdir(self.challenges_dir) if f.endswith(".json")
        ]

        for challenge_file in challenge_files:
            try:
                with open(os.path.join(self.challenges_dir, challenge_file), "r") as f:
                    challenge_data = json.load(f)

                # Process each challenge in the file
                for challenge_entry in challenge_data:
                    try:
                        challenge = self._parse_challenge_from_json(challenge_entry)
                        if challenge:
                            self.challenges[challenge.id] = challenge
                            logger.info(f"Loaded challenge: {challenge.name}")
                    except Exception as e:
                        logger.error(f"Error processing challenge: {str(e)}")

            except Exception as e:
                logger.error(
                    f"Error loading challenges from {challenge_file}: {str(e)}"
                )

        logger.info(f"Loaded {len(self.challenges)} challenges")

    def _parse_challenge_from_json(self, challenge_data: dict) -> Optional[Challenge]:
        """Parse a challenge from JSON data."""
        try:
            stages = []
            for stage_data in challenge_data.get("stages", []):
                stage = ChallengeStage(
                    id=stage_data["id"],
                    name=stage_data["name"],
                    description=stage_data["description"],
                    success_criteria=stage_data["success_criteria"],
                    hints=stage_data.get("hints", []),
                )
                stages.append(stage)

            challenge = Challenge(
                id=challenge_data["id"],
                name=challenge_data["name"],
                description=challenge_data["description"],
                difficulty=DifficultyLevel(challenge_data["difficulty"]),
                category=ChallengeCategory(challenge_data["category"]),
                stages=stages,
                prerequisites=challenge_data.get("prerequisites", []),
                learning_objectives=challenge_data.get("learning_objectives", []),
                resources=challenge_data.get("resources", {}),
                tags=challenge_data.get("tags", []),
                estimated_time_minutes=challenge_data.get("estimated_time_minutes", 60),
                author=challenge_data.get("author", ""),
            )

            return challenge
        except KeyError as e:
            logger.error(f"Missing required field in challenge data: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"Error parsing challenge data: {str(e)}")
            return None

    def get_challenge(self, challenge_id: str) -> Optional[Challenge]:
        """Get a challenge by ID."""
        return self.challenges.get(challenge_id)

    def get_challenges_by_difficulty(
        self, difficulty: DifficultyLevel
    ) -> List[Challenge]:
        """Get all challenges of a specific difficulty."""
        return [c for c in self.challenges.values() if c.difficulty == difficulty]

    def get_challenges_by_category(
        self, category: ChallengeCategory
    ) -> List[Challenge]:
        """Get all challenges in a specific category."""
        return [c for c in self.challenges.values() if c.category == category]

    def search_challenges(self, query: str) -> List[Challenge]:
        """Search challenges by name, description, or tags."""
        query = query.lower()
        results = []

        for challenge in self.challenges.values():
            if (
                query in challenge.name.lower()
                or query in challenge.description.lower()
                or any(query in tag.lower() for tag in challenge.tags)
            ):
                results.append(challenge)

        return results

    def save_progress(self, user_id: str) -> bool:
        """Save the user's challenge progress."""
        try:
            progress_dir = os.path.join(self.challenges_dir, "progress")
            os.makedirs(progress_dir, exist_ok=True)

            progress_data = {}
            for challenge_id, challenge in self.challenges.items():
                if challenge.status != ChallengeStatus.NOT_STARTED:
                    completed_stages = [
                        stage.id for stage in challenge.stages if stage.completed
                    ]
                    progress_data[challenge_id] = {
                        "status": challenge.status.value,
                        "completed_stages": completed_stages,
                    }

            progress_file = os.path.join(progress_dir, f"{user_id}_challenges.json")
            with open(progress_file, "w") as f:
                json.dump(progress_data, f, indent=2)

            logger.info(f"Saved challenge progress for user {user_id}")
            return True
        except Exception as e:
            logger.error(f"Error saving challenge progress: {str(e)}")
            return False

    def load_progress(self, user_id: str) -> bool:
        """Load the user's challenge progress."""
        try:
            progress_file = os.path.join(
                self.challenges_dir, "progress", f"{user_id}_challenges.json"
            )

            if not os.path.exists(progress_file):
                logger.info(f"No progress file found for user {user_id}")
                return False

            with open(progress_file, "r") as f:
                progress_data = json.load(f)

            for challenge_id, progress in progress_data.items():
                challenge = self.challenges.get(challenge_id)
                if challenge:
                    challenge.status = ChallengeStatus(progress["status"])
                    for stage_id in progress.get("completed_stages", []):
                        for stage in challenge.stages:
                            if stage.id == stage_id:
                                stage.completed = True

            logger.info(f"Loaded challenge progress for user {user_id}")
            return True
        except Exception as e:
            logger.error(f"Error loading challenge progress: {str(e)}")
            return False


# Example challenge creation function
def create_example_challenges(manager: ChallengeManager) -> None:
    """Create example challenges for educational purposes."""
    # Create challenges directory if it doesn't exist
    os.makedirs(manager.challenges_dir, exist_ok=True)

    # Define some example challenges
    challenges = [
        {
            "id": "navigation_basic",
            "name": "Basic Robot Navigation",
            "description": "Learn to program the robot to navigate through a simple course with waypoints.",
            "difficulty": "beginner",
            "category": "navigation",
            "learning_objectives": [
                "Understand basic robot movement commands",
                "Learn to plan a simple path",
                "Practice sequential programming",
            ],
            "estimated_time_minutes": 30,
            "tags": ["navigation", "beginner", "movement"],
            "stages": [
                {
                    "id": "nav_basic_1",
                    "name": "Forward and Backward",
                    "description": "Program the robot to move forward 1 meter, then backward to its starting position.",
                    "success_criteria": "Robot returns to within 5cm of its starting position.",
                    "hints": [
                        "Use robot.forward() and robot.backward() methods.",
                        "Remember to use robot.sleep() to give the robot time to move.",
                    ],
                },
                {
                    "id": "nav_basic_2",
                    "name": "Square Path",
                    "description": "Program the robot to move in a 1-meter square path, returning to its starting position.",
                    "success_criteria": "Robot completes a square and returns to within 10cm of starting position.",
                    "hints": [
                        "Break down the square into four straight movements with turns in between.",
                        "Use robot.turn_left() or robot.turn_right() for the turns.",
                        "You'll need 90-degree turns at each corner.",
                    ],
                },
                {
                    "id": "nav_basic_3",
                    "name": "Navigate to Target",
                    "description": "Program the robot to navigate to a marked target placed at a specific position.",
                    "success_criteria": "Robot stops on the target marker.",
                    "hints": [
                        "You'll need to combine multiple movements and turns.",
                        "Test your program with small movements first.",
                        "Consider using the camera to detect when you've reached the target.",
                    ],
                },
            ],
        },
        {
            "id": "object_detection_basic",
            "name": "Basic Object Detection",
            "description": "Learn to use the robot's camera to detect and identify objects of different colors.",
            "difficulty": "intermediate",
            "category": "object_detection",
            "prerequisites": ["navigation_basic"],
            "learning_objectives": [
                "Understand basic computer vision concepts",
                "Learn to process camera images",
                "Implement color-based object detection",
            ],
            "estimated_time_minutes": 45,
            "tags": ["vision", "camera", "detection", "color"],
            "stages": [
                {
                    "id": "obj_det_1",
                    "name": "Color Calibration",
                    "description": "Capture images of red, green, and blue objects and determine the HSV color ranges for detection.",
                    "success_criteria": "Successfully identify HSV ranges that detect each color with minimal false positives.",
                    "hints": [
                        "Use cv2.cvtColor() to convert from BGR to HSV color space.",
                        "Start with wide ranges and narrow them down based on results.",
                        "Test with different lighting conditions.",
                    ],
                },
                {
                    "id": "obj_det_2",
                    "name": "Object Location",
                    "description": "Detect colored objects and determine their locations in the image.",
                    "success_criteria": "Correctly identify the center coordinates of each colored object.",
                    "hints": [
                        "Use cv2.findContours() to find the object boundaries.",
                        "Calculate the centroid of each contour.",
                        "Use cv2.moments() to find the center of mass.",
                    ],
                },
                {
                    "id": "obj_det_3",
                    "name": "Multi-Object Tracking",
                    "description": "Track multiple colored objects as they move in the robot's field of view.",
                    "success_criteria": "Maintain tracking of multiple objects as they move, with correct color identification.",
                    "hints": [
                        "Implement a simple tracking algorithm based on object position.",
                        "Consider using a threshold for movement to avoid jitter.",
                        "You might need to implement some form of filtering to smooth the detection.",
                    ],
                },
            ],
        },
    ]

    # Write challenges to a JSON file
    with open(
        os.path.join(manager.challenges_dir, "example_challenges.json"), "w"
    ) as f:
        json.dump(challenges, f, indent=2)

    logger.info("Created example challenges file")
