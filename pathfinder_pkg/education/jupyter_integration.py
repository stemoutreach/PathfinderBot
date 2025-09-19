"""
Jupyter Notebook Integration for PathfinderBot Educational Framework

This module provides functionality to integrate PathfinderBot with Jupyter notebooks,
enabling interactive learning and experimentation.
"""

import os
import sys
import json
import time
import logging
import subprocess
import ipywidgets as widgets
from typing import Dict, List, Optional, Any, Callable
from IPython.display import display, HTML, Javascript
import numpy as np
from matplotlib import pyplot as plt

from pathfinder_pkg.utils.logging import get_logger
from pathfinder_pkg.core.robot import Robot

logger = get_logger(__name__)


class JupyterRobot:
    """A wrapper class for Robot to provide interactive controls in Jupyter notebooks."""

    def __init__(self, robot: Optional[Robot] = None, use_simulator: bool = False):
        """Initialize the JupyterRobot with a real robot or simulator.

        Args:
            robot: An existing Robot instance, or None to create a new one
            use_simulator: Whether to use a simulated robot instead of real hardware
        """
        if robot is None:
            if use_simulator:
                # Import only if needed to avoid circular dependencies
                from pathfinder_pkg.simulations.robot_sim import SimulatedRobot

                self.robot = SimulatedRobot()
                self.is_simulated = True
            else:
                self.robot = Robot()
                self.is_simulated = False
        else:
            self.robot = robot
            self.is_simulated = False

        self.history = []
        self.output = widgets.Output()
        logger.info(f"Initialized JupyterRobot (Simulated: {self.is_simulated})")

    def create_control_panel(self) -> widgets.VBox:
        """Create interactive control widgets for the robot.

        Returns:
            A widget containing robot controls
        """
        style = {"description_width": "initial"}

        # Movement controls
        speed_slider = widgets.FloatSlider(
            value=0.5, min=0.1, max=1.0, step=0.1, description="Speed:", style=style
        )

        forward_button = widgets.Button(description="Forward")
        backward_button = widgets.Button(description="Backward")
        left_button = widgets.Button(description="Turn Left")
        right_button = widgets.Button(description="Turn Right")
        stop_button = widgets.Button(description="Stop", button_style="danger")

        # Camera controls
        take_photo_button = widgets.Button(
            description="Take Photo", button_style="info"
        )

        # Arm controls (if applicable)
        has_arm = hasattr(self.robot, "arm")

        if has_arm:
            arm_up_button = widgets.Button(description="Arm Up")
            arm_down_button = widgets.Button(description="Arm Down")
            grip_button = widgets.Button(description="Toggle Gripper")

            arm_controls = widgets.HBox([arm_up_button, arm_down_button, grip_button])

        # Connect event handlers
        forward_button.on_click(lambda b: self._on_forward_click(speed_slider.value))
        backward_button.on_click(lambda b: self._on_backward_click(speed_slider.value))
        left_button.on_click(lambda b: self._on_left_click(speed_slider.value))
        right_button.on_click(lambda b: self._on_right_click(speed_slider.value))
        stop_button.on_click(lambda b: self._on_stop_click())
        take_photo_button.on_click(lambda b: self._on_take_photo())

        if has_arm:
            arm_up_button.on_click(lambda b: self._on_arm_up())
            arm_down_button.on_click(lambda b: self._on_arm_down())
            grip_button.on_click(lambda b: self._on_grip_toggle())

        # Create layout
        move_controls = widgets.HBox(
            [forward_button, backward_button, left_button, right_button, stop_button]
        )

        if has_arm:
            controls = widgets.VBox(
                [
                    speed_slider,
                    move_controls,
                    arm_controls,
                    take_photo_button,
                    self.output,
                ]
            )
        else:
            controls = widgets.VBox(
                [speed_slider, move_controls, take_photo_button, self.output]
            )

        logger.info("Created interactive robot control panel")
        return controls

    def _on_forward_click(self, speed: float) -> None:
        """Handle forward button click."""
        self.robot.forward(speed)
        self._log_action(f"Moving forward at {speed:.1f} speed")

    def _on_backward_click(self, speed: float) -> None:
        """Handle backward button click."""
        self.robot.backward(speed)
        self._log_action(f"Moving backward at {speed:.1f} speed")

    def _on_left_click(self, speed: float) -> None:
        """Handle left button click."""
        self.robot.turn_left(speed)
        self._log_action(f"Turning left at {speed:.1f} speed")

    def _on_right_click(self, speed: float) -> None:
        """Handle right button click."""
        self.robot.turn_right(speed)
        self._log_action(f"Turning right at {speed:.1f} speed")

    def _on_stop_click(self) -> None:
        """Handle stop button click."""
        self.robot.stop()
        self._log_action("Robot stopped")

    def _on_take_photo(self) -> None:
        """Handle take photo button click."""
        self._log_action("Taking photo")
        try:
            img = self.robot.camera.capture()
            with self.output:
                plt.figure(figsize=(8, 6))
                plt.imshow(img[:, :, ::-1])  # Convert BGR to RGB for display
                plt.title("Robot Camera Image")
                plt.axis("off")
                plt.show()
            self._log_action("Photo captured and displayed")
        except Exception as e:
            self._log_action(f"Error capturing photo: {str(e)}")

    def _on_arm_up(self) -> None:
        """Handle arm up button click."""
        if hasattr(self.robot, "arm"):
            try:
                self.robot.arm.move_up()
                self._log_action("Moving arm up")
            except Exception as e:
                self._log_action(f"Error moving arm: {str(e)}")

    def _on_arm_down(self) -> None:
        """Handle arm down button click."""
        if hasattr(self.robot, "arm"):
            try:
                self.robot.arm.move_down()
                self._log_action("Moving arm down")
            except Exception as e:
                self._log_action(f"Error moving arm: {str(e)}")

    def _on_grip_toggle(self) -> None:
        """Handle gripper toggle button click."""
        if hasattr(self.robot, "arm") and hasattr(self.robot.arm, "gripper"):
            try:
                is_open = self.robot.arm.gripper.toggle()
                state = "opened" if is_open else "closed"
                self._log_action(f"Gripper {state}")
            except Exception as e:
                self._log_action(f"Error toggling gripper: {str(e)}")

    def _log_action(self, message: str) -> None:
        """Log an action to the output widget and history."""
        timestamp = time.strftime("%H:%M:%S")
        self.history.append(f"{timestamp}: {message}")

        with self.output:
            print(f"{timestamp}: {message}")

        logger.info(message)


