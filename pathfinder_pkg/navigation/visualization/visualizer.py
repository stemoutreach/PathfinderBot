"""
Visualization module for PathfinderBot navigation.

This module provides tools for visualizing the robot's environment, path,
and navigation data to help with debugging and user interfaces.
"""

import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.figure import Figure
from matplotlib.axes import Axes
from typing import List, Tuple, Dict, Optional, Union, Any, Callable
import threading
import time
import math
import io
from PIL import Image

from pathfinder_pkg.utils.logging import get_logger
from pathfinder_pkg.navigation.map import OccupancyGridMap
from pathfinder_pkg.navigation.localization import Pose
from pathfinder_pkg.navigation.slam.slam import SLAM
from pathfinder_pkg.navigation.path_planning.planner import Waypoint
from pathfinder_pkg.navigation.behaviors.navigator import NavigationController

logger = get_logger(__name__)


class MapVisualizer:
    """
    Visualizer for occupancy grid maps.

    This class provides methods for visualizing occupancy grid maps, robot poses,
    paths, and other navigation data.
    """

    def __init__(
        self,
        width: int = 6,
        height: int = 6,
        dpi: int = 100,
        cmap: str = "gray",
        bg_color: str = "white",
    ):
        """
        Initialize the map visualizer.

        Args:
            width: Width of the figure in inches
            height: Height of the figure in inches
            dpi: Dots per inch (resolution)
            cmap: Colormap for the occupancy grid
            bg_color: Background color
        """
        self.width = width
        self.height = height
        self.dpi = dpi
        self.cmap = cmap
        self.bg_color = bg_color

        # Create figure and axes
        self.fig, self.ax = plt.subplots(figsize=(width, height), dpi=dpi)
        self.fig.patch.set_facecolor(bg_color)

        # Lock for thread safety
        self.lock = threading.RLock()

        logger.info("Map visualizer initialized")

    def visualize_map(
        self,
        grid_map: OccupancyGridMap,
        show_grid: bool = True,
        show_axes: bool = True,
        title: Optional[str] = None,
    ) -> Tuple[Figure, Axes]:
        """
        Visualize an occupancy grid map.

        Args:
            grid_map: Occupancy grid map to visualize
            show_grid: Whether to show grid lines
            show_axes: Whether to show axes
            title: Title of the plot

        Returns:
            The figure and axes objects
        """
        with self.lock:
            # Clear previous plot
            self.ax.clear()

            # Get map data
            grid_data = grid_map.get_grid()

            # Create image
            img = self.ax.imshow(
                grid_data,
                cmap=self.cmap,
                origin="lower",
                extent=[
                    grid_map.origin_x,
                    grid_map.origin_x + grid_map.width * grid_map.resolution,
                    grid_map.origin_y,
                    grid_map.origin_y + grid_map.height * grid_map.resolution,
                ],
                vmin=0,
                vmax=1,
            )

            # Set title
            if title:
                self.ax.set_title(title)
            else:
                self.ax.set_title("Occupancy Grid Map")

            # Set axes
            self.ax.set_xlabel("X (m)")
            self.ax.set_ylabel("Y (m)")

            # Show/hide grid and axes
            self.ax.grid(show_grid)
            if not show_axes:
                self.ax.set_axis_off()

            # Add colorbar
            self.fig.colorbar(img, ax=self.ax, label="Occupancy Probability")

            return self.fig, self.ax

    def plot_pose(
        self,
        pose: Pose,
        color: str = "red",
        arrow_length: float = 0.3,
        marker_size: int = 8,
        label: Optional[str] = None,
    ) -> None:
        """
        Plot a robot pose on the current map.

        Args:
            pose: Robot pose to plot
            color: Color of the pose marker and arrow
            arrow_length: Length of the orientation arrow
            marker_size: Size of the pose marker
            label: Label for the pose in the legend
        """
        with self.lock:
            # Plot position
            self.ax.plot(
                pose.x, pose.y, "o", color=color, markersize=marker_size, label=label
            )

            # Plot orientation arrow
            dx = arrow_length * math.cos(pose.theta)
            dy = arrow_length * math.sin(pose.theta)
            self.ax.arrow(
                pose.x,
                pose.y,
                dx,
                dy,
                head_width=0.1,
                head_length=0.15,
                fc=color,
                ec=color,
            )

    def plot_path(
        self,
        waypoints: List[Waypoint],
        color: str = "blue",
        line_width: float = 2,
        marker_size: int = 6,
        label: Optional[str] = None,
        show_orientations: bool = False,
        orientation_length: float = 0.2,
    ) -> None:
        """
        Plot a path on the current map.

        Args:
            waypoints: List of waypoints defining the path
            color: Color of the path
            line_width: Width of the path line
            marker_size: Size of the waypoint markers
            label: Label for the path in the legend
            show_orientations: Whether to show orientation arrows for waypoints
            orientation_length: Length of the orientation arrows
        """
        with self.lock:
            if not waypoints:
                return

            # Extract waypoint positions
            x_coords = [wp.x for wp in waypoints]
            y_coords = [wp.y for wp in waypoints]

            # Plot path line
            self.ax.plot(
                x_coords, y_coords, "-", color=color, linewidth=line_width, label=label
            )

            # Plot waypoints
            self.ax.plot(x_coords, y_coords, "o", color=color, markersize=marker_size)

            # Plot start and goal points with different markers
            if waypoints[0].action == "start":
                self.ax.plot(
                    waypoints[0].x,
                    waypoints[0].y,
                    "D",
                    color="green",
                    markersize=marker_size + 2,
                )
            if waypoints[-1].action == "goal":
                self.ax.plot(
                    waypoints[-1].x,
                    waypoints[-1].y,
                    "*",
                    color="green",
                    markersize=marker_size + 2,
                )

            # Plot orientations if requested
            if show_orientations:
                for wp in waypoints:
                    if wp.theta is not None:
                        dx = orientation_length * math.cos(wp.theta)
                        dy = orientation_length * math.sin(wp.theta)
                        self.ax.arrow(
                            wp.x,
                            wp.y,
                            dx,
                            dy,
                            head_width=0.05,
                            head_length=0.1,
                            fc=color,
                            ec=color,
                            alpha=0.6,
                        )

    def plot_particles(
        self,
        particles: np.ndarray,
        weights: Optional[np.ndarray] = None,
        color: str = "blue",
        alpha: float = 0.5,
        size_range: Tuple[float, float] = (1.0, 8.0),
    ) -> None:
        """
        Plot particles from a particle filter on the current map.

        Args:
            particles: Particle positions and orientations as Nx3 array (x,y,theta)
            weights: Particle weights (optional)
            color: Color of the particles
            alpha: Transparency of the particles
            size_range: Range of marker sizes (min, max) based on weights
        """
        with self.lock:
            if particles.shape[1] < 2:
                logger.warning("Particles must have at least x,y coordinates")
                return

            # Extract positions
            x_coords = particles[:, 0]
            y_coords = particles[:, 1]

            # Calculate marker sizes based on weights if provided
            if weights is not None:
                # Normalize weights to [0, 1]
                normalized_weights = (
                    weights / np.max(weights)
                    if np.max(weights) > 0
                    else np.ones_like(weights)
                )

                # Scale to marker sizes
                sizes = size_range[0] + normalized_weights * (
                    size_range[1] - size_range[0]
                )

                # Plot particles with varying sizes
                scatter = self.ax.scatter(
                    x_coords, y_coords, s=sizes, color=color, alpha=alpha, marker="o"
                )
            else:
                # Plot particles with uniform size
                scatter = self.ax.scatter(
                    x_coords,
                    y_coords,
                    s=size_range[0],
                    color=color,
                    alpha=alpha,
                    marker="o",
                )

            # Plot orientations if available (theta is the third column)
            if particles.shape[1] > 2:
                # Sample a subset of particles if there are too many
                max_arrows = 100
                indices = np.linspace(
                    0, len(particles) - 1, min(max_arrows, len(particles))
                ).astype(int)

                for i in indices:
                    theta = particles[i, 2]
                    dx = 0.1 * math.cos(theta)
                    dy = 0.1 * math.sin(theta)
                    self.ax.arrow(
                        x_coords[i],
                        y_coords[i],
                        dx,
                        dy,
                        head_width=0.02,
                        head_length=0.05,
                        fc=color,
                        ec=color,
                        alpha=alpha,
                    )

    def add_legend(self, loc: str = "best") -> None:
        """
        Add a legend to the plot.

        Args:
            loc: Location of the legend
        """
        with self.lock:
            self.ax.legend(loc=loc)

    def save_figure(self, filepath: str, dpi: Optional[int] = None) -> None:
        """
        Save the current figure to a file.

        Args:
            filepath: Path to save the figure to
            dpi: Resolution (dots per inch), if not provided, uses the figure's dpi
        """
        with self.lock:
            if dpi is None:
                dpi = self.dpi
            self.fig.savefig(filepath, dpi=dpi, bbox_inches="tight")
            logger.info(f"Figure saved to {filepath}")

    def get_image_bytes(self, format: str = "png", dpi: Optional[int] = None) -> bytes:
        """
        Get the current figure as image bytes.

        Args:
            format: Image format ('png', 'jpg', etc.)
            dpi: Resolution (dots per inch), if not provided, uses the figure's dpi

        Returns:
            Image bytes
        """
        with self.lock:
            if dpi is None:
                dpi = self.dpi

            # Save figure to a BytesIO object
            buf = io.BytesIO()
            self.fig.savefig(buf, format=format, dpi=dpi, bbox_inches="tight")
            buf.seek(0)
            return buf.getvalue()

    def show(self) -> None:
        """Show the current figure."""
        with self.lock:
            plt.tight_layout()
            plt.show()

    def close(self) -> None:
        """Close the current figure."""
        with self.lock:
            plt.close(self.fig)


