"""
Unit tests for the error handling module.
"""

import os
import pytest
import time
import logging
from pathlib import Path

from pathfinder_pkg.reliability.error_handling.errors import (
    ErrorSeverity,
    ErrorCategory,
    PathfinderError,
    HardwareError,
    SensorError,
    ActuatorError,
    CommunicationError,
    SoftwareError,
    ConfigurationError,
    get_error_registry,
    register_error,
    register_handler,
    register_recovery_handler,
    attempt_recovery,
    ok,
    err,
    safe_call,
)


def test_error_creation():
    """Test that errors can be created with the correct attributes."""
    # Create a basic error
    error = PathfinderError("Test error")
    assert error.message == "Test error"
    assert error.severity == ErrorSeverity.MEDIUM
    assert error.category == ErrorCategory.UNKNOWN
    assert not error.details
    assert error.cause is None

    # Create an error with custom attributes
    cause = ValueError("Original error")
    error = PathfinderError(
        message="Custom error",
        severity=ErrorSeverity.HIGH,
        category=ErrorCategory.HARDWARE,
        details={"device": "sensor"},
        cause=cause,
    )
    assert error.message == "Custom error"
    assert error.severity == ErrorSeverity.HIGH
    assert error.category == ErrorCategory.HARDWARE
    assert error.details == {"device": "sensor"}
    assert error.cause == cause


def test_error_registry():
    """Test that errors are properly registered and can be retrieved."""
    # Get the registry
    registry = get_error_registry()

    # Clear the registry first to ensure a clean state
    registry.errors.clear()

    # Create and register some errors
    error1 = HardwareError("Hardware failure")
    error2 = SensorError("Sensor failure", sensor_id="sensor1")

    register_error(error1)
    register_error(error2)

    # Check that the errors were registered
    assert len(registry.errors) == 2
    assert registry.errors[0] == error1
    assert registry.errors[1] == error2

    # Check error severity filtering
    high_errors = registry.get_errors_by_severity(ErrorSeverity.HIGH)
    assert len(high_errors) == 1
    assert high_errors[0] == error1

    # Check error category filtering
    sensor_errors = registry.get_errors_by_category(ErrorCategory.SENSOR)
    assert len(sensor_errors) == 1
    assert sensor_errors[0] == error2

    # Check statistics
    stats = registry.get_error_statistics()
    assert stats["total_errors"] == 2
    assert stats["by_severity"][ErrorSeverity.HIGH.name] == 1
    assert stats["by_category"][ErrorCategory.HARDWARE.name] == 1
    assert stats["by_category"][ErrorCategory.SENSOR.name] == 1


def test_error_handlers():
    """Test that error handlers are properly called when errors are registered."""
    # Get the registry
    registry = get_error_registry()

    # Clear the registry and handlers first
    registry.errors.clear()
    registry.error_handlers.clear()

    # Create a list to track handler calls
    handler_calls = []

    # Define a handler function
    def test_handler(error):
        handler_calls.append(error)

    # Register the handler for HardwareError
    handler_id = register_handler(HardwareError, test_handler)

    # Register some errors
    error1 = HardwareError("Hardware failure")
    error2 = SensorError("Sensor failure", sensor_id="sensor1")

    register_error(error1)  # Should trigger the handler
    register_error(error2)  # Should not trigger the handler

    # Check that the handler was called for the HardwareError only
    assert len(handler_calls) == 1
    assert handler_calls[0] == error1


def test_error_recovery():
    """Test that recovery handlers are properly called when recovery is attempted."""
    # Get the registry
    registry = get_error_registry()

    # Clear the registry and handlers first
    registry.errors.clear()
    registry.recovery_handlers.clear()

    # Define recovery handlers
    def successful_recovery(error):
        return True

    def failed_recovery(error):
        return False

    # Register the recovery handlers
    register_recovery_handler(HardwareError, failed_recovery)
    register_recovery_handler(SensorError, successful_recovery)

    # Create some errors
    error1 = HardwareError("Hardware failure")
    error2 = SensorError("Sensor failure", sensor_id="sensor1")

    # Attempt recovery
    result1 = attempt_recovery(error1)  # Should fail
    result2 = attempt_recovery(error2)  # Should succeed

    # Check the results
    assert result1 is False
    assert result2 is True


def test_result_functions():
    """Test the ok and err functions for creating result tuples."""
    # Test ok function
    value, error = ok(42)
    assert value == 42
    assert error is None

    # Test err function
    error = PathfinderError("Test error")
    value, returned_error = err(error)
    assert value is None
    assert returned_error is error

    # Check that the error was registered
    registry = get_error_registry()
    assert error in registry.errors


def test_safe_call():
    """Test the safe_call function for handling exceptions."""

    # Define test functions
    def successful_function():
        return 42

    def failing_function():
        raise ValueError("Test exception")

    def pathfinder_error_function():
        raise PathfinderError("Test error")

    # Test successful call
    result = safe_call(successful_function)
    assert result == 42

    # Test call with regular exception
    result = safe_call(failing_function)
    assert result is None

    # Test call with PathfinderError
    result = safe_call(pathfinder_error_function)
    assert result is None

    # Check that errors were registered
    registry = get_error_registry()
    assert len(registry.errors) >= 2  # At least 2 new errors


def test_error_inheritance():
    """Test that error subclasses properly inherit from PathfinderError."""
    # Create errors of different types
    hw_error = HardwareError("Hardware failure")
    sensor_error = SensorError("Sensor failure", sensor_id="sensor1")
    actuator_error = ActuatorError("Actuator failure", actuator_id="actuator1")
    comm_error = CommunicationError("Communication failure")
    sw_error = SoftwareError("Software failure")
    config_error = ConfigurationError("Configuration failure", config_key="config1")

    # Check inheritance
    assert isinstance(hw_error, PathfinderError)
    assert isinstance(sensor_error, PathfinderError)
    assert isinstance(actuator_error, PathfinderError)
    assert isinstance(comm_error, PathfinderError)
    assert isinstance(sw_error, PathfinderError)
    assert isinstance(config_error, PathfinderError)

    # Check categories
    assert hw_error.category == ErrorCategory.HARDWARE
    assert sensor_error.category == ErrorCategory.SENSOR
    assert actuator_error.category == ErrorCategory.ACTUATOR
    assert comm_error.category == ErrorCategory.COMMUNICATION
    assert sw_error.category == ErrorCategory.SOFTWARE
    assert config_error.category == ErrorCategory.CONFIGURATION