class JupyterLearningTrack:
    """Interface for working with learning tracks in Jupyter notebooks."""

    def __init__(self, track_id: str = None):
        """Initialize with a specific track or load all available tracks."""
        from pathfinder_pkg.education.learning_levels import (
            LearningTrackManager,
            LearningTrack,
            DifficultyLevel,
        )

        self.manager = LearningTrackManager()
        self.manager.load_tracks()

        if track_id:
            self.current_track = self.manager.get_track(track_id)
            if not self.current_track:
                logger.warning(f"Track {track_id} not found. Loading all tracks.")
                self.current_track = None
        else:
            self.current_track = None

        self.output = widgets.Output()
        logger.info(f"Initialized JupyterLearningTrack")

    def create_track_selector(self) -> widgets.VBox:
        """Create a widget for selecting and viewing learning tracks.

        Returns:
            A widget for track selection and viewing
        """
        # Create track selector dropdown
        tracks = list(self.manager.tracks.values())
        track_options = {t.name: t.id for t in tracks}

        if not tracks:
            with self.output:
                print("No learning tracks available. Please check your installation.")
            return widgets.VBox([self.output])

        track_dropdown = widgets.Dropdown(
            options=track_options,
            description="Select Track:",
            style={"description_width": "initial"},
        )

        difficulty_filter = widgets.Dropdown(
            options=["All", "Beginner", "Intermediate", "Advanced"],
            value="All",
            description="Filter by:",
            style={"description_width": "initial"},
        )

        view_button = widgets.Button(description="View Track")
        view_button.on_click(lambda b: self._display_track(track_dropdown.value))

        controls = widgets.HBox([track_dropdown, difficulty_filter, view_button])

        # If we already have a track selected, display it
        if self.current_track:
            self._display_track(self.current_track.id)

        return widgets.VBox([controls, self.output])

    def _display_track(self, track_id: str) -> None:
        """Display the selected track information."""
        self.current_track = self.manager.get_track(track_id)

        if not self.current_track:
            with self.output:
                self.output.clear_output()
                print(f"Track {track_id} not found.")
            return

        with self.output:
            self.output.clear_output()

            print(f"# {self.current_track.name}")
            print(f"{self.current_track.description}\n")
            print(f"**Difficulty:** {self.current_track.difficulty.value.title()}")
            print(
                f"**Track Type:** {self.current_track.track_type.value.replace('_', ' ').title()}"
            )
            print(
                f"**Completion:** {self.current_track.completion_percentage():.1f}%\n"
            )

            print("## Levels")
            for i, level in enumerate(self.current_track.levels):
                status = "✅" if level.is_completed() else "⬜"
                print(
                    f"{status} **{i+1}. {level.name}** ({level.completion_percentage():.1f}% complete)"
                )
                print(f"   {level.description}")
                print(f"   *Difficulty: {level.difficulty.value.title()}*\n")

                # Display objectives for this level
                if level.objectives:
                    print(f"   **Objectives:**")
                    for obj in level.objectives:
                        obj_status = "✅" if obj.completed else "⬜"
                        print(f"   {obj_status} {obj.name}: {obj.description}")
                    print("")