class RealTimeVisualizer:
    """
    Real-time visualizer for navigation data.

    This class provides methods for continuously updating a visualization
    with real-time data from the robot.
    """

    def __init__(
        self,
        slam_system: SLAM,
        navigation_controller: Optional[NavigationController] = None,
        update_interval: float = 0.5,
        width: int = 8,
        height: int = 6,
        dpi: int = 100,
    ):
        """
        Initialize the real-time visualizer.

        Args:
            slam_system: SLAM system to visualize
            navigation_controller: Navigation controller to visualize (optional)
            update_interval: Interval for updating the visualization (seconds)
            width: Width of the figure in inches
            height: Height of the figure in inches
            dpi: Dots per inch (resolution)
        """
        self.slam = slam_system
        self.nav_controller = navigation_controller
        self.update_interval = update_interval

        # Create map visualizer
        self.visualizer = MapVisualizer(width=width, height=height, dpi=dpi)

        # Thread for continuous updates
        self.update_thread: Optional[threading.Thread] = None
        self.running = False

        # Callback for new frames
        self.frame_callback: Optional[Callable[[bytes], None]] = None

        logger.info("Real-time visualizer initialized")

    def set_frame_callback(self, callback: Callable[[bytes], None]) -> None:
        """
        Set a callback function to receive new visualization frames.

        Args:
            callback: Function to call with new frame bytes
        """
        self.frame_callback = callback
        logger.info("Frame callback set")

    def start(self) -> None:
        """Start the visualization updates."""
        if self.running:
            logger.warning("Visualization already running")
            return

        self.running = True
        self.update_thread = threading.Thread(target=self._update_loop, daemon=True)
        self.update_thread.start()
        logger.info("Visualization updates started")

    def stop(self) -> None:
        """Stop the visualization updates."""
        if not self.running:
            logger.warning("Visualization not running")
            return

        self.running = False
        if self.update_thread:
            self.update_thread.join(timeout=2.0)
        logger.info("Visualization updates stopped")

    def _update_loop(self) -> None:
        """Background thread for updating the visualization."""
        logger.info("Update loop started")

        while self.running:
            try:
                # Update visualization
                self._update_visualization()

                # Sleep until next update
                time.sleep(self.update_interval)

            except Exception as e:
                logger.error(f"Error in update loop: {e}")
                time.sleep(1.0)

    def _update_visualization(self) -> None:
        """Update the visualization with current data."""
        # Get current map and pose
        current_map = self.slam.get_map()
        current_pose = self.slam.get_pose()

        if current_map is None:
            logger.warning("No map available for visualization")
            return

        # Visualize map
        self.visualizer.visualize_map(current_map, title="Real-time Map")

        # Visualize current pose if available
        if current_pose:
            self.visualizer.plot_pose(
                current_pose,
                color="red",
                arrow_length=0.3,
                marker_size=10,
                label="Current Pose",
            )

        # Visualize particle filter if available
        particles = (
            self.slam.particle_filter.get_particles()
            if hasattr(self.slam, "particle_filter")
            else None
        )
        if particles is not None:
            self.visualizer.plot_particles(particles, alpha=0.3)

        # Visualize path if available
        if self.nav_controller and hasattr(self.nav_controller, "current_path"):
            path = self.nav_controller.current_path
            if path:
                self.visualizer.plot_path(
                    path,
                    color="blue",
                    line_width=2,
                    marker_size=4,
                    label="Planned Path",
                )

        # Add legend
        self.visualizer.add_legend()

        # Send frame to callback if set
        if self.frame_callback:
            frame_bytes = self.visualizer.get_image_bytes()
            self.frame_callback(frame_bytes)


