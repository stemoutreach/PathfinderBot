"""
User interface for multi-robot coordination.
Provides a dashboard for monitoring and controlling multiple robots.
"""

import tkinter as tk
from tkinter import ttk, messagebox
from typing import Dict, List, Tuple, Any, Optional, Callable
import threading
import time
import logging
import json
import math
from enum import Enum
import matplotlib

matplotlib.use("TkAgg")  # Use TkAgg backend for embedding in Tkinter
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
import matplotlib.pyplot as plt
import numpy as np

from .algorithms import Position, Pose, RobotState, Task, TaskPriority
from .communication import Message, CoordinationServer
from .behaviors import TransportRole, CoverageStatus, GameRole


class DashboardType(Enum):
    """Types of dashboards available in the UI."""

    MAIN = "main"
    TASK_ALLOCATION = "task_allocation"
    FORMATION_CONTROL = "formation_control"
    AREA_COVERAGE = "area_coverage"
    OBJECT_TRANSPORT = "object_transport"
    COLLABORATIVE_GAME = "collaborative_game"


class RobotColor:
    """Color mapping for robots in UI."""

    COLORS = [
        "#1f77b4",  # Blue
        "#ff7f0e",  # Orange
        "#2ca02c",  # Green
        "#d62728",  # Red
        "#9467bd",  # Purple
        "#8c564b",  # Brown
        "#e377c2",  # Pink
        "#7f7f7f",  # Gray
        "#bcbd22",  # Olive
        "#17becf",  # Teal
    ]

    @classmethod
    def get_color(cls, robot_id: str) -> str:
        """Get color for a robot based on its ID."""
        # Use hash of robot_id to consistently assign the same color
        color_idx = abs(hash(robot_id)) % len(cls.COLORS)
        return cls.COLORS[color_idx]


