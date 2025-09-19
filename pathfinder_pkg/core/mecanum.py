"""
Mecanum drive control module for PathfinderBot.

This module provides control for the mecanum drive system, allowing for
omnidirectional movement with holonomic control.
"""

import time
import math
import numpy as np
from pathfinder_pkg.utils.logging import get_logger

logger = get_logger(__name__)

# Default constants
WHEEL_RADIUS_MM = 60.0
WHEEL_BASE_WIDTH_MM = 220.0  # Distance between left and right wheels
WHEEL_BASE_LENGTH_MM = 200.0  # Distance between front and rear wheels
WHEEL_GEAR_RATIO = 50.0  # Motor gear ratio
ENCODER_TICKS_PER_REV = 1120.0  # Encoder ticks per revolution
MAX_SPEED_RPM = 180.0  # Maximum motor speed in RPM


class MecanumChassis:
    """
    Controller for a mecanum drive chassis with 4 wheels.

    This class provides methods to control a 4-wheeled mecanum drive system,
    allowing for holonomic motion (movement in any direction without changing orientation).

    Attributes:
        wheel_radius (float): Radius of wheels in mm.
        wheel_base_width (float): Distance between left and right wheels in mm.
        wheel_base_length (float): Distance between front and rear wheels in mm.
        max_rpm (float): Maximum RPM of the motors.
        gear_ratio (float): Gear ratio of the motors.
        encoder_ticks_per_rev (float): Encoder ticks per revolution.
    """

    def __init__(
        self,
        wheel_radius=WHEEL_RADIUS_MM,
        wheel_base_width=WHEEL_BASE_WIDTH_MM,
        wheel_base_length=WHEEL_BASE_LENGTH_MM,
        max_rpm=MAX_SPEED_RPM,
        gear_ratio=WHEEL_GEAR_RATIO,
        encoder_ticks_per_rev=ENCODER_TICKS_PER_REV,
    ):
        """
        Initialize the mecanum chassis with the specified parameters.

        Args:
            wheel_radius (float, optional): Radius of wheels in mm.
            wheel_base_width (float, optional): Distance between left and right wheels in mm.
            wheel_base_length (float, optional): Distance between front and rear wheels in mm.
            max_rpm (float, optional): Maximum RPM of the motors.
            gear_ratio (float, optional): Gear ratio of the motors.
            encoder_ticks_per_rev (float, optional): Encoder ticks per revolution.
        """
        self.wheel_radius = wheel_radius
        self.wheel_base_width = wheel_base_width
        self.wheel_base_length = wheel_base_length
        self.max_rpm = max_rpm
        self.gear_ratio = gear_ratio
        self.encoder_ticks_per_rev = encoder_ticks_per_rev

        self.max_speed_mm_s = (self.max_rpm / 60.0) * 2.0 * math.pi * self.wheel_radius

        self._motor_speeds = [0.0, 0.0, 0.0, 0.0]  # FL, FR, RL, RR
        self._motor_positions = [0, 0, 0, 0]  # FL, FR, RL, RR

        try:
            # Import hardware-specific motor control based on platform
            self._init_hardware()
            logger.info("MecanumChassis initialized successfully")
        except ImportError as e:
            logger.warning(
                f"Hardware motor drivers not found: {e}. Using simulation mode."
            )
        except Exception as e:
            logger.error(f"Failed to initialize motors: {e}")

    def _init_hardware(self):
        """Initialize the hardware motor controllers."""
        try:
            # This will be implemented with actual hardware drivers
            # For now, just log that we're in simulation mode
            logger.info("Motor hardware initialization would occur here")
            logger.info("Running in simulation mode")
        except Exception as e:
            logger.error(f"Error initializing motor hardware: {e}")
            raise

    def translation(self, x_mm_s, y_mm_s):
        """
        Move the chassis in a straight line.

        Args:
            x_mm_s (float): Speed in the x-direction (sideways) in mm/s.
                            Positive is right, negative is left.
            y_mm_s (float): Speed in the y-direction (forward/backward) in mm/s.
                            Positive is forward, negative is backward.
        """
        if abs(x_mm_s) < 1e-6 and abs(y_mm_s) < 1e-6:
            self.reset_motors()
            return

        # Clamp speeds to maximum
        magnitude = math.sqrt(x_mm_s**2 + y_mm_s**2)
        if magnitude > self.max_speed_mm_s:
            scale = self.max_speed_mm_s / magnitude
            x_mm_s *= scale
            y_mm_s *= scale

        logger.debug(f"Translation: x={x_mm_s:.2f} mm/s, y={y_mm_s:.2f} mm/s")
        self.set_velocity(x_mm_s, y_mm_s, 0.0)

    def rotation(self, omega_rad_s):
        """
        Rotate the chassis around its center.

        Args:
            omega_rad_s (float): Angular velocity in radians per second.
                                Positive is counter-clockwise, negative is clockwise.
        """
        if abs(omega_rad_s) < 1e-6:
            self.reset_motors()
            return

        logger.debug(f"Rotation: omega={omega_rad_s:.2f} rad/s")
        self.set_velocity(0.0, 0.0, omega_rad_s)

    def set_velocity(self, x_mm_s, y_mm_s, omega_rad_s):
        """
        Set the velocity of the chassis in all three dimensions.

        Args:
            x_mm_s (float): Speed in the x-direction (sideways) in mm/s.
            y_mm_s (float): Speed in the y-direction (forward/backward) in mm/s.
            omega_rad_s (float): Angular velocity in radians per second.
        """
        # Convert omega from rad/s to mm/s at the wheel
        rotation_factor = (
            omega_rad_s * (self.wheel_base_width + self.wheel_base_length) / 2.0
        )

        # Calculate wheel speeds based on desired motion
        # Front Left = y + x + rotation
        # Front Right = y - x - rotation
        # Rear Left = y - x + rotation
        # Rear Right = y + x - rotation
        self._motor_speeds[0] = y_mm_s + x_mm_s + rotation_factor  # Front Left
        self._motor_speeds[1] = y_mm_s - x_mm_s - rotation_factor  # Front Right
        self._motor_speeds[2] = y_mm_s - x_mm_s + rotation_factor  # Rear Left
        self._motor_speeds[3] = y_mm_s + x_mm_s - rotation_factor  # Rear Right

        # Find the maximum wheel speed
        max_speed = max(map(abs, self._motor_speeds))

        # Scale all speeds if any exceed the maximum
        if max_speed > self.max_speed_mm_s:
            scale = self.max_speed_mm_s / max_speed
            for i in range(4):
                self._motor_speeds[i] *= scale

        # Apply wheel speeds to the motors
        self._apply_motor_speeds()

    def reset_motors(self):
        """Stop all motors."""
        self._motor_speeds = [0.0, 0.0, 0.0, 0.0]
        self._apply_motor_speeds()
        logger.debug("All motors reset")

    def _apply_motor_speeds(self):
        """Apply the calculated motor speeds to the physical motors."""
        # Convert from mm/s to motor RPM
        rpms = []
        for speed in self._motor_speeds:
            if abs(speed) < 1e-6:
                rpms.append(0.0)
            else:
                # Convert from mm/s to RPM
                wheel_rps = speed / (2.0 * math.pi * self.wheel_radius)
                motor_rpm = wheel_rps * 60.0 * self.gear_ratio
                rpms.append(motor_rpm)

        # Log the applied RPMs
        logger.debug(f"Motor RPMs: {[round(rpm, 2) for rpm in rpms]}")

        # In a real implementation, this would apply the RPMs to the motors
        # For simulation, just log the values
        try:
            # This would set actual motor speeds in real hardware
            pass
        except Exception as e:
            logger.error(f"Failed to apply motor speeds: {e}")

    def get_motor_positions(self):
        """
        Get the current encoder positions of all motors.

        Returns:
            list: List of encoder positions [FL, FR, RL, RR].
        """
        # In a real implementation, this would read from encoders
        # For simulation, just return the stored positions
        return self._motor_positions

    def stop(self):
        """Stop the chassis and release motor resources."""
        self.reset_motors()
        logger.info("MecanumChassis stopped")