class WebVisualizer:
    """
    Web-based visualizer for navigation data.

    This class provides methods for generating visualizations that can be
    displayed in a web interface, using a RealTimeVisualizer to generate
    frames.
    """

    def __init__(
        self,
        slam_system: SLAM,
        navigation_controller: Optional[NavigationController] = None,
        update_interval: float = 0.5,
        width: int = 640,
        height: int = 480,
    ):
        """
        Initialize the web visualizer.

        Args:
            slam_system: SLAM system to visualize
            navigation_controller: Navigation controller to visualize (optional)
            update_interval: Interval for updating the visualization (seconds)
            width: Width of the visualization in pixels
            height: Height of the visualization in pixels
        """
        # Calculate figure size based on pixels and DPI
        dpi = 100
        fig_width = width / dpi
        fig_height = height / dpi

        # Create real-time visualizer
        self.visualizer = RealTimeVisualizer(
            slam_system=slam_system,
            navigation_controller=navigation_controller,
            update_interval=update_interval,
            width=fig_width,
            height=fig_height,
            dpi=dpi,
        )

        # Current frame data
        self.current_frame: Optional[bytes] = None
        self.frame_lock = threading.Lock()

        # Set callback for new frames
        self.visualizer.set_frame_callback(self._on_new_frame)

        logger.info("Web visualizer initialized")

    def _on_new_frame(self, frame_bytes: bytes) -> None:
        """
        Callback for new visualization frames.

        Args:
            frame_bytes: New frame as bytes
        """
        with self.frame_lock:
            self.current_frame = frame_bytes

    def start(self) -> None:
        """Start the visualization updates."""
        self.visualizer.start()

    def stop(self) -> None:
        """Stop the visualization updates."""
        self.visualizer.stop()

    def get_current_frame(self) -> Optional[bytes]:
        """
        Get the current visualization frame.

        Returns:
            Current frame as bytes or None if no frame is available
        """
        with self.frame_lock:
            return self.current_frame