class JupyterCodeTemplate:
    """Interface for working with code templates in Jupyter notebooks."""

    def __init__(self, template_id: str = None):
        """Initialize with a specific template or load all available templates."""
        from pathfinder_pkg.education.code_templates import (
            TemplateManager,
            CodeTemplate,
            TemplateCategory,
        )

        self.manager = TemplateManager()
        self.manager.load_templates()

        if not self.manager.templates:
            # Create example templates if none exist
            from pathfinder_pkg.education.code_templates import create_example_templates

            create_example_templates(self.manager)
            self.manager.load_templates()

        if template_id:
            self.current_template = self.manager.get_template(template_id)
            if not self.current_template:
                logger.warning(f"Template {template_id} not found.")
                self.current_template = None
        else:
            self.current_template = None

        self.code_widget = None
        self.output = widgets.Output()
        self.hint_count = 0
        self.code_execution_output = widgets.Output()

        logger.info(f"Initialized JupyterCodeTemplate")

    def create_template_selector(self) -> widgets.VBox:
        """Create a widget for selecting and working with code templates.

        Returns:
            A widget for template selection and coding
        """
        # Create template selector dropdown
        templates = list(self.manager.templates.values())

        if not templates:
            with self.output:
                print("No code templates available. Please check your installation.")
            return widgets.VBox([self.output])

        template_options = {t.name: t.id for t in templates}

        template_dropdown = widgets.Dropdown(
            options=template_options,
            description="Select Template:",
            style={"description_width": "initial"},
        )

        difficulty_filter = widgets.Dropdown(
            options=["All", "Beginner", "Intermediate", "Advanced"],
            value="All",
            description="Filter by:",
            style={"description_width": "initial"},
        )

        load_button = widgets.Button(description="Load Template")
        load_button.on_click(lambda b: self._load_template(template_dropdown.value))

        controls = widgets.HBox([template_dropdown, difficulty_filter, load_button])

        # If we already have a template selected, load it
        if self.current_template:
            self._load_template(self.current_template.id)

        return widgets.VBox([controls, self.output])

    def _load_template(self, template_id: str) -> None:
        """Load the selected template into the code editor."""
        self.current_template = self.manager.get_template(template_id)
        self.hint_count = 0

        if not self.current_template:
            with self.output:
                self.output.clear_output()
                print(f"Template {template_id} not found.")
            return

        # Create code editor
        self.code_widget = widgets.Textarea(
            value=self.current_template.template_code,
            placeholder="Fill in your code here",
            description="Code:",
            disabled=False,
            rows=15,
            style={"description_width": "initial"},
        )

        # Create control buttons
        hint_button = widgets.Button(description="Get Hint")
        hint_button.on_click(lambda b: self._show_hint())

        run_button = widgets.Button(description="Run Code", button_style="success")
        run_button.on_click(lambda b: self._run_code())

        check_button = widgets.Button(description="Check Solution")
        check_button.on_click(lambda b: self._check_solution())

        reset_button = widgets.Button(description="Reset Code")
        reset_button.on_click(lambda b: self._reset_code())

        button_controls = widgets.HBox(
            [hint_button, run_button, check_button, reset_button]
        )

        with self.output:
            self.output.clear_output()

            print(f"# {self.current_template.name}")
            print(f"{self.current_template.description}\n")
            print(f"**Difficulty:** {self.current_template.difficulty.value.title()}")
            print(
                f"**Category:** {self.current_template.category.value.replace('_', ' ').title()}"
            )

            if self.current_template.prerequisites:
                prereq_list = ", ".join(self.current_template.prerequisites)
                print(f"**Prerequisites:** {prereq_list}")

            display(
                widgets.VBox(
                    [self.code_widget, button_controls, self.code_execution_output]
                )
            )

    def _show_hint(self) -> None:
        """Display a hint for the current template."""
        if not self.current_template:
            return

        hints = self.current_template.hints

        with self.code_execution_output:
            self.code_execution_output.clear_output()

            if not hints:
                print("No hints available for this template.")
                return

            # Cycle through available hints
            hint_index = min(self.hint_count, len(hints) - 1)
            print(f"Hint {hint_index + 1}: {hints[hint_index]}")

            # Increment for next hint
            self.hint_count = (self.hint_count + 1) % len(hints)

    def _run_code(self) -> None:
        """Run the code in the code editor."""
        if not self.current_template or not self.code_widget:
            return

        code = self.code_widget.value

        with self.code_execution_output:
            self.code_execution_output.clear_output()
            print("Running your code...\n")

            try:
                # Create a temporary code file
                temp_file = "temp_code_execution.py"
                with open(temp_file, "w") as f:
                    f.write(code)

                # Execute the code in a separate process
                result = subprocess.run(
                    [sys.executable, temp_file], capture_output=True, text=True
                )

                # Display output
                if result.stdout:
                    print("Output:")
                    print(result.stdout)

                if result.stderr:
                    print("Errors:")
                    print(result.stderr)

                # Clean up
                if os.path.exists(temp_file):
                    os.remove(temp_file)

            except Exception as e:
                print(f"Error executing code: {str(e)}")

    def _check_solution(self) -> None:
        """Check the current code against the solution."""
        if not self.current_template or not self.code_widget:
            return

        user_code = self.code_widget.value
        diffs = self.current_template.get_diff_with_solution(user_code)

        with self.code_execution_output:
            self.code_execution_output.clear_output()

            if not diffs:
                print("Congratulations! Your solution matches the expected code. 🎉")
                return

            print("Your solution has some differences from the expected code:")
            for diff in diffs:
                print(f"  • {diff}")

            print(
                "\nDon't worry if your solution works but doesn't exactly match the expected code."
            )
            print("There are often multiple ways to solve a problem!")

    def _reset_code(self) -> None:
        """Reset the code editor to the original template."""
        if not self.current_template or not self.code_widget:
            return

        self.code_widget.value = self.current_template.template_code

        with self.code_execution_output:
            self.code_execution_output.clear_output()
            print("Code reset to original template.")


