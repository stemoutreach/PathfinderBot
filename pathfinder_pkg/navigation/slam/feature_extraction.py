"""
Feature extraction module for SLAM implementation.

This module provides functionality for extracting features from sensor data
that can be used as landmarks in SLAM algorithms.
"""

import numpy as np
import cv2
from typing import Dict, List, Optional, Tuple, Union
import math

from pathfinder_pkg.utils.logging import get_logger

logger = get_logger(__name__)


class FeatureExtractor:
    """
    Extracts features from sensor data for use in SLAM.

    This class implements methods to extract distinctive features from various
    sensor inputs (camera images, depth maps, LiDAR scans) that can be used
    as landmarks in SLAM algorithms.
    """

    def __init__(
        self,
        max_features: int = 100,
        min_distance: float = 0.5,
        min_distinctiveness: float = 0.1,
    ):
        """
        Initialize the feature extractor.

        Args:
            max_features: Maximum number of features to extract
            min_distance: Minimum distance between features in meters
            min_distinctiveness: Minimum distinctiveness score for features
        """
        self.max_features = max_features
        self.min_distance = min_distance
        self.min_distinctiveness = min_distinctiveness

        # Initialize feature detector and descriptor
        try:
            # Try to use ORB (it's fast and rotation invariant)
            self.feature_detector = cv2.ORB_create(nfeatures=max_features)
        except AttributeError:
            # Fall back to SIFT if ORB is not available
            logger.warning("ORB not available, falling back to SIFT")
            self.feature_detector = cv2.SIFT_create()

        # Initialize feature matcher
        self.matcher = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=True)

        logger.info(f"Initialized feature extractor with max {max_features} features")

    def extract_features_from_image(
        self, image: np.ndarray
    ) -> Tuple[List[cv2.KeyPoint], np.ndarray]:
        """
        Extract features from a camera image.

        Args:
            image: Grayscale or RGB image as a numpy array

        Returns:
            Tuple of (keypoints, descriptors) where keypoints is a list of cv2.KeyPoint
            and descriptors is a numpy array of descriptors
        """
        # Ensure image is grayscale
        if len(image.shape) > 2 and image.shape[2] > 1:
            gray = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)
        else:
            gray = image

        # Detect features
        keypoints, descriptors = self.feature_detector.detectAndCompute(gray, None)

        logger.debug(f"Extracted {len(keypoints)} features from image")

        return keypoints, descriptors

    def extract_corners_from_scan(
        self,
        scan: np.ndarray,
        scan_angles: np.ndarray,
        robot_pose_x: float = 0.0,
        robot_pose_y: float = 0.0,
        robot_pose_theta: float = 0.0,
        min_corner_angle: float = 0.5,
        distance_threshold: float = 0.3,
    ) -> List[Tuple[float, float]]:
        """
        Extract corner features from a laser scan.

        Args:
            scan: Array of range measurements
            scan_angles: Array of corresponding angles
            robot_pose_x: Robot x position in world coordinates
            robot_pose_y: Robot y position in world coordinates
            robot_pose_theta: Robot orientation in world coordinates
            min_corner_angle: Minimum angle (in radians) for corner detection
            distance_threshold: Distance threshold for corner point clustering

        Returns:
            List of (x, y) coordinates of detected corners in world frame
        """
        # Convert scan to Cartesian coordinates (robot frame)
        points = []
        valid_indices = []

        for i, (r, theta) in enumerate(zip(scan, scan_angles)):
            # Skip invalid readings
            if r <= 0 or math.isnan(r) or math.isinf(r):
                continue

            # Convert to Cartesian (robot frame)
            x = r * math.cos(theta)
            y = r * math.sin(theta)

            points.append((x, y))
            valid_indices.append(i)

        if len(points) < 3:
            logger.warning("Not enough valid scan points for corner extraction")
            return []

        # Convert to numpy array for easier processing
        points_array = np.array(points)

        # Find corners using the angle between consecutive points
        corners = []
        for i in range(1, len(points_array) - 1):
            # Get vectors to adjacent points
            v1 = points_array[i - 1] - points_array[i]
            v2 = points_array[i + 1] - points_array[i]

            # Normalize vectors
            v1_norm = np.linalg.norm(v1)
            v2_norm = np.linalg.norm(v2)

            if v1_norm == 0 or v2_norm == 0:
                continue

            v1 = v1 / v1_norm
            v2 = v2 / v2_norm

            # Calculate angle between vectors
            dot_product = np.clip(np.dot(v1, v2), -1.0, 1.0)
            angle = math.acos(dot_product)

            # If angle is significant, this might be a corner
            if angle > min_corner_angle:
                # Get original scan index
                idx = valid_indices[i]

                # Calculate world coordinates
                world_x = (
                    robot_pose_x
                    + points_array[i][0] * math.cos(robot_pose_theta)
                    - points_array[i][1] * math.sin(robot_pose_theta)
                )
                world_y = (
                    robot_pose_y
                    + points_array[i][0] * math.sin(robot_pose_theta)
                    + points_array[i][1] * math.cos(robot_pose_theta)
                )

                corners.append((world_x, world_y))

        # Cluster corners that are close to each other
        clustered_corners = []
        for corner in corners:
            # Check if this corner is close to any existing clustered corner
            is_close = False
            for i, clustered in enumerate(clustered_corners):
                dist = math.sqrt(
                    (corner[0] - clustered[0]) ** 2 + (corner[1] - clustered[1]) ** 2
                )
                if dist < distance_threshold:
                    # Average the positions
                    clustered_corners[i] = (
                        (clustered[0] + corner[0]) / 2,
                        (clustered[1] + corner[1]) / 2,
                    )
                    is_close = True
                    break

            if not is_close:
                clustered_corners.append(corner)

        logger.debug(f"Extracted {len(clustered_corners)} corners from scan")

        return clustered_corners

    def extract_line_segments(
        self,
        scan: np.ndarray,
        scan_angles: np.ndarray,
        robot_pose_x: float = 0.0,
        robot_pose_y: float = 0.0,
        robot_pose_theta: float = 0.0,
        min_points: int = 10,
        distance_threshold: float = 0.05,
    ) -> List[Tuple[Tuple[float, float], Tuple[float, float]]]:
        """
        Extract line segments from a laser scan using RANSAC.

        Args:
            scan: Array of range measurements
            scan_angles: Array of corresponding angles
            robot_pose_x: Robot x position in world coordinates
            robot_pose_y: Robot y position in world coordinates
            robot_pose_theta: Robot orientation in world coordinates
            min_points: Minimum number of points to form a line
            distance_threshold: Maximum distance from a point to a line

        Returns:
            List of ((x1, y1), (x2, y2)) line segments in world coordinates
        """
        # Convert scan to Cartesian coordinates (robot frame)
        points = []

        for r, theta in zip(scan, scan_angles):
            # Skip invalid readings
            if r <= 0 or math.isnan(r) or math.isinf(r):
                continue

            # Convert to Cartesian (robot frame)
            x = r * math.cos(theta)
            y = r * math.sin(theta)

            points.append((x, y))

        if len(points) < min_points:
            logger.warning("Not enough valid scan points for line extraction")
            return []

        # Convert to numpy array for easier processing
        points_array = np.array(points)

        # Find line segments using RANSAC
        remaining_points = points_array.copy()
        line_segments = []

        while len(remaining_points) >= min_points:
            # Use RANSAC to find the best line
            best_line = None
            best_inliers = []
            best_inlier_count = 0

            # Maximum number of RANSAC iterations
            max_iterations = 100

            for _ in range(max_iterations):
                # Randomly select 2 points
                if len(remaining_points) < 2:
                    break

                indices = np.random.choice(len(remaining_points), 2, replace=False)
                p1 = remaining_points[indices[0]]
                p2 = remaining_points[indices[1]]

                # Skip if points are too close
                if np.linalg.norm(p1 - p2) < 0.1:
                    continue

                # Calculate line parameters (ax + by + c = 0)
                a = p2[1] - p1[1]
                b = p1[0] - p2[0]
                c = p2[0] * p1[1] - p1[0] * p2[1]

                # Normalize
                norm = math.sqrt(a * a + b * b)
                if norm == 0:
                    continue

                a /= norm
                b /= norm
                c /= norm

                # Find inliers
                distances = abs(
                    a * remaining_points[:, 0] + b * remaining_points[:, 1] + c
                )
                inliers = np.where(distances < distance_threshold)[0]

                if len(inliers) > best_inlier_count:
                    best_inlier_count = len(inliers)
                    best_inliers = inliers
                    best_line = (a, b, c, p1, p2)

            # If we found a good line
            if best_line is not None and best_inlier_count >= min_points:
                a, b, c, p1, p2 = best_line

                # Get all inlier points
                inlier_points = remaining_points[best_inliers]

                # Project points onto the line to find extremities
                line_dir = p2 - p1
                line_dir = line_dir / np.linalg.norm(line_dir)

                # Project points onto the line
                projections = np.dot(inlier_points - p1, line_dir)
                min_proj = np.min(projections)
                max_proj = np.max(projections)

                # Calculate line extremities
                start_point = p1 + min_proj * line_dir
                end_point = p1 + max_proj * line_dir

                # Transform to world coordinates
                world_start = (
                    robot_pose_x
                    + start_point[0] * math.cos(robot_pose_theta)
                    - start_point[1] * math.sin(robot_pose_theta),
                    robot_pose_y
                    + start_point[0] * math.sin(robot_pose_theta)
                    + start_point[1] * math.cos(robot_pose_theta),
                )

                world_end = (
                    robot_pose_x
                    + end_point[0] * math.cos(robot_pose_theta)
                    - end_point[1] * math.sin(robot_pose_theta),
                    robot_pose_y
                    + end_point[0] * math.sin(robot_pose_theta)
                    + end_point[1] * math.cos(robot_pose_theta),
                )

                line_segments.append((world_start, world_end))

                # Remove inliers from remaining points
                mask = np.ones(len(remaining_points), dtype=bool)
                mask[best_inliers] = False
                remaining_points = remaining_points[mask]
            else:
                # No more good lines to find
                break

        logger.debug(f"Extracted {len(line_segments)} line segments from scan")

        return line_segments

    def match_features(
        self,
        descriptors1: np.ndarray,
        descriptors2: np.ndarray,
        ratio_threshold: float = 0.75,
    ) -> List[Tuple[int, int]]:
        """
        Match feature descriptors using a ratio test.

        Args:
            descriptors1: First set of descriptors
            descriptors2: Second set of descriptors
            ratio_threshold: Threshold for ratio test

        Returns:
            List of (index1, index2) matches
        """
        # Handle empty descriptor sets
        if descriptors1 is None or descriptors2 is None:
            return []

        if len(descriptors1) == 0 or len(descriptors2) == 0:
            return []

        # Convert descriptors to the right type
        descriptors1 = np.uint8(descriptors1)
        descriptors2 = np.uint8(descriptors2)

        # Find matches
        matches = self.matcher.match(descriptors1, descriptors2)

        # Sort by distance
        matches = sorted(matches, key=lambda x: x.distance)

        # Filter using ratio test if we have enough matches
        if len(matches) > 2:
            # Calculate average and std deviation of distances
            distances = np.array([m.distance for m in matches])
            avg_dist = np.mean(distances)
            std_dist = np.std(distances)

            # Keep only matches with distance < avg + threshold * std
            good_matches = [
                m for m in matches if m.distance < avg_dist + ratio_threshold * std_dist
            ]
        else:
            good_matches = matches

        logger.debug(
            f"Matched {len(good_matches)} features out of {len(matches)} candidates"
        )

        # Convert to pairs of indices
        return [(m.queryIdx, m.trainIdx) for m in good_matches]