class CoordinationDashboard:
    """
    Main dashboard for multi-robot coordination visualization and control.
    """

    def __init__(self, server: Optional[CoordinationServer] = None, root=None):
        """
        Initialize the dashboard.

        Args:
            server: Optional coordination server to connect to
            root: Tkinter root window (if None, a new one will be created)
        """
        self.server = server
        self.robots: Dict[str, RobotState] = {}
        self.tasks: Dict[str, Task] = {}
        self.active_dashboard = DashboardType.MAIN
        self.dashboards = {}
        self.stop_event = threading.Event()
        self.update_interval = 100  # ms
        self.logger = logging.getLogger("CoordinationDashboard")

        # Create UI
        self.root = root if root else tk.Tk()
        self.root.title("PathfinderBot Multi-Robot Coordination Dashboard")
        self.root.geometry("1200x800")
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

        self._create_menu()
        self._create_layout()
        self._create_dashboards()

        # Start update thread
        self.update_thread = threading.Thread(target=self._update_loop, daemon=True)
        self.update_thread.start()

    def _create_menu(self):
        """Create the menu bar."""
        self.menu_bar = tk.Menu(self.root)

        # File menu
        file_menu = tk.Menu(self.menu_bar, tearoff=0)
        file_menu.add_command(label="Connect to Server", command=self.connect_to_server)
        file_menu.add_command(label="Disconnect", command=self.disconnect_from_server)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.on_close)
        self.menu_bar.add_cascade(label="File", menu=file_menu)

        # View menu
        view_menu = tk.Menu(self.menu_bar, tearoff=0)
        view_menu.add_command(
            label="Main Dashboard",
            command=lambda: self.show_dashboard(DashboardType.MAIN),
        )
        view_menu.add_command(
            label="Task Allocation",
            command=lambda: self.show_dashboard(DashboardType.TASK_ALLOCATION),
        )
        view_menu.add_command(
            label="Formation Control",
            command=lambda: self.show_dashboard(DashboardType.FORMATION_CONTROL),
        )
        view_menu.add_command(
            label="Area Coverage",
            command=lambda: self.show_dashboard(DashboardType.AREA_COVERAGE),
        )
        view_menu.add_command(
            label="Object Transport",
            command=lambda: self.show_dashboard(DashboardType.OBJECT_TRANSPORT),
        )
        view_menu.add_command(
            label="Collaborative Games",
            command=lambda: self.show_dashboard(DashboardType.COLLABORATIVE_GAME),
        )
        self.menu_bar.add_cascade(label="View", menu=view_menu)

        # Tools menu
        tools_menu = tk.Menu(self.menu_bar, tearoff=0)
        tools_menu.add_command(label="Configure Robots", command=self.configure_robots)
        tools_menu.add_command(label="Configure Tasks", command=self.configure_tasks)
        tools_menu.add_separator()
        tools_menu.add_command(label="Settings", command=self.show_settings)
        self.menu_bar.add_cascade(label="Tools", menu=tools_menu)

        # Help menu
        help_menu = tk.Menu(self.menu_bar, tearoff=0)
        help_menu.add_command(label="Documentation", command=self.show_documentation)
        help_menu.add_command(label="About", command=self.show_about)
        self.menu_bar.add_cascade(label="Help", menu=help_menu)

        self.root.config(menu=self.menu_bar)

    def _create_layout(self):
        """Create the main layout."""
        self.main_frame = ttk.Frame(self.root)
        self.main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Create a status bar
        self.status_bar = ttk.Frame(self.root, relief=tk.SUNKEN, borderwidth=1)
        self.status_bar.pack(fill=tk.X, side=tk.BOTTOM)

        self.status_label = ttk.Label(self.status_bar, text="Ready")
        self.status_label.pack(side=tk.LEFT, padx=5)

        self.connection_label = ttk.Label(self.status_bar, text="Not Connected")
        self.connection_label.pack(side=tk.RIGHT, padx=5)

    def _create_dashboards(self):
        """Create all dashboard views."""
        # Main dashboard
        main_dashboard = ttk.Frame(self.main_frame)
        main_dashboard.pack(fill=tk.BOTH, expand=True)

        # Create a notebook for different sections
        notebook = ttk.Notebook(main_dashboard)
        notebook.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Robot status tab
        robot_frame = ttk.Frame(notebook)
        notebook.add(robot_frame, text="Robot Status")

        # Robot list
        robot_list_frame = ttk.LabelFrame(robot_frame, text="Connected Robots")
        robot_list_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5, side=tk.LEFT)

        self.robot_tree = ttk.Treeview(
            robot_list_frame, columns=("ID", "Status", "Battery", "Task")
        )
        self.robot_tree.heading("#0", text="")
        self.robot_tree.heading("ID", text="Robot ID")
        self.robot_tree.heading("Status", text="Status")
        self.robot_tree.heading("Battery", text="Battery")
        self.robot_tree.heading("Task", text="Current Task")
        self.robot_tree.column("#0", width=10)
        self.robot_tree.column("ID", width=150)
        self.robot_tree.column("Status", width=100)
        self.robot_tree.column("Battery", width=80)
        self.robot_tree.column("Task", width=150)
        self.robot_tree.pack(fill=tk.BOTH, expand=True)

        robot_scrollbar = ttk.Scrollbar(
            robot_list_frame, orient="vertical", command=self.robot_tree.yview
        )
        robot_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.robot_tree.configure(yscrollcommand=robot_scrollbar.set)

        # Robot details panel
        robot_details_frame = ttk.LabelFrame(robot_frame, text="Robot Details")
        robot_details_frame.pack(
            fill=tk.BOTH, expand=True, padx=5, pady=5, side=tk.RIGHT
        )

        # Visualization frame
        vis_frame = ttk.Frame(robot_details_frame)
        vis_frame.pack(fill=tk.BOTH, expand=True)

        self.robot_fig = Figure(figsize=(6, 4), dpi=100)
        self.robot_ax = self.robot_fig.add_subplot(111)
        self.robot_ax.set_aspect("equal")
        self.robot_canvas = FigureCanvasTkAgg(self.robot_fig, master=vis_frame)
        self.robot_canvas.draw()
        self.robot_canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

        # Tasks tab
        tasks_frame = ttk.Frame(notebook)
        notebook.add(tasks_frame, text="Tasks")

        # Task list
        task_list_frame = ttk.LabelFrame(tasks_frame, text="Active Tasks")
        task_list_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5, side=tk.LEFT)

        self.task_tree = ttk.Treeview(
            task_list_frame,
            columns=("ID", "Type", "Priority", "Status", "Progress", "Assigned"),
        )
        self.task_tree.heading("#0", text="")
        self.task_tree.heading("ID", text="Task ID")
        self.task_tree.heading("Type", text="Type")
        self.task_tree.heading("Priority", text="Priority")
        self.task_tree.heading("Status", text="Status")
        self.task_tree.heading("Progress", text="Progress")
        self.task_tree.heading("Assigned", text="Assigned To")
        self.task_tree.column("#0", width=10)
        self.task_tree.column("ID", width=100)
        self.task_tree.column("Type", width=100)
        self.task_tree.column("Priority", width=80)
        self.task_tree.column("Status", width=80)
        self.task_tree.column("Progress", width=80)
        self.task_tree.column("Assigned", width=100)
        self.task_tree.pack(fill=tk.BOTH, expand=True)

        task_scrollbar = ttk.Scrollbar(
            task_list_frame, orient="vertical", command=self.task_tree.yview
        )
        task_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.task_tree.configure(yscrollcommand=task_scrollbar.set)

        # Task details
        task_details_frame = ttk.LabelFrame(tasks_frame, text="Task Details")
        task_details_frame.pack(
            fill=tk.BOTH, expand=True, padx=5, pady=5, side=tk.RIGHT
        )

        # Add task button
        add_task_button = ttk.Button(
            task_details_frame, text="Add Task", command=self.add_task
        )
        add_task_button.pack(padx=5, pady=5)

        # Communication tab
        comm_frame = ttk.Frame(notebook)
        notebook.add(comm_frame, text="Communication")

        # Message log
        message_log_frame = ttk.LabelFrame(comm_frame, text="Message Log")
        message_log_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        self.message_tree = ttk.Treeview(
            message_log_frame, columns=("Time", "From", "To", "Type", "Size")
        )
        self.message_tree.heading("#0", text="")
        self.message_tree.heading("Time", text="Time")
        self.message_tree.heading("From", text="From")
        self.message_tree.heading("To", text="To")
        self.message_tree.heading("Type", text="Type")
        self.message_tree.heading("Size", text="Size")
        self.message_tree.column("#0", width=10)
        self.message_tree.column("Time", width=150)
        self.message_tree.column("From", width=100)
        self.message_tree.column("To", width=100)
        self.message_tree.column("Type", width=150)
        self.message_tree.column("Size", width=80)
        self.message_tree.pack(fill=tk.BOTH, expand=True)

        message_scrollbar = ttk.Scrollbar(
            message_log_frame, orient="vertical", command=self.message_tree.yview
        )
        message_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.message_tree.configure(yscrollcommand=message_scrollbar.set)

        # Store main dashboard
        self.dashboards[DashboardType.MAIN] = main_dashboard

        # Create other specialized dashboards (hidden initially)
        self._create_task_allocation_dashboard()
        self._create_formation_control_dashboard()
        self._create_area_coverage_dashboard()
        self._create_object_transport_dashboard()
        self._create_collaborative_game_dashboard()

        # Show main dashboard by default
        self.show_dashboard(DashboardType.MAIN)

    def _create_task_allocation_dashboard(self):
        """Create the task allocation dashboard."""
        dashboard = ttk.Frame(self.main_frame)

        # Title
        title_label = ttk.Label(
            dashboard, text="Task Allocation Dashboard", font=("Helvetica", 16, "bold")
        )
        title_label.pack(pady=10)

        # Split into two frames
        left_frame = ttk.Frame(dashboard)
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5)

        right_frame = ttk.Frame(dashboard)
        right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Available robots frame
        available_robots_frame = ttk.LabelFrame(left_frame, text="Available Robots")
        available_robots_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        self.available_robot_tree = ttk.Treeview(
            available_robots_frame, columns=("ID", "Capabilities", "Battery")
        )
        self.available_robot_tree.heading("#0", text="")
        self.available_robot_tree.heading("ID", text="Robot ID")
        self.available_robot_tree.heading("Capabilities", text="Capabilities")
        self.available_robot_tree.heading("Battery", text="Battery")
        self.available_robot_tree.column("#0", width=10)
        self.available_robot_tree.column("ID", width=150)
        self.available_robot_tree.column("Capabilities", width=150)
        self.available_robot_tree.column("Battery", width=80)
        self.available_robot_tree.pack(fill=tk.BOTH, expand=True)

        # Pending tasks frame
        pending_tasks_frame = ttk.LabelFrame(right_frame, text="Pending Tasks")
        pending_tasks_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        self.pending_task_tree = ttk.Treeview(
            pending_tasks_frame, columns=("ID", "Type", "Priority", "Requirements")
        )
        self.pending_task_tree.heading("#0", text="")
        self.pending_task_tree.heading("ID", text="Task ID")
        self.pending_task_tree.heading("Type", text="Type")
        self.pending_task_tree.heading("Priority", text="Priority")
        self.pending_task_tree.heading("Requirements", text="Requirements")
        self.pending_task_tree.column("#0", width=10)
        self.pending_task_tree.column("ID", width=150)
        self.pending_task_tree.column("Type", width=100)
        self.pending_task_tree.column("Priority", width=80)
        self.pending_task_tree.column("Requirements", width=150)
        self.pending_task_tree.pack(fill=tk.BOTH, expand=True)

        # Allocations frame
        allocations_frame = ttk.LabelFrame(dashboard, text="Current Allocations")
        allocations_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        self.allocations_tree = ttk.Treeview(
            allocations_frame, columns=("Task", "Robot", "Status", "Progress")
        )
        self.allocations_tree.heading("#0", text="")
        self.allocations_tree.heading("Task", text="Task")
        self.allocations_tree.heading("Robot", text="Assigned Robot")
        self.allocations_tree.heading("Status", text="Status")
        self.allocations_tree.heading("Progress", text="Progress")
        self.allocations_tree.column("#0", width=10)
        self.allocations_tree.column("Task", width=150)
        self.allocations_tree.column("Robot", width=150)
        self.allocations_tree.column("Status", width=100)
        self.allocations_tree.column("Progress", width=100)
        self.allocations_tree.pack(fill=tk.BOTH, expand=True)

        # Buttons frame
        buttons_frame = ttk.Frame(dashboard)
        buttons_frame.pack(fill=tk.X, pady=10)

        allocate_btn = ttk.Button(
            buttons_frame, text="Allocate Tasks", command=self.allocate_tasks
        )
        allocate_btn.pack(side=tk.LEFT, padx=5)

        add_task_btn = ttk.Button(buttons_frame, text="Add Task", command=self.add_task)
        add_task_btn.pack(side=tk.LEFT, padx=5)

        clear_btn = ttk.Button(
            buttons_frame, text="Clear Completed", command=self.clear_completed_tasks
        )
        clear_btn.pack(side=tk.LEFT, padx=5)

        self.dashboards[DashboardType.TASK_ALLOCATION] = dashboard

    def _create_formation_control_dashboard(self):
        """Create the formation control dashboard."""
        dashboard = ttk.Frame(self.main_frame)

        # Title
        title_label = ttk.Label(
            dashboard,
            text="Formation Control Dashboard",
            font=("Helvetica", 16, "bold"),
        )
        title_label.pack(pady=10)

        # Formation control frame
        control_frame = ttk.LabelFrame(dashboard, text="Formation Control")
        control_frame.pack(fill=tk.X, padx=10, pady=5)

        # Formation type selection
        form_type_frame = ttk.Frame(control_frame)
        form_type_frame.pack(fill=tk.X, pady=5)

        ttk.Label(form_type_frame, text="Formation Type:").pack(side=tk.LEFT, padx=5)

        self.formation_type_var = tk.StringVar(value="line")
        formation_combo = ttk.Combobox(
            form_type_frame, textvariable=self.formation_type_var
        )
        formation_combo["values"] = (
            "line",
            "column",
            "wedge",
            "echelon_left",
            "echelon_right",
            "vee",
            "circle",
            "grid",
        )
        formation_combo.pack(side=tk.LEFT, padx=5)

        # Spacing
        spacing_frame = ttk.Frame(control_frame)
        spacing_frame.pack(fill=tk.X, pady=5)

        ttk.Label(spacing_frame, text="Robot Spacing (m):").pack(side=tk.LEFT, padx=5)

        self.spacing_var = tk.DoubleVar(value=1.0)
        spacing_spin = ttk.Spinbox(
            spacing_frame,
            from_=0.2,
            to=3.0,
            increment=0.1,
            textvariable=self.spacing_var,
        )
        spacing_spin.pack(side=tk.LEFT, padx=5)

        # Leader selection
        leader_frame = ttk.Frame(control_frame)
        leader_frame.pack(fill=tk.X, pady=5)

        ttk.Label(leader_frame, text="Formation Leader:").pack(side=tk.LEFT, padx=5)

        self.leader_var = tk.StringVar()
        self.leader_combo = ttk.Combobox(leader_frame, textvariable=self.leader_var)
        self.leader_combo.pack(side=tk.LEFT, padx=5)

        # Apply button
        apply_btn = ttk.Button(
            control_frame, text="Apply Formation", command=self.apply_formation
        )
        apply_btn.pack(pady=5)

        # Visualization frame
        vis_frame = ttk.LabelFrame(dashboard, text="Formation Visualization")
        vis_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        # Formation visualization
        self.formation_fig = Figure(figsize=(8, 6), dpi=100)
        self.formation_ax = self.formation_fig.add_subplot(111)
        self.formation_ax.set_aspect("equal")
        self.formation_ax.set_xlabel("X (m)")
        self.formation_ax.set_ylabel("Y (m)")
        self.formation_canvas = FigureCanvasTkAgg(self.formation_fig, master=vis_frame)
        self.formation_canvas.draw()
        self.formation_canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

        self.dashboards[DashboardType.FORMATION_CONTROL] = dashboard

    def _create_area_coverage_dashboard(self):
        """Create the area coverage dashboard."""
        dashboard = ttk.Frame(self.main_frame)

        # Title
        title_label = ttk.Label(
            dashboard, text="Area Coverage Dashboard", font=("Helvetica", 16, "bold")
        )
        title_label.pack(pady=10)

        # Split into control and visualization frames
        control_frame = ttk.Frame(dashboard)
        control_frame.pack(side=tk.LEFT, fill=tk.BOTH, padx=10, pady=5)

        vis_frame = ttk.Frame(dashboard)
        vis_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=10, pady=5)

        # Area configuration frame
        area_config_frame = ttk.LabelFrame(control_frame, text="Area Configuration")
        area_config_frame.pack(fill=tk.X, pady=5)

        # Grid size
        grid_size_frame = ttk.Frame(area_config_frame)
        grid_size_frame.pack(fill=tk.X, pady=5)

        ttk.Label(grid_size_frame, text="Grid Size X:").grid(
            row=0, column=0, padx=5, pady=2
        )
        self.grid_size_x_var = tk.IntVar(value=10)
        ttk.Spinbox(
            grid_size_frame, from_=2, to=50, textvariable=self.grid_size_x_var
        ).grid(row=0, column=1, padx=5, pady=2)

        ttk.Label(grid_size_frame, text="Grid Size Y:").grid(
            row=1, column=0, padx=5, pady=2
        )
        self.grid_size_y_var = tk.IntVar(value=10)
        ttk.Spinbox(
            grid_size_frame, from_=2, to=50, textvariable=self.grid_size_y_var
        ).grid(row=1, column=1, padx=5, pady=2)

        # Cell size
        cell_size_frame = ttk.Frame(area_config_frame)
        cell_size_frame.pack(fill=tk.X, pady=5)

        ttk.Label(cell_size_frame, text="Cell Size (m):").pack(side=tk.LEFT, padx=5)
        self.cell_size_var = tk.DoubleVar(value=1.0)
        ttk.Spinbox(
            cell_size_frame,
            from_=0.2,
            to=5.0,
            increment=0.1,
            textvariable=self.cell_size_var,
        ).pack(side=tk.LEFT, padx=5)

        # Create/configure area button
        create_btn = ttk.Button(
            area_config_frame, text="Create/Configure Area", command=self.configure_area
        )
        create_btn.pack(pady=5)

        # Robot status frame
        robot_status_frame = ttk.LabelFrame(control_frame, text="Robots")
        robot_status_frame.pack(fill=tk.X, pady=5)

        # Robot list
        self.coverage_robot_list = ttk.Treeview(
            robot_status_frame, columns=("ID", "Status")
        )
        self.coverage_robot_list.heading("#0", text="")
        self.coverage_robot_list.heading("ID", text="Robot ID")
        self.coverage_robot_list.heading("Status", text="Status")
        self.coverage_robot_list.column("#0", width=10)
        self.coverage_robot_list.column("ID", width=100)
        self.coverage_robot_list.column("Status", width=100)
        self.coverage_robot_list.pack(fill=tk.BOTH, expand=True, pady=5)

        # Control buttons
        button_frame = ttk.Frame(control_frame)
        button_frame.pack(fill=tk.X, pady=10)

        start_btn = ttk.Button(
            button_frame, text="Start Coverage", command=self.start_coverage
        )
        start_btn.pack(side=tk.LEFT, padx=5)

        pause_btn = ttk.Button(button_frame, text="Pause", command=self.pause_coverage)
        pause_btn.pack(side=tk.LEFT, padx=5)

        reset_btn = ttk.Button(button_frame, text="Reset", command=self.reset_coverage)
        reset_btn.pack(side=tk.LEFT, padx=5)

        # Coverage visualization frame
        vis_label_frame = ttk.LabelFrame(vis_frame, text="Area Coverage Map")
        vis_label_frame.pack(fill=tk.BOTH, expand=True)

        # Coverage visualization
        self.coverage_fig = Figure(figsize=(8, 6), dpi=100)
        self.coverage_ax = self.coverage_fig.add_subplot(111)
        self.coverage_ax.set_aspect("equal")
        self.coverage_ax.set_xlabel("X (m)")
        self.coverage_ax.set_ylabel("Y (m)")
        self.coverage_canvas = FigureCanvasTkAgg(
            self.coverage_fig, master=vis_label_frame
        )
        self.coverage_canvas.draw()
        self.coverage_canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

        # Status frame
        status_frame = ttk.Frame(vis_frame)
        status_frame.pack(fill=tk.X, pady=5)

        # Progress bar
        ttk.Label(status_frame, text="Coverage Progress:").pack(side=tk.LEFT, padx=5)
        self.coverage_progress = ttk.Progressbar(
            status_frame, orient="horizontal", length=200, mode="determinate"
        )
        self.coverage_progress.pack(side=tk.LEFT, padx=5)

        self.dashboards[DashboardType.AREA_COVERAGE] = dashboard

    def _create_object_transport_dashboard(self):
        """Create the object transport dashboard."""
        dashboard = ttk.Frame(self.main_frame)

        # Title
        title_label = ttk.Label(
            dashboard, text="Object Transport Dashboard", font=("Helvetica", 16, "bold")
        )
        title_label.pack(pady=10)

        # Split into control and visualization frames
        control_frame = ttk.Frame(dashboard)
        control_frame.pack(side=tk.LEFT, fill=tk.BOTH, padx=10, pady=5, expand=False)

        vis_frame = ttk.Frame(dashboard)
        vis_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=10, pady=5)

        # Object configuration frame
        obj_config_frame = ttk.LabelFrame(control_frame, text="Object Configuration")
        obj_config_frame.pack(fill=tk.X, pady=5)

        # Object position
        pos_frame = ttk.Frame(obj_config_frame)
        pos_frame.pack(fill=tk.X, pady=5)

        ttk.Label(pos_frame, text="Object Position:").grid(
            row=0, column=0, padx=5, pady=2
        )

        pos_entry_frame = ttk.Frame(pos_frame)
        pos_entry_frame.grid(row=0, column=1, padx=5, pady=2)

        ttk.Label(pos_entry_frame, text="X:").grid(row=0, column=0)
        self.obj_x_var = tk.DoubleVar(value=0.0)
        ttk.Spinbox(
            pos_entry_frame,
            from_=-100,
            to=100,
            increment=0.1,
            width=5,
            textvariable=self.obj_x_var,
        ).grid(row=0, column=1)

        ttk.Label(pos_entry_frame, text="Y:").grid(row=0, column=2, padx=5)
        self.obj_y_var = tk.DoubleVar(value=0.0)
        ttk.Spinbox(
            pos_entry_frame,
            from_=-100,
            to=100,
            increment=0.1,
            width=5,
            textvariable=self.obj_y_var,
        ).grid(row=0, column=3)

        # Object orientation
        orientation_frame = ttk.Frame(obj_config_frame)
        orientation_frame.pack(fill=tk.X, pady=5)

        ttk.Label(orientation_frame, text="Object Orientation (deg):").pack(
            side=tk.LEFT, padx=5
        )
        self.obj_orientation_var = tk.DoubleVar(value=0.0)
        ttk.Spinbox(
            orientation_frame,
            from_=0,
            to=360,
            increment=5,
            textvariable=self.obj_orientation_var,
        ).pack(side=tk.LEFT, padx=5)

        # Target position
        target_frame = ttk.Frame(obj_config_frame)
        target_frame.pack(fill=tk.X, pady=5)

        ttk.Label(target_frame, text="Target Position:").grid(
            row=0, column=0, padx=5, pady=2
        )

        target_entry_frame = ttk.Frame(target_frame)
        target_entry_frame.grid(row=0, column=1, padx=5, pady=2)

        ttk.Label(target_entry_frame, text="X:").grid(row=0, column=0)
        self.target_x_var = tk.DoubleVar(value=5.0)
        ttk.Spinbox(
            target_entry_frame,
            from_=-100,
            to=100,
            increment=0.1,
            width=5,
            textvariable=self.target_x_var,
        ).grid(row=0, column=1)

        ttk.Label(target_entry_frame, text="Y:").grid(row=0, column=2, padx=5)
        self.target_y_var = tk.DoubleVar(value=5.0)
        ttk.Spinbox(
            target_entry_frame,
            from_=-100,
            to=100,
            increment=0.1,
            width=5,
            textvariable=self.target_y_var,
        ).grid(row=0, column=3)

        # Robot selection
        robot_frame = ttk.LabelFrame(control_frame, text="Transport Robots")
        robot_frame.pack(fill=tk.BOTH, expand=True, pady=5)

        self.transport_robot_tree = ttk.Treeview(robot_frame, columns=("ID", "Role"))
        self.transport_robot_tree.heading("#0", text="")
        self.transport_robot_tree.heading("ID", text="Robot ID")
        self.transport_robot_tree.heading("Role", text="Role")
        self.transport_robot_tree.column("#0", width=10)
        self.transport_robot_tree.column("ID", width=100)
        self.transport_robot_tree.column("Role", width=100)
        self.transport_robot_tree.pack(fill=tk.BOTH, expand=True, pady=5)

        # Buttons
        button_frame = ttk.Frame(control_frame)
        button_frame.pack(fill=tk.X, pady=10)

        assign_btn = ttk.Button(
            button_frame, text="Assign Roles", command=self.assign_transport_roles
        )
        assign_btn.pack(side=tk.LEFT, padx=5)

        start_btn = ttk.Button(
            button_frame, text="Start Transport", command=self.start_transport
        )
        start_btn.pack(side=tk.LEFT, padx=5)

        stop_btn = ttk.Button(button_frame, text="Stop", command=self.stop_transport)
        stop_btn.pack(side=tk.LEFT, padx=5)

        # Transport visualization
        vis_label_frame = ttk.LabelFrame(vis_frame, text="Transport Visualization")
        vis_label_frame.pack(fill=tk.BOTH, expand=True)

        self.transport_fig = Figure(figsize=(8, 6), dpi=100)
        self.transport_ax = self.transport_fig.add_subplot(111)
        self.transport_ax.set_aspect("equal")
        self.transport_ax.set_xlabel("X (m)")
        self.transport_ax.set_ylabel("Y (m)")
        self.transport_canvas = FigureCanvasTkAgg(
            self.transport_fig, master=vis_label_frame
        )
        self.transport_canvas.draw()
        self.transport_canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

        self.dashboards[DashboardType.OBJECT_TRANSPORT] = dashboard

    def _create_collaborative_game_dashboard(self):
        """Create the collaborative game dashboard."""
        dashboard = ttk.Frame(self.main_frame)

        # Title
        title_label = ttk.Label(
            dashboard,
            text="Collaborative Games Dashboard",
            font=("Helvetica", 16, "bold"),
        )
        title_label.pack(pady=10)

        # Game selection frame
        game_selection_frame = ttk.LabelFrame(dashboard, text="Game Selection")
        game_selection_frame.pack(fill=tk.X, padx=10, pady=5)

        # Game type
        game_type_frame = ttk.Frame(game_selection_frame)
        game_type_frame.pack(fill=tk.X, pady=5)

        ttk.Label(game_type_frame, text="Game Type:").pack(side=tk.LEFT, padx=5)

        self.game_type_var = tk.StringVar(value="soccer")
        game_combo = ttk.Combobox(game_type_frame, textvariable=self.game_type_var)
        game_combo["values"] = ("soccer", "relay_race", "cooperative_puzzle")
        game_combo.pack(side=tk.LEFT, padx=5)

        # Game control buttons
        game_btn_frame = ttk.Frame(game_selection_frame)
        game_btn_frame.pack(fill=tk.X, pady=5)

        config_btn = ttk.Button(
            game_btn_frame, text="Configure Game", command=self.configure_game
        )
        config_btn.pack(side=tk.LEFT, padx=5)

        start_btn = ttk.Button(
            game_btn_frame, text="Start Game", command=self.start_game
        )
        start_btn.pack(side=tk.LEFT, padx=5)

        stop_btn = ttk.Button(game_btn_frame, text="Stop Game", command=self.stop_game)
        stop_btn.pack(side=tk.LEFT, padx=5)

        reset_btn = ttk.Button(game_btn_frame, text="Reset", command=self.reset_game)
        reset_btn.pack(side=tk.LEFT, padx=5)

        # Split into robot list and game visualization
        middle_frame = ttk.Frame(dashboard)
        middle_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        # Robot list frame
        robot_frame = ttk.LabelFrame(middle_frame, text="Game Robots")
        robot_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=False)

        self.game_robot_tree = ttk.Treeview(
            robot_frame, columns=("ID", "Role", "Status")
        )
        self.game_robot_tree.heading("#0", text="")
        self.game_robot_tree.heading("ID", text="Robot ID")
        self.game_robot_tree.heading("Role", text="Role")
        self.game_robot_tree.heading("Status", text="Status")
        self.game_robot_tree.column("#0", width=10)
        self.game_robot_tree.column("ID", width=100)
        self.game_robot_tree.column("Role", width=100)
        self.game_robot_tree.column("Status", width=100)
        self.game_robot_tree.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Game visualization frame
        vis_frame = ttk.LabelFrame(middle_frame, text="Game Visualization")
        vis_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=5)

        self.game_fig = Figure(figsize=(8, 6), dpi=100)
        self.game_ax = self.game_fig.add_subplot(111)
        self.game_ax.set_aspect("equal")
        self.game_ax.set_xlabel("X (m)")
        self.game_ax.set_ylabel("Y (m)")
        self.game_canvas = FigureCanvasTkAgg(self.game_fig, master=vis_frame)
        self.game_canvas.draw()
        self.game_canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

        # Game status frame
        status_frame = ttk.LabelFrame(dashboard, text="Game Status")
        status_frame.pack(fill=tk.X, padx=10, pady=5)

        # Status display - will be filled dynamically based on game type
        self.game_status_text = tk.Text(status_frame, height=5, state="disabled")
        self.game_status_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        self.dashboards[DashboardType.COLLABORATIVE_GAME] = dashboard

    def show_dashboard(self, dashboard_type: DashboardType):
        """Show the specified dashboard and hide others."""
        for dash_type, dashboard in self.dashboards.items():
            if dash_type == dashboard_type:
                dashboard.pack(fill=tk.BOTH, expand=True)
            else:
                dashboard.pack_forget()

        self.active_dashboard = dashboard_type
        self.update_active_dashboard()

    def _update_loop(self):
        """Background thread for updating UI elements."""
        while not self.stop_event.is_set():
            try:
                # Use after to schedule UI updates from the main thread
                self.root.after(self.update_interval, self.update_ui)
                time.sleep(self.update_interval / 1000)  # Convert to seconds
            except Exception as e:
                self.logger.error(f"Error in update loop: {e}")

    def update_ui(self):
        """Update all UI elements with current data."""
        try:
            # Update status bar
            if self.server and self.server.get_connected_robots():
                robot_count = len(self.server.get_connected_robots())
                self.connection_label.config(text=f"Connected: {robot_count} robots")
            else:
                self.connection_label.config(text="Not Connected")

            # Update active dashboard
            self.update_active_dashboard()

        except Exception as e:
            self.logger.error(f"Error updating UI: {e}")

    def update_active_dashboard(self):
        """Update the currently active dashboard."""
        if self.active_dashboard == DashboardType.MAIN:
            self.update_main_dashboard()
        elif self.active_dashboard == DashboardType.TASK_ALLOCATION:
            self.update_task_allocation_dashboard()
        elif self.active_dashboard == DashboardType.FORMATION_CONTROL:
            self.update_formation_control_dashboard()
        elif self.active_dashboard == DashboardType.AREA_COVERAGE:
            self.update_area_coverage_dashboard()
        elif self.active_dashboard == DashboardType.OBJECT_TRANSPORT:
            self.update_object_transport_dashboard()
        elif self.active_dashboard == DashboardType.COLLABORATIVE_GAME:
            self.update_collaborative_game_dashboard()

    def update_main_dashboard(self):
        """Update the main dashboard."""
        # Update robot list
        self.robot_tree.delete(*self.robot_tree.get_children())
        for robot_id, robot_state in self.robots.items():
            status = (
                "Active" if robot_state.last_updated > time.time() - 5 else "Inactive"
            )
            battery = f"{robot_state.battery_level * 100:.1f}%"
            current_task = robot_state.current_task or "None"

            self.robot_tree.insert(
                "", "end", values=(robot_id, status, battery, current_task)
            )

        # Update task list
        self.task_tree.delete(*self.task_tree.get_children())
        for task_id, task in self.tasks.items():
            progress = f"{task.progress * 100:.1f}%"
            self.task_tree.insert(
                "",
                "end",
                values=(
                    task_id,
                    task.task_type,
                    task.priority.name,
                    task.status,
                    progress,
                    task.assigned_robot or "None",
                ),
            )

        # Update robot visualization
        if self.robots:
            self.robot_ax.clear()
            for robot_id, robot_state in self.robots.items():
                # Draw robot position
                x, y = robot_state.pose.position.x, robot_state.pose.position.y
                color = RobotColor.get_color(robot_id)

                # Draw robot as a circle with an orientation line
                circle = plt.Circle((x, y), 0.2, color=color, alpha=0.7)
                self.robot_ax.add_patch(circle)

                # Draw orientation line
                orientation = robot_state.pose.orientation
                dx = 0.3 * math.cos(orientation)
                dy = 0.3 * math.sin(orientation)
                self.robot_ax.arrow(
                    x, y, dx, dy, head_width=0.1, head_length=0.1, fc=color, ec=color
                )

                # Add robot ID text
                self.robot_ax.text(
                    x, y + 0.3, robot_id, ha="center", va="center", color=color
                )

            self.robot_ax.set_xlim(-10, 10)
            self.robot_ax.set_ylim(-10, 10)
            self.robot_ax.set_aspect("equal")
            self.robot_ax.grid(True)
            self.robot_canvas.draw()

    def update_task_allocation_dashboard(self):
        """Update the task allocation dashboard."""
        # Implementation will be added later
        pass

    def update_formation_control_dashboard(self):
        """Update the formation control dashboard."""
        # Implementation will be added later
        pass

    def update_area_coverage_dashboard(self):
        """Update the area coverage dashboard."""
        # Implementation will be added later
        pass

    def update_object_transport_dashboard(self):
        """Update the object transport dashboard."""
        # Implementation will be added later
        pass

    def update_collaborative_game_dashboard(self):
        """Update the collaborative game dashboard."""
        # Implementation will be added later
        pass

    def connect_to_server(self):
        """Connect to the coordination server."""
        # Show connection dialog
        # Implementation will be added later
        pass

    def disconnect_from_server(self):
        """Disconnect from the coordination server."""
        if self.server:
            # Disconnect logic
            self.connection_label.config(text="Not Connected")

    def configure_robots(self):
        """Open robot configuration dialog."""
        # Implementation will be added later
        pass

    def configure_tasks(self):
        """Open task configuration dialog."""
        # Implementation will be added later
        pass

    def add_task(self):
        """Add a new task."""
        # Implementation will be added later
        pass

    def allocate_tasks(self):
        """Allocate tasks to robots."""
        # Implementation will be added later
        pass

    def clear_completed_tasks(self):
        """Clear completed tasks from the list."""
        # Implementation will be added later
        pass

    def apply_formation(self):
        """Apply the selected formation to robots."""
        # Implementation will be added later
        pass

    def configure_area(self):
        """Configure the area for coverage."""
        # Implementation will be added later
        pass

    def start_coverage(self):
        """Start the area coverage operation."""
        # Implementation will be added later
        pass

    def pause_coverage(self):
        """Pause the area coverage operation."""
        # Implementation will be added later
        pass

    def reset_coverage(self):
        """Reset the area coverage operation."""
        # Implementation will be added later
        pass

    def assign_transport_roles(self):
        """Assign roles for object transport."""
        # Implementation will be added later
        pass

    def start_transport(self):
        """Start the object transport operation."""
        # Implementation will be added later
        pass

    def stop_transport(self):
        """Stop the object transport operation."""
        # Implementation will be added later
        pass

    def configure_game(self):
        """Configure the selected game."""
        # Implementation will be added later
        pass

    def start_game(self):
        """Start the selected game."""
        # Implementation will be added later
        pass

    def stop_game(self):
        """Stop the current game."""
        # Implementation will be added later
        pass

    def reset_game(self):
        """Reset the current game."""
        # Implementation will be added later
        pass

    def show_settings(self):
        """Show settings dialog."""
        # Implementation will be added later
        pass

    def show_documentation(self):
        """Show documentation."""
        # Implementation will be added later
        pass

    def show_about(self):
        """Show about dialog."""
        # Implementation will be added later
        pass

    def run(self):
        """Start the dashboard."""
        self.root.mainloop()

    def on_close(self):
        """Handle window close event."""
        self.stop_event.set()
        if self.server:
            # Disconnect from server
            pass
        self.root.destroy()


def launch_dashboard(server=None):
    """Launch the coordination dashboard."""
    dashboard = CoordinationDashboard(server)
    dashboard.run()


if __name__ == "__main__":
    launch_dashboard()
