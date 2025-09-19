"""
Learning Levels Framework for PathfinderBot

This module defines the progressive learning framework with multiple difficulty levels
and learning tracks. It provides a structured approach to learning robotics concepts
from beginner to advanced levels.
"""

import enum
import json
import os
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from pathfinder_pkg.utils.logging import get_logger

logger = get_logger(__name__)


class DifficultyLevel(enum.Enum):
    """Enumeration of difficulty levels for educational content."""

    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"


class TrackType(enum.Enum):
    """Types of learning tracks available in the educational framework."""

    ROBOTICS = "robotics"
    COMPUTER_VISION = "computer_vision"
    PROGRAMMING = "programming"
    MECHATRONICS = "mechatronics"
    AI = "artificial_intelligence"


@dataclass
class LearningObjective:
    """Represents a specific learning objective within a level."""

    id: str
    name: str
    description: str
    estimated_time_minutes: int
    prerequisites: List[str] = field(default_factory=list)
    resources: Dict[str, str] = field(default_factory=dict)
    completed: bool = False


@dataclass
class LearningLevel:
    """Represents a specific level within a learning track."""

    id: str
    name: str
    description: str
    difficulty: DifficultyLevel
    objectives: List[LearningObjective] = field(default_factory=list)

    def add_objective(self, objective: LearningObjective) -> None:
        """Add a learning objective to this level."""
        self.objectives.append(objective)
        logger.info(f"Added objective '{objective.name}' to level '{self.name}'")

    def get_objective(self, objective_id: str) -> Optional[LearningObjective]:
        """Get a specific learning objective by ID."""
        for objective in self.objectives:
            if objective.id == objective_id:
                return objective
        return None

    def complete_objective(self, objective_id: str) -> bool:
        """Mark a learning objective as completed."""
        objective = self.get_objective(objective_id)
        if objective:
            objective.completed = True
            logger.info(f"Marked objective '{objective.name}' as completed")
            return True
        logger.warning(f"Objective '{objective_id}' not found in level '{self.name}'")
        return False

    def is_completed(self) -> bool:
        """Check if all objectives in this level are completed."""
        return all(objective.completed for objective in self.objectives)

    def completion_percentage(self) -> float:
        """Calculate the percentage of completed objectives."""
        if not self.objectives:
            return 0.0
        completed = sum(1 for obj in self.objectives if obj.completed)
        return (completed / len(self.objectives)) * 100


@dataclass
class LearningTrack:
    """Represents a complete learning track with multiple levels."""

    id: str
    name: str
    description: str
    track_type: TrackType
    levels: List[LearningLevel] = field(default_factory=list)

    def add_level(self, level: LearningLevel) -> None:
        """Add a learning level to this track."""
        self.levels.append(level)
        logger.info(f"Added level '{level.name}' to track '{self.name}'")

    def get_level(self, level_id: str) -> Optional[LearningLevel]:
        """Get a specific level by ID."""
        for level in self.levels:
            if level.id == level_id:
                return level
        return None

    def get_level_by_difficulty(
        self, difficulty: DifficultyLevel
    ) -> List[LearningLevel]:
        """Get all levels of a specific difficulty."""
        return [level for level in self.levels if level.difficulty == difficulty]

    def completion_percentage(self) -> float:
        """Calculate the percentage of completed levels."""
        if not self.levels:
            return 0.0

        total_objectives = 0
        completed_objectives = 0

        for level in self.levels:
            total_objectives += len(level.objectives)
            completed_objectives += sum(1 for obj in level.objectives if obj.completed)

        if total_objectives == 0:
            return 0.0

        return (completed_objectives / total_objectives) * 100