def create_test_visualization() -> None:
    """Create a test visualization to demonstrate the visualizer capabilities."""
    # Create a simple map
    width, height = 100, 100
    resolution = 0.1  # 10 cm per cell
    grid_map = OccupancyGridMap(width, height, resolution)

    # Add some obstacles
    for i in range(width):
        for j in range(height):
            # Create a simple maze-like structure
            if (i == 20 or i == 80) and (j >= 20 and j <= 80):
                grid_map.update_cell(i, j, 1.0)  # Occupied
            if (j == 20 or j == 80) and (i >= 20 and i <= 80):
                grid_map.update_cell(i, j, 1.0)  # Occupied
            if (i == 50) and (j >= 20 and j <= 50):
                grid_map.update_cell(i, j, 1.0)  # Occupied
            if (j == 50) and (i >= 50 and i <= 80):
                grid_map.update_cell(i, j, 1.0)  # Occupied

    # Create robot poses
    start_pose = Pose(2.0, 2.0, 0.0)
    current_pose = Pose(3.5, 3.5, math.pi / 4)
    goal_pose = Pose(8.0, 8.0, math.pi)

    # Create a path
    waypoints = [
        Waypoint(x=2.0, y=2.0, theta=0.0, action="start"),
        Waypoint(x=2.5, y=2.0, theta=0.0, action="navigate"),
        Waypoint(x=3.0, y=2.5, theta=math.pi / 4, action="navigate"),
        Waypoint(x=3.5, y=3.0, theta=math.pi / 4, action="navigate"),
        Waypoint(x=4.0, y=4.0, theta=math.pi / 4, action="navigate"),
        Waypoint(x=5.0, y=5.0, theta=math.pi / 4, action="navigate"),
        Waypoint(x=6.0, y=6.0, theta=math.pi / 2, action="navigate"),
        Waypoint(x=7.0, y=7.0, theta=3 * math.pi / 4, action="navigate"),
        Waypoint(x=8.0, y=8.0, theta=math.pi, action="goal"),
    ]

    # Create particles for a particle filter
    num_particles = 50
    particles = np.zeros((num_particles, 3))
    for i in range(num_particles):
        particles[i, 0] = 3.5 + np.random.normal(0, 0.2)  # x
        particles[i, 1] = 3.5 + np.random.normal(0, 0.2)  # y
        particles[i, 2] = math.pi / 4 + np.random.normal(0, 0.1)  # theta

    # Create weights
    weights = np.random.uniform(0.1, 1.0, num_particles)
    weights /= np.sum(weights)  # Normalize

    # Create visualizer
    visualizer = MapVisualizer(width=8, height=8, dpi=100)

    # Visualize map
    visualizer.visualize_map(grid_map, title="Test Visualization")

    # Plot poses
    visualizer.plot_pose(start_pose, color="green", label="Start")
    visualizer.plot_pose(current_pose, color="red", label="Current")
    visualizer.plot_pose(goal_pose, color="blue", label="Goal")

    # Plot path
    visualizer.plot_path(
        waypoints, color="purple", show_orientations=True, label="Planned Path"
    )

    # Plot particles
    visualizer.plot_particles(particles, weights)

    # Add legend
    visualizer.add_legend()

    # Show visualization
    visualizer.show()
