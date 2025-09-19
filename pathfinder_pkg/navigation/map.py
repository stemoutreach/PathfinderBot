"""
Map representation module for PathfinderBot navigation.

This module provides classes for representing and managing maps,
including occupancy grid maps and landmark maps.
"""

import numpy as np
import json
import os
from typing import List, Tuple, Dict, Optional, Union
import matplotlib.pyplot as plt
from pathlib import Path

from pathfinder_pkg.utils.logging import get_logger

logger = get_logger(__name__)


class OccupancyGridMap:
    """
    Occupancy grid map representation for robot navigation.

    The occupancy grid represents the environment as a grid where each cell
    contains a probability of occupancy (0 = free, 1 = occupied, 0.5 = unknown).
    """

    def __init__(
        self,
        width: int = 100,
        height: int = 100,
        resolution: float = 0.1,
        origin_x: float = 0.0,
        origin_y: float = 0.0,
    ):
        """
        Initialize a new occupancy grid map.

        Args:
            width: Width of the map in cells
            height: Height of the map in cells
            resolution: Resolution of the map in meters/cell
            origin_x: X coordinate of the map origin in world coordinates
            origin_y: Y coordinate of the map origin in world coordinates
        """
        self.width = width
        self.height = height
        self.resolution = resolution
        self.origin_x = origin_x
        self.origin_y = origin_y

        # Initialize grid with all cells as unknown (0.5)
        self.grid = np.ones((height, width)) * 0.5

        # Map metadata
        self.metadata = {
            "created": None,
            "last_updated": None,
            "name": "New Map",
            "description": "",
            "landmarks": {},
        }

        logger.info(
            f"Created occupancy grid map of size {width}x{height} with resolution {resolution}m/cell"
        )

    def update_cell(self, x: int, y: int, value: float) -> bool:
        """
        Update the occupancy probability of a cell.

        Args:
            x: Cell x coordinate (grid coordinates)
            y: Cell y coordinate (grid coordinates)
            value: New occupancy probability (0 to 1)

        Returns:
            True if the update was successful, False otherwise
        """
        if 0 <= x < self.width and 0 <= y < self.height:
            self.grid[y, x] = max(0.0, min(1.0, value))  # Clamp to [0, 1]
            return True
        else:
            logger.warning(
                f"Cell coordinates ({x}, {y}) out of bounds for map of size {self.width}x{self.height}"
            )
            return False

    def get_cell(self, x: int, y: int) -> Optional[float]:
        """
        Get the occupancy probability of a cell.

        Args:
            x: Cell x coordinate (grid coordinates)
            y: Cell y coordinate (grid coordinates)

        Returns:
            The occupancy probability (0 to 1) or None if out of bounds
        """
        if 0 <= x < self.width and 0 <= y < self.height:
            return float(self.grid[y, x])
        return None

    def update_cells_in_radius(
        self, center_x: int, center_y: int, radius: int, value: float
    ) -> int:
        """
        Update all cells within a radius from the center point.

        Args:
            center_x: Center x coordinate (grid coordinates)
            center_y: Center y coordinate (grid coordinates)
            radius: Radius in cells
            value: New occupancy probability (0 to 1)

        Returns:
            Number of cells updated
        """
        cells_updated = 0
        for y in range(
            max(0, center_y - radius), min(self.height, center_y + radius + 1)
        ):
            for x in range(
                max(0, center_x - radius), min(self.width, center_x + radius + 1)
            ):
                if (x - center_x) ** 2 + (y - center_y) ** 2 <= radius**2:
                    self.grid[y, x] = max(0.0, min(1.0, value))
                    cells_updated += 1
        return cells_updated

    def world_to_grid(self, world_x: float, world_y: float) -> Tuple[int, int]:
        """
        Convert world coordinates to grid coordinates.

        Args:
            world_x: X coordinate in world frame (meters)
            world_y: Y coordinate in world frame (meters)

        Returns:
            Tuple of (grid_x, grid_y) coordinates
        """
        grid_x = int((world_x - self.origin_x) / self.resolution)
        grid_y = int((world_y - self.origin_y) / self.resolution)
        return grid_x, grid_y

    def grid_to_world(self, grid_x: int, grid_y: int) -> Tuple[float, float]:
        """
        Convert grid coordinates to world coordinates.

        Args:
            grid_x: X coordinate in grid cells
            grid_y: Y coordinate in grid cells

        Returns:
            Tuple of (world_x, world_y) coordinates in meters
        """
        world_x = grid_x * self.resolution + self.origin_x
        world_y = grid_y * self.resolution + self.origin_y
        return world_x, world_y

    def is_occupied(self, x: int, y: int, threshold: float = 0.65) -> bool:
        """
        Check if a cell is considered occupied.

        Args:
            x: Cell x coordinate (grid coordinates)
            y: Cell y coordinate (grid coordinates)
            threshold: Occupancy threshold (default: 0.65)

        Returns:
            True if the cell is occupied, False otherwise
        """
        value = self.get_cell(x, y)
        return value is not None and value >= threshold

    def is_free(self, x: int, y: int, threshold: float = 0.35) -> bool:
        """
        Check if a cell is considered free.

        Args:
            x: Cell x coordinate (grid coordinates)
            y: Cell y coordinate (grid coordinates)
            threshold: Free threshold (default: 0.35)

        Returns:
            True if the cell is free, False otherwise
        """
        value = self.get_cell(x, y)
        return value is not None and value <= threshold

    def is_unknown(self, x: int, y: int, epsilon: float = 0.1) -> bool:
        """
        Check if a cell is considered unknown.

        Args:
            x: Cell x coordinate (grid coordinates)
            y: Cell y coordinate (grid coordinates)
            epsilon: Epsilon around 0.5 to consider unknown (default: 0.1)

        Returns:
            True if the cell is unknown, False otherwise
        """
        value = self.get_cell(x, y)
        return value is not None and 0.5 - epsilon <= value <= 0.5 + epsilon

    def add_landmark(
        self, name: str, x: float, y: float, description: str = ""
    ) -> None:
        """
        Add a landmark to the map.

        Args:
            name: Landmark name
            x: X coordinate in world frame (meters)
            y: Y coordinate in world frame (meters)
            description: Optional description
        """
        self.metadata["landmarks"][name] = {"x": x, "y": y, "description": description}
        logger.info(f"Added landmark '{name}' at position ({x}, {y})")

    def save(self, filepath: Union[str, Path]) -> bool:
        """
        Save the map to a file.

        Args:
            filepath: Path to save the map

        Returns:
            True if the save was successful, False otherwise
        """
        try:
            # Create directory if it doesn't exist
            path = Path(filepath)
            path.parent.mkdir(parents=True, exist_ok=True)

            # Save as NPZ file with metadata
            np.savez_compressed(
                filepath,
                grid=self.grid,
                width=self.width,
                height=self.height,
                resolution=self.resolution,
                origin_x=self.origin_x,
                origin_y=self.origin_y,
                metadata=json.dumps(self.metadata),
            )

            logger.info(f"Map saved to {filepath}")
            return True
        except Exception as e:
            logger.error(f"Error saving map to {filepath}: {e}")
            return False

    @classmethod
    def load(cls, filepath: Union[str, Path]) -> "OccupancyGridMap":
        """
        Load a map from a file.

        Args:
            filepath: Path to the map file

        Returns:
            Loaded OccupancyGridMap
        """
        try:
            data = np.load(filepath, allow_pickle=True)

            # Create a new map with the loaded parameters
            map_obj = cls(
                width=int(data["width"]),
                height=int(data["height"]),
                resolution=float(data["resolution"]),
                origin_x=float(data["origin_x"]),
                origin_y=float(data["origin_y"]),
            )

            # Load grid data
            map_obj.grid = data["grid"]

            # Load metadata
            if "metadata" in data:
                map_obj.metadata = json.loads(str(data["metadata"]))

            logger.info(f"Map loaded from {filepath}")
            return map_obj
        except Exception as e:
            logger.error(f"Error loading map from {filepath}: {e}")
            # Return an empty map
            return cls()

    def visualize(self, ax=None, show: bool = True):
        """
        Visualize the occupancy grid map.

        Args:
            ax: Matplotlib axes to plot on
            show: Whether to show the plot

        Returns:
            Matplotlib axes object
        """
        if ax is None:
            fig, ax = plt.subplots(figsize=(10, 8))

        # Plot the occupancy grid
        cmap = plt.cm.gray_r  # Reversed grayscale (white=free, black=occupied)
        img = ax.imshow(
            self.grid,
            cmap=cmap,
            origin="lower",
            extent=[
                self.origin_x,
                self.origin_x + self.width * self.resolution,
                self.origin_y,
                self.origin_y + self.height * self.resolution,
            ],
        )

        # Add colorbar
        plt.colorbar(img, ax=ax, label="Occupancy Probability")

        # Plot landmarks
        for name, landmark in self.metadata["landmarks"].items():
            ax.plot(landmark["x"], landmark["y"], "ro", markersize=5)
            ax.annotate(
                name,
                (landmark["x"], landmark["y"]),
                fontsize=8,
                xytext=(5, 5),
                textcoords="offset points",
            )

        # Set labels and title
        ax.set_xlabel("X (meters)")
        ax.set_ylabel("Y (meters)")
        ax.set_title(f"Occupancy Grid Map: {self.metadata['name']}")

        if show:
            plt.tight_layout()
            plt.show()

        return ax