class JupyterChallenge:
    """Interface for working with challenges in Jupyter notebooks."""

    def __init__(self, challenge_id: str = None):
        """Initialize with a specific challenge or load all available challenges."""
        from pathfinder_pkg.education.challenge_system import (
            ChallengeManager,
            Challenge,
            ChallengeCategory,
            ChallengeStatus,
        )

        self.manager = ChallengeManager()
        self.manager.load_challenges()

        if not self.manager.challenges:
            # Create example challenges if none exist
            from pathfinder_pkg.education.challenge_system import (
                create_example_challenges,
            )

            create_example_challenges(self.manager)
            self.manager.load_challenges()

        if challenge_id:
            self.current_challenge = self.manager.get_challenge(challenge_id)
            if not self.current_challenge:
                logger.warning(f"Challenge {challenge_id} not found.")
                self.current_challenge = None
        else:
            self.current_challenge = None

        self.output = widgets.Output()
        logger.info(f"Initialized JupyterChallenge")

    def create_challenge_selector(self) -> widgets.VBox:
        """Create a widget for selecting and working with challenges.

        Returns:
            A widget for challenge selection and interaction
        """
        # Create challenge selector dropdown
        challenges = list(self.manager.challenges.values())

        if not challenges:
            with self.output:
                print("No challenges available. Please check your installation.")
            return widgets.VBox([self.output])

        challenge_options = {c.name: c.id for c in challenges}

        challenge_dropdown = widgets.Dropdown(
            options=challenge_options,
            description="Select Challenge:",
            style={"description_width": "initial"},
        )

        load_button = widgets.Button(description="Load Challenge")
        load_button.on_click(lambda b: self._load_challenge(challenge_dropdown.value))

        controls = widgets.HBox([challenge_dropdown, load_button])

        # If we already have a challenge selected, load it
        if self.current_challenge:
            self._load_challenge(self.current_challenge.id)

        return widgets.VBox([controls, self.output])

    def _load_challenge(self, challenge_id: str) -> None:
        """Load and display the selected challenge."""
        self.current_challenge = self.manager.get_challenge(challenge_id)

        if not self.current_challenge:
            with self.output:
                self.output.clear_output()
                print(f"Challenge {challenge_id} not found.")
            return

        with self.output:
            self.output.clear_output()

            # Display challenge information
            print(f"# {self.current_challenge.name}")
            print(f"{self.current_challenge.description}\n")
            print(f"**Difficulty:** {self.current_challenge.difficulty.value.title()}")
            print(
                f"**Category:** {self.current_challenge.category.value.replace('_', ' ').title()}"
            )
            print(
                f"**Estimated Time:** {self.current_challenge.estimated_time_minutes} minutes"
            )
            print(
                f"**Status:** {self.current_challenge.status.value.replace('_', ' ').title()}"
            )
            print(
                f"**Completion:** {self.current_challenge.completion_percentage():.1f}%\n"
            )

            # Display prerequisites if any
            if self.current_challenge.prerequisites:
                prereq_list = ", ".join(self.current_challenge.prerequisites)
                print(f"**Prerequisites:** {prereq_list}\n")

            # Display learning objectives
            if self.current_challenge.learning_objectives:
                print("## Learning Objectives")
                for obj in self.current_challenge.learning_objectives:
                    print(f"- {obj}")
                print("")

            # Display stages
            print("## Stages")
            for i, stage in enumerate(self.current_challenge.stages):
                status = "✅" if stage.completed else "⬜"
                print(f"{status} **{i+1}. {stage.name}**")
                print(f"   {stage.description}")
                print(f"   **Success Criteria:** {stage.success_criteria}\n")

                # Create complete button for each stage
                if not stage.completed:
                    complete_button = widgets.Button(
                        description=f"Mark Stage {i+1} Complete",
                        button_style="success",
                        layout=widgets.Layout(width="200px"),
                    )
                    complete_button.stage_id = stage.id
                    complete_button.on_click(self._complete_stage)
                    display(complete_button)
                    print("\n")

            # Create reset button
            if self.current_challenge.status != ChallengeStatus.NOT_STARTED:
                reset_button = widgets.Button(
                    description="Reset Challenge", button_style="warning"
                )
                reset_button.on_click(lambda b: self._reset_challenge())
                display(reset_button)

    def _complete_stage(self, button) -> None:
        """Mark a stage as completed."""
        if not self.current_challenge:
            return

        stage_id = button.stage_id
        success = self.current_challenge.complete_stage(stage_id)

        if success:
            # Re-render the challenge to show updated status
            self._load_challenge(self.current_challenge.id)

            # Save progress
            self.manager.save_progress("jupyter_user")

    def _reset_challenge(self) -> None:
        """Reset the current challenge."""
        if not self.current_challenge:
            return

        self.current_challenge.reset()

        # Save progress
        self.manager.save_progress("jupyter_user")

        # Re-render the challenge
        self._load_challenge(self.current_challenge.id)