class LearningTrackManager:
    """Manages loading and saving of learning tracks and user progress."""

    def __init__(self, tracks_directory: str = None):
        """Initialize the track manager with a directory for track definitions."""
        if tracks_directory is None:
            base_dir = os.path.dirname(os.path.abspath(__file__))
            tracks_directory = os.path.join(base_dir, "tracks")

        self.tracks_directory = tracks_directory
        self.tracks: Dict[str, LearningTrack] = {}

        # Ensure tracks directory exists
        os.makedirs(self.tracks_directory, exist_ok=True)

        logger.info(
            f"Initialized LearningTrackManager with tracks directory: {self.tracks_directory}"
        )

    def load_tracks(self) -> None:
        """Load all track definitions from the tracks directory."""
        track_files = [
            f for f in os.listdir(self.tracks_directory) if f.endswith(".json")
        ]

        for track_file in track_files:
            try:
                with open(os.path.join(self.tracks_directory, track_file), "r") as f:
                    track_data = json.load(f)

                track = self._parse_track_from_json(track_data)
                if track:
                    self.tracks[track.id] = track
                    logger.info(f"Loaded track: {track.name}")
            except Exception as e:
                logger.error(f"Error loading track from {track_file}: {str(e)}")

        logger.info(f"Loaded {len(self.tracks)} learning tracks")

    def _parse_track_from_json(self, track_data: dict) -> Optional[LearningTrack]:
        """Parse a track from JSON data."""
        try:
            # Create the track
            track = LearningTrack(
                id=track_data["id"],
                name=track_data["name"],
                description=track_data["description"],
                track_type=TrackType(track_data["track_type"]),
            )

            # Add levels
            for level_data in track_data.get("levels", []):
                level = LearningLevel(
                    id=level_data["id"],
                    name=level_data["name"],
                    description=level_data["description"],
                    difficulty=DifficultyLevel(level_data["difficulty"]),
                )

                # Add objectives
                for obj_data in level_data.get("objectives", []):
                    objective = LearningObjective(
                        id=obj_data["id"],
                        name=obj_data["name"],
                        description=obj_data["description"],
                        estimated_time_minutes=obj_data["estimated_time_minutes"],
                        prerequisites=obj_data.get("prerequisites", []),
                        resources=obj_data.get("resources", {}),
                    )
                    level.add_objective(objective)

                track.add_level(level)

            return track
        except KeyError as e:
            logger.error(f"Missing required field in track data: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"Error parsing track data: {str(e)}")
            return None

    def get_track(self, track_id: str) -> Optional[LearningTrack]:
        """Get a track by its ID."""
        return self.tracks.get(track_id)

    def get_tracks_by_type(self, track_type: TrackType) -> List[LearningTrack]:
        """Get all tracks of a specific type."""
        return [
            track for track in self.tracks.values() if track.track_type == track_type
        ]

    def save_user_progress(
        self, user_id: str, track_id: str, progress_data: dict
    ) -> bool:
        """Save user progress for a specific track."""
        try:
            progress_dir = os.path.join(self.tracks_directory, "progress")
            os.makedirs(progress_dir, exist_ok=True)

            progress_file = os.path.join(progress_dir, f"{user_id}_{track_id}.json")
            with open(progress_file, "w") as f:
                json.dump(progress_data, f, indent=2)

            logger.info(f"Saved progress for user {user_id} on track {track_id}")
            return True
        except Exception as e:
            logger.error(f"Error saving progress for user {user_id}: {str(e)}")
            return False

    def load_user_progress(self, user_id: str, track_id: str) -> Optional[dict]:
        """Load user progress for a specific track."""
        try:
            progress_file = os.path.join(
                self.tracks_directory, "progress", f"{user_id}_{track_id}.json"
            )

            if not os.path.exists(progress_file):
                logger.info(
                    f"No progress file found for user {user_id} on track {track_id}"
                )
                return None

            with open(progress_file, "r") as f:
                progress_data = json.load(f)

            logger.info(f"Loaded progress for user {user_id} on track {track_id}")
            return progress_data
        except Exception as e:
            logger.error(f"Error loading progress for user {user_id}: {str(e)}")
            return None

    def apply_progress_to_track(
        self, track: LearningTrack, progress_data: dict
    ) -> None:
        """Apply saved progress data to a track."""
        try:
            for level_id, objectives in progress_data.get(
                "completed_objectives", {}
            ).items():
                level = track.get_level(level_id)
                if level:
                    for obj_id in objectives:
                        level.complete_objective(obj_id)

            logger.info(f"Applied progress data to track {track.name}")
        except Exception as e:
            logger.error(f"Error applying progress data: {str(e)}")
