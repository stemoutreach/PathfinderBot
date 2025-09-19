"""
Block detector implementation for PathfinderBot.

This module provides enhanced block detection capabilities with improved
color segmentation, shape analysis, and tracking for robot manipulation.
"""

import cv2
import numpy as np
from pathfinder_pkg.utils.logging import get_logger
from .base import Detector

logger = get_logger(__name__)


class BlockDetector(Detector):
    """
    Enhanced block detector with advanced color segmentation and shape analysis.

    This detector can identify colored blocks in an image, classify them by color,
    and provide detailed information about their position, size, and orientation.

    Attributes:
        name (str): The name of the detector ("block").
        hsv_ranges (dict): HSV color ranges for different block colors.
        min_area (int): Minimum pixel area for a block to be considered valid.
        rect_min_fill (float): Minimum ratio of contour area to bounding box area.
        blur_kernel_size (int): Kernel size for Gaussian blur preprocessing.
        history (list): History of recent detections for tracking.
        max_history_size (int): Maximum number of frames to keep in history.
    """

    name = "block"

    def __init__(
        self,
        hsv_ranges=None,
        min_area=1000,
        rect_min_fill=0.6,
        blur_kernel_size=5,
        max_history_size=10,
    ):
        """
        Initialize the block detector with custom parameters.

        Args:
            hsv_ranges (dict, optional): HSV color ranges for different colors.
                Format: {'color_name': [(lower1, upper1), (lower2, upper2), ...]}
            min_area (int, optional): Minimum pixel area for a valid block.
            rect_min_fill (float, optional): Minimum contour/bbox area ratio.
            blur_kernel_size (int, optional): Size of Gaussian blur kernel.
            max_history_size (int, optional): Number of frames to keep in history.
        """
        super().__init__()

        # Default HSV color ranges if none provided
        self.hsv_ranges = hsv_ranges or {
            "red": [((0, 120, 70), (10, 255, 255)), ((170, 120, 70), (180, 255, 255))],
            "green": [((35, 100, 70), (85, 255, 255))],
            "blue": [((90, 100, 70), (130, 255, 255))],
            "yellow": [((18, 120, 120), (35, 255, 255))],
        }

        self.min_area = int(min_area)
        self.rect_min_fill = float(rect_min_fill)
        self.blur_kernel_size = blur_kernel_size
        self.history = []
        self.max_history_size = max_history_size

        logger.info(
            f"BlockDetector initialized with {len(self.hsv_ranges)} color ranges"
        )

    def infer(self, frame_bgr):
        """
        Detect blocks in the provided BGR frame.

        Args:
            frame_bgr (numpy.ndarray): BGR format image frame.

        Returns:
            dict: Detection results with block information.
                Format:
                {
                    "type": "block",
                    "items": [
                        {
                            "id": unique_id,
                            "label": "block",
                            "color": color_name,
                            "box": [x1, y1, x2, y2],
                            "center": [cx, cy],
                            "area": contour_area,
                            "fill": contour_area / bbox_area,
                            "corners": number_of_corners,
                            "rotation": estimated_rotation_angle,
                            "confidence": detection_confidence
                        },
                        ...
                    ],
                    "debug": {
                        "count": total_number_of_blocks_detected,
                        "masked_areas": areas_covered_by_color_masks,
                        "processing_time_ms": processing_time_in_milliseconds
                    }
                }
        """
        start_time = cv2.getTickCount()

        # Pre-process the frame
        blurred = cv2.GaussianBlur(
            frame_bgr, (self.blur_kernel_size, self.blur_kernel_size), 0
        )
        hsv = cv2.cvtColor(blurred, cv2.COLOR_BGR2HSV)

        # Process each color
        results = []
        masked_areas = {}
        color_masks = {}

        for color, ranges in self.hsv_ranges.items():
            # Create mask for this color by combining all ranges
            color_mask = None
            for lower, upper in ranges:
                lower_bound = np.array(lower, dtype=np.uint8)
                upper_bound = np.array(upper, dtype=np.uint8)
                mask = cv2.inRange(hsv, lower_bound, upper_bound)

                if color_mask is None:
                    color_mask = mask
                else:
                    color_mask = cv2.bitwise_or(color_mask, mask)

            if color_mask is None:
                continue

            # Store mask for debug
            color_masks[color] = color_mask

            # Apply morphological operations to clean up the mask
            kernel3 = np.ones((3, 3), np.uint8)
            kernel5 = np.ones((5, 5), np.uint8)

            # Remove small noise
            color_mask = cv2.morphologyEx(
                color_mask, cv2.MORPH_OPEN, kernel3, iterations=1
            )

            # Close holes in the mask
            color_mask = cv2.morphologyEx(
                color_mask, cv2.MORPH_CLOSE, kernel5, iterations=2
            )

            # Find contours in the mask
            contours, _ = cv2.findContours(
                color_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
            )

            masked_areas[color] = cv2.countNonZero(color_mask)

            # Process each contour
            for i, contour in enumerate(contours):
                area = cv2.contourArea(contour)

                # Skip if too small
                if area < self.min_area:
                    continue

                # Get bounding box
                x, y, w, h = cv2.boundingRect(contour)

                # Calculate fill ratio
                rect_area = w * h if w > 0 and h > 0 else 1
                fill_ratio = area / rect_area

                # Skip if fill ratio is too low (likely not a block)
                if fill_ratio < self.rect_min_fill:
                    continue

                # Calculate centroid
                M = cv2.moments(contour)
                if M["m00"] > 0:
                    cx = int(M["m10"] / M["m00"])
                    cy = int(M["m01"] / M["m00"])
                else:
                    cx, cy = x + w // 2, y + h // 2

                # Estimate corner count using approxPolyDP
                epsilon = 0.04 * cv2.arcLength(contour, True)
                approx = cv2.approxPolyDP(contour, epsilon, True)
                corners = len(approx)

                # Skip if not likely a block (too few or too many corners)
                if corners < 4:
                    continue

                # Estimate rotation angle for rectangular blocks
                if corners <= 6:  # Likely a rectangle or close to it
                    # Find the minimum area rectangle
                    rect = cv2.minAreaRect(contour)
                    box = cv2.boxPoints(rect)
                    box = np.intp(box)

                    # Extract angle from the rect
                    _, _, rotation = rect

                    # Adjust angle to be between 0 and 90 degrees
                    if rotation < -45:
                        rotation += 90

                    # Make angle positive
                    rotation = abs(rotation)
                else:
                    # For non-rectangular shapes, set rotation to 0
                    rotation = 0

                # Calculate detection confidence based on fill ratio and area
                confidence = min(1.0, (fill_ratio - self.rect_min_fill) * 10) * min(
                    1.0, area / (self.min_area * 5)
                )

                # Create result entry
                block_info = {
                    "id": f"{color}_{i}",
                    "label": "block",
                    "color": color,
                    "box": [int(x), int(y), int(x + w), int(y + h)],
                    "center": [int(cx), int(cy)],
                    "area": int(area),
                    "fill": float(fill_ratio),
                    "corners": int(corners),
                    "rotation": float(rotation),
                    "confidence": float(confidence),
                }

                results.append(block_info)

        # Sort results by area (largest first)
        results.sort(key=lambda r: r["area"], reverse=True)

        # Update history for tracking
        self.update_history(results)

        # Calculate processing time
        processing_time = (
            (cv2.getTickCount() - start_time) / cv2.getTickFrequency() * 1000
        )

        return {
            "type": self.name,
            "items": results,
            "debug": {
                "count": len(results),
                "masked_areas": masked_areas,
                "processing_time_ms": processing_time,
            },
        }

    def update_history(self, current_results):
        """
        Update detection history for tracking blocks across frames.

        Args:
            current_results (list): List of blocks detected in current frame.
        """
        # Add current results to history
        self.history.append(current_results)

        # Trim history if it gets too long
        if len(self.history) > self.max_history_size:
            self.history.pop(0)

    def get_block_trajectory(self, block_id, frames=5):
        """
        Get trajectory of a specific block over recent frames.

        Args:
            block_id (str): ID of the block to track.
            frames (int, optional): Number of recent frames to consider.

        Returns:
            list: List of (x, y) center positions for the block.
        """
        positions = []

        # Look through available history (up to requested frames)
        frames = min(frames, len(self.history))

        for frame_idx in range(-frames, 0):
            frame_results = self.history[frame_idx]

            # Find the block in this frame
            for block in frame_results:
                if block.get("id") == block_id:
                    positions.append(tuple(block["center"]))
                    break
            else:
                # Block not found in this frame
                positions.append(None)

        return positions