def load_jupyter_extensions() -> None:
    """Load required Jupyter notebook extensions."""
    try:
        from IPython import get_ipython

        # Enable widgets
        get_ipython().run_line_magic("matplotlib", "inline")

        logger.info("Loaded Jupyter notebook extensions")
    except ImportError:
        logger.warning(
            "Failed to load Jupyter extensions. Some features may not work properly."
        )


def display_robot_controls(use_simulator: bool = False) -> JupyterRobot:
    """Create and display interactive robot controls.

    Args:
        use_simulator: Whether to use a simulated robot

    Returns:
        The JupyterRobot instance
    """
    robot = JupyterRobot(use_simulator=use_simulator)
    controls = robot.create_control_panel()
    display(controls)
    return robot


def display_learning_track_selector(track_id: str = None) -> JupyterLearningTrack:
    """Create and display a learning track selector.

    Args:
        track_id: Optional track ID to pre-select

    Returns:
        The JupyterLearningTrack instance
    """
    track_manager = JupyterLearningTrack(track_id)
    selector = track_manager.create_track_selector()
    display(selector)
    return track_manager


def display_code_template(template_id: str = None) -> JupyterCodeTemplate:
    """Create and display a code template editor.

    Args:
        template_id: Optional template ID to pre-select

    Returns:
        The JupyterCodeTemplate instance
    """
    template_manager = JupyterCodeTemplate(template_id)
    selector = template_manager.create_template_selector()
    display(selector)
    return template_manager


def display_challenge_selector(challenge_id: str = None) -> JupyterChallenge:
    """Create and display a challenge selector.

    Args:
        challenge_id: Optional challenge ID to pre-select

    Returns:
        The JupyterChallenge instance
    """
    challenge_manager = JupyterChallenge(challenge_id)
    selector = challenge_manager.create_challenge_selector()
    display(selector)
    return challenge_manager
