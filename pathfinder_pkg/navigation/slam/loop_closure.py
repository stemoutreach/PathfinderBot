"""
Loop closure detection for SLAM.

This module provides functionality for detecting loop closures in SLAM,
which helps to correct accumulated drift in the robot's pose estimation.
"""

import numpy as np
from typing import Dict, List, Optional, Tuple, Union, Any
import math
import cv2
from collections import deque
from dataclasses import dataclass, field
import time

from pathfinder_pkg.utils.logging import get_logger
from pathfinder_pkg.navigation.localization import Pose

logger = get_logger(__name__)


@dataclass
class LoopClosure:
    """Data class representing a detected loop closure."""

    current_index: int  # Index of current pose in pose history
    matched_index: int  # Index of matched pose in pose history
    transform: np.ndarray  # Transformation matrix between poses
    confidence: float  # Confidence score of the loop closure
    timestamp: float = field(default_factory=time.time)  # Time of detection

    def __str__(self) -> str:
        """String representation of the loop closure."""
        return f"LoopClosure(current={self.current_index}, matched={self.matched_index}, confidence={self.confidence:.3f})"


class LoopClosureDetector:
    """
    Detector for identifying loop closures in a robot's trajectory.

    This class implements methods to detect when a robot revisits a previously
    mapped area, which can be used to correct drift in SLAM systems.
    """

    def __init__(
        self,
        distance_threshold: float = 0.5,
        angle_threshold: float = 0.3,
        similarity_threshold: float = 0.75,
        min_loop_separation: int = 50,
    ):
        """
        Initialize the loop closure detector.

        Args:
            distance_threshold: Maximum distance between poses for potential loop closure (meters)
            angle_threshold: Maximum angle difference between poses for potential loop closure (radians)
            similarity_threshold: Minimum similarity score for confirming a loop closure
            min_loop_separation: Minimum number of poses between loop closure candidates
        """
        self.distance_threshold = distance_threshold
        self.angle_threshold = angle_threshold
        self.similarity_threshold = similarity_threshold
        self.min_loop_separation = min_loop_separation

        # Store history of detected features for loop closure
        self.descriptor_history: List[np.ndarray] = []
        self.pose_history: List[Pose] = []
        self.image_history: List[np.ndarray] = []

        # Store detected loop closures
        self.detected_closures: List[LoopClosure] = []

        # Feature detector for loop closure
        try:
            # Try to use ORB (it's fast and rotation invariant)
            self.feature_detector = cv2.ORB_create(nfeatures=500)
            self.matcher = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=True)
        except AttributeError:
            # Fall back to SIFT if ORB is not available
            logger.warning("ORB not available, falling back to SIFT for loop closure")
            self.feature_detector = cv2.SIFT_create()
            self.matcher = cv2.BFMatcher(cv2.NORM_L2, crossCheck=True)

        logger.info("Initialized loop closure detector")

    def add_keyframe(self, pose: Pose, image: Optional[np.ndarray] = None) -> None:
        """
        Add a keyframe to the history for loop closure detection.

        Args:
            pose: Robot pose at the keyframe
            image: Camera image at the keyframe (if available)
        """
        self.pose_history.append(pose)

        if image is not None:
            # Convert to grayscale if needed
            if len(image.shape) > 2 and image.shape[2] > 1:
                gray = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)
            else:
                gray = image.copy()

            # Store image
            self.image_history.append(gray)

            # Extract and store features
            kp, desc = self.feature_detector.detectAndCompute(gray, None)
            if desc is not None:
                self.descriptor_history.append(desc)
            else:
                # If no features detected, use empty descriptor
                self.descriptor_history.append(np.array([]))

            logger.debug(f"Added keyframe with {len(kp) if kp else 0} features")
        else:
            # If no image is provided, use empty descriptor
            self.descriptor_history.append(np.array([]))

    def detect_loop_closure(
        self,
        current_pose: Pose,
        current_image: Optional[np.ndarray] = None,
        max_candidates: int = 5,
    ) -> Optional[LoopClosure]:
        """
        Check for loop closures with the current pose and image.

        Args:
            current_pose: Current robot pose
            current_image: Current camera image (if available)
            max_candidates: Maximum number of candidates to check

        Returns:
            Detected loop closure or None if no loop closure found
        """
        # If we don't have enough history, return None
        if len(self.pose_history) < self.min_loop_separation + 1:
            return None

        # Find pose candidates based on position
        candidates = self._find_pose_candidates(current_pose, max_candidates)

        # If no candidates or no image, return None
        if not candidates or current_image is None:
            return None

        # Convert current image to grayscale if needed
        if len(current_image.shape) > 2 and current_image.shape[2] > 1:
            current_gray = cv2.cvtColor(current_image, cv2.COLOR_RGB2GRAY)
        else:
            current_gray = current_image.copy()

        # Extract features from current image
        current_kp, current_desc = self.feature_detector.detectAndCompute(
            current_gray, None
        )

        if current_desc is None or len(current_kp) < 10:
            logger.debug(
                f"Not enough features in current image: {len(current_kp) if current_kp else 0}"
            )
            return None

        # Check each candidate for feature matches
        best_loop_closure = None
        best_confidence = 0.0

        for candidate_idx, _ in candidates:
            # Skip if we don't have descriptors for this candidate
            if (
                candidate_idx >= len(self.descriptor_history)
                or len(self.descriptor_history[candidate_idx]) == 0
            ):
                continue

            candidate_desc = self.descriptor_history[candidate_idx]

            # Try to match features
            try:
                matches = self.matcher.match(current_desc, candidate_desc)

                # Filter and sort matches by distance
                matches = sorted(matches, key=lambda x: x.distance)

                # Calculate confidence score based on matches
                if len(matches) >= 20:
                    # Get matched keypoints
                    current_pts = np.float32(
                        [current_kp[m.queryIdx].pt for m in matches[:20]]
                    )
                    candidate_pts = np.float32(
                        [self.image_history[candidate_idx].shape for m in matches[:20]]
                    )

                    # Compute homography matrix
                    H, mask = cv2.findHomography(
                        current_pts, candidate_pts, cv2.RANSAC, 5.0
                    )

                    if H is not None:
                        # Calculate confidence based on inliers
                        num_inliers = np.sum(mask)
                        confidence = num_inliers / len(matches[:20])

                        # Check if this is better than previous candidates
                        if (
                            confidence > best_confidence
                            and confidence > self.similarity_threshold
                        ):
                            best_confidence = confidence

                            # Create transformation matrix
                            transform = np.eye(3)
                            # In a real implementation, we'd compute the actual transformation
                            # between poses, but for simplicity we're just using identity

                            best_loop_closure = LoopClosure(
                                current_index=len(self.pose_history),
                                matched_index=candidate_idx,
                                transform=transform,
                                confidence=confidence,
                            )

                            logger.debug(
                                f"Potential loop closure with idx {candidate_idx}, confidence {confidence:.3f}"
                            )
            except Exception as e:
                logger.warning(f"Error matching features: {e}")
                continue

        # If we found a good loop closure, add it to detected closures
        if best_loop_closure and best_confidence > self.similarity_threshold:
            self.detected_closures.append(best_loop_closure)
            logger.info(f"Detected loop closure: {best_loop_closure}")
            return best_loop_closure

        return None

    def _find_pose_candidates(
        self, current_pose: Pose, max_candidates: int
    ) -> List[Tuple[int, float]]:
        """
        Find candidate poses for loop closure based on position.

        Args:
            current_pose: Current robot pose
            max_candidates: Maximum number of candidates to return

        Returns:
            List of (index, distance) tuples for candidate poses
        """
        candidates = []

        # Skip recent poses (defined by min_loop_separation)
        search_history = (
            self.pose_history[: -self.min_loop_separation]
            if len(self.pose_history) > self.min_loop_separation
            else []
        )

        # No candidates if search history is empty
        if not search_history:
            return []

        # Check each pose in history
        for i, pose in enumerate(search_history):
            # Calculate distance between poses
            distance = math.sqrt(
                (current_pose.x - pose.x) ** 2 + (current_pose.y - pose.y) ** 2
            )

            # Calculate angle difference (normalized to [-π, π])
            angle_diff = abs(
                (current_pose.theta - pose.theta + math.pi) % (2 * math.pi) - math.pi
            )

            # If within thresholds, add to candidates
            if distance < self.distance_threshold and angle_diff < self.angle_threshold:
                candidates.append((i, distance))

        # Sort by distance and take top candidates
        candidates.sort(key=lambda x: x[1])
        return candidates[:max_candidates]

    def get_loop_closures(self) -> List[LoopClosure]:
        """
        Get all detected loop closures.

        Returns:
            List of detected loop closures
        """
        return self.detected_closures.copy()

    def get_recent_loop_closures(self, count: int = 5) -> List[LoopClosure]:
        """
        Get the most recent loop closures.

        Args:
            count: Maximum number of loop closures to return

        Returns:
            List of most recent loop closures
        """
        return self.detected_closures[-count:] if self.detected_closures else []

    def clear_history(self) -> None:
        """Clear the detector's history."""
        self.descriptor_history = []
        self.pose_history = []
        self.image_history = []
        logger.info("Cleared loop closure detector history")