class EnhancedBlockDetector(BlockDetector):
    """
    Enhanced block detector with advanced tracking and manipulation assistance.

    This detector extends the basic BlockDetector with features to help with
    robot manipulation, such as block pickup feedback and position prediction.
    """

    def __init__(self, **kwargs):
        """
        Initialize the enhanced block detector.

        Args:
            **kwargs: Arguments to pass to the parent BlockDetector.
        """
        super().__init__(**kwargs)
        self.target_block = None

    def set_target_block(self, block_id):
        """
        Set a specific block as the target for manipulation.

        Args:
            block_id (str): ID of the block to target.

        Returns:
            bool: True if the block was found and set as target, False otherwise.
        """
        if not self.history:
            logger.warning("No detection history available to set target block")
            return False

        # Look for block in most recent frame
        latest_frame = self.history[-1]
        for block in latest_frame:
            if block.get("id") == block_id:
                self.target_block = block_id
                logger.info(f"Target block set: {block_id}")
                return True

        logger.warning(f"Block {block_id} not found in current frame")
        return False

    def get_target_block_info(self):
        """
        Get the latest information about the target block.

        Returns:
            dict: Block information, or None if no target or target not visible.
        """
        if not self.target_block or not self.history:
            return None

        # Look for target block in most recent frame
        latest_frame = self.history[-1]
        for block in latest_frame:
            if block.get("id") == self.target_block:
                return block

        return None

    def get_pickup_feedback(self, gripper_position):
        """
        Get feedback for block pickup based on gripper position.

        Args:
            gripper_position (tuple): (x, y) position of the gripper in the image.

        Returns:
            dict: Feedback information for gripper alignment:
                {
                    "aligned": bool,
                    "distance": float,
                    "direction": (dx, dy),
                    "block": block_info or None
                }
        """
        # Get target block info
        block = self.get_target_block_info()
        if not block:
            return {
                "aligned": False,
                "distance": float("inf"),
                "direction": (0, 0),
                "block": None,
            }

        # Calculate distance between gripper and block center
        gx, gy = gripper_position
        cx, cy = block["center"]
        dx, dy = cx - gx, cy - gy
        distance = np.sqrt(dx * dx + dy * dy)

        # Determine if gripper is aligned with block
        # (within 10% of block width/height)
        x, y, x2, y2 = block["box"]
        width, height = x2 - x, y2 - y
        alignment_threshold = min(width, height) * 0.1
        aligned = distance < alignment_threshold

        return {
            "aligned": aligned,
            "distance": float(distance),
            "direction": (float(dx), float(dy)),
            "block": block,
        }

    def predict_block_position(self, block_id, frames_ahead=1):
        """
        Predict the future position of a block based on its recent trajectory.

        Args:
            block_id (str): ID of the block to predict.
            frames_ahead (int, optional): How many frames ahead to predict.

        Returns:
            tuple: Predicted (x, y) position, or None if prediction isn't possible.
        """
        # Get recent positions
        positions = self.get_block_trajectory(block_id, frames=5)

        # Need at least 2 valid positions to predict
        valid_positions = [p for p in positions if p is not None]
        if len(valid_positions) < 2:
            return None

        # For simple prediction, use linear extrapolation from last two points
        if len(valid_positions) >= 2:
            p1 = np.array(valid_positions[-2])
            p2 = np.array(valid_positions[-1])
            velocity = p2 - p1

            # Predict future position
            predicted = p2 + velocity * frames_ahead

            return (int(predicted[0]), int(predicted[1]))

        return None
