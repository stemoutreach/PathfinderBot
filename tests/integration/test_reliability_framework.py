"""
Integration tests for the reliability and diagnostics framework.

This test suite verifies that the various components of the reliability
and diagnostics framework work together correctly.
"""

import pytest
import time
import os
import threading
import logging
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

from pathfinder_pkg.reliability.error_handling.errors import (
    PathfinderError,
    SoftwareError,
    register_error,
    get_error_registry,
    register_handler,
)
from pathfinder_pkg.reliability.fault_tolerance.watchdog import (
    Watchdog,
    register_component_watchdog,
    reset_component_watchdog,
    unregister_component_watchdog,
)
from pathfinder_pkg.reliability.resource_management.resource_monitor import (
    ResourceThresholds,
    start_resource_monitoring,
    stop_resource_monitoring,
    register_resource_threshold_handler,
)
from pathfinder_pkg.diagnostics.telemetry.telemetry_collector import (
    start_telemetry_collection,
    stop_telemetry_collection,
    record_telemetry,
    register_telemetry_collector,
)
from pathfinder_pkg.diagnostics.debugging.debugger import (
    debug_context,
    hit_breakpoint,
    set_breakpoint,
    call_tracer,
    record_state,
    dump_threads,
)


@pytest.fixture(scope="module", autouse=True)
def setup_logging():
    """Set up logging for the tests."""
    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )
    yield


class TestReliabilityIntegration:
    """Integration tests for the reliability framework."""

    def test_error_handling_with_telemetry(self):
        """
        Test that errors are properly registered and telemetry is recorded.

        This test verifies that:
        1. Errors can be registered
        2. Error handlers are called
        3. Telemetry is recorded for errors
        """
        # Set up
        error_handler_called = False
        error_data = {}

        # Start telemetry collection
        start_telemetry_collection()

        try:
            # Register an error handler that records telemetry
            def error_handler(error):
                nonlocal error_handler_called, error_data
                error_handler_called = True
                error_data = {
                    "message": error.message,
                    "severity": error.severity.name,
                    "category": error.category.name,
                }
                # Record error in telemetry
                record_telemetry(
                    metric_name="error.occurred",
                    value=1,
                    source="test",
                    tags={
                        "error_type": error.__class__.__name__,
                        "severity": error.severity.name,
                        "category": error.category.name,
                    },
                )

            handler_id = register_handler(SoftwareError, error_handler)

            # Create and register an error
            error = SoftwareError("Test software error")
            register_error(error)

            # Check that the handler was called
            assert error_handler_called
            assert error_data["message"] == "Test software error"
            assert error_data["category"] == "SOFTWARE"

            # Sleep briefly to allow telemetry collection
            time.sleep(0.1)

            # Check the error registry
            registry = get_error_registry()
            assert error in registry.errors

        finally:
            # Stop telemetry collection
            stop_telemetry_collection()

    def test_watchdog_with_resource_monitoring(self):
        """
        Test that watchdogs and resource monitoring work together.

        This test verifies that:
        1. Watchdogs can detect component failures
        2. Resource monitoring can track system resources
        3. Resource threshold events can trigger watchdog resets
        """
        # Set up
        watchdog_triggered = False
        resource_alert_triggered = False
        test_component_alive = True

        # Start resource monitoring with test thresholds
        thresholds = ResourceThresholds(
            cpu_percent=10.0,  # Low threshold to ensure triggering
            memory_percent=90.0,
            disk_percent=90.0,
        )
        start_resource_monitoring(thresholds=thresholds)

        try:
            # Define watchdog callback
            def watchdog_callback():
                nonlocal watchdog_triggered
                watchdog_triggered = True
                logging.info("Watchdog triggered for test_component")

            # Register a component watchdog
            register_component_watchdog(
                component_name="test_component",
                callback=watchdog_callback,
                timeout=0.2,
            )

            # Reset the watchdog initially
            reset_component_watchdog("test_component")

            # Define resource threshold handler
            def resource_handler(resource_type, usage_value, threshold):
                nonlocal resource_alert_triggered, test_component_alive
                resource_alert_triggered = True
                logging.info(
                    f"Resource alert: {resource_type} at {usage_value}% "
                    f"(threshold: {threshold}%)"
                )

                # Only reset the watchdog if the component is "alive"
                if test_component_alive:
                    reset_component_watchdog("test_component")

                # Record telemetry
                record_telemetry(
                    metric_name=f"resource.alert.{resource_type}",
                    value=usage_value,
                    source="test",
                    tags={"threshold": str(threshold)},
                )

            # Register resource handler
            handler_id = register_resource_threshold_handler(resource_handler)

            # Reset the watchdog to keep it alive initially
            reset_component_watchdog("test_component")

            # Sleep to allow resource monitoring to trigger the handler
            time.sleep(0.3)

            # The resource handler should have reset the watchdog, so it shouldn't trigger
            assert not watchdog_triggered
            assert resource_alert_triggered

            # Now simulate component failure
            test_component_alive = False

            # Wait for the watchdog to trigger
            time.sleep(0.3)

            # Check that the watchdog was triggered due to missed resets
            assert watchdog_triggered

        finally:
            # Clean up
            unregister_component_watchdog("test_component")
            stop_resource_monitoring()

    def test_debugging_with_telemetry(self):
        """
        Test that debugging tools work with telemetry.

        This test verifies that:
        1. Debug contexts can record execution information
        2. Breakpoints can be set and triggered
        3. State recording works
        4. Call tracing works
        5. All debug information can be recorded as telemetry
        """
        # Start telemetry collection
        start_telemetry_collection()

        try:
            # Register a telemetry collector for debug information
            def debug_collector():
                return {
                    "active_breakpoints": len(set_breakpoint.breakpoints.keys()),
                    "thread_count": threading.active_count(),
                }

            register_telemetry_collector("debug_info", debug_collector)

            # Test debug context
            with debug_context("test_debug_operation") as ctx:
                # Perform some operations
                result = 0
                for i in range(10000):
                    result += i

                # Record state of operation
                record_state("debug_operation.result", result)

            # Test breakpoints
            breakpoint_triggered = False

            def breakpoint_callback(bp):
                nonlocal breakpoint_triggered
                breakpoint_triggered = True
                # Record telemetry when breakpoint is hit
                record_telemetry(
                    metric_name="debug.breakpoint.hit",
                    value=1,
                    source="test",
                    tags={"breakpoint_name": bp.name},
                )

            # Set a breakpoint
            set_breakpoint("test_breakpoint", callback=breakpoint_callback)

            # Trigger the breakpoint
            hit_breakpoint("test_breakpoint")

            # Check that the breakpoint was triggered
            assert breakpoint_triggered

            # Test call tracing
            call_tracer.start()

            @call_tracer
            def traced_function(x, y):
                return x + y

            result = traced_function(10, 20)
            assert result == 30

            call_tracer.stop()

            # Get thread dump for telemetry
            thread_dumps = dump_threads()
            record_telemetry(
                metric_name="debug.thread_dump",
                value={"thread_count": len(thread_dumps)},
                source="test",
            )

            # Sleep briefly to allow telemetry collection to run
            time.sleep(0.1)

        finally:
            # Stop telemetry collection
            stop_telemetry_collection()

    def test_comprehensive_reliability_framework(self):
        """
        Test the complete reliability framework working together.

        This test verifies that all components of the reliability and
        diagnostics framework can work together in a realistic scenario.
        """
        # Create a temporary directory for test files
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            test_file = temp_path / "test_data.txt"

            # Start all monitoring systems
            start_telemetry_collection()
            start_resource_monitoring()

            try:
                # Set up debug context for the whole test
                with debug_context("comprehensive_test", capture_vars=True):
                    # Set a test breakpoint
                    set_breakpoint("critical_operation")

                    # Simulate component activity with watchdog
                    def component_activity():
                        # Create a file to simulate work
                        with open(test_file, "w") as f:
                            f.write("Test data")

                        # Record telemetry about the operation
                        record_telemetry(
                            metric_name="component.operation",
                            value=1,
                            source="test_component",
                            tags={"operation": "file_write"},
                        )

                        # Record state for debugging
                        record_state("component.file_written", str(test_file))

                        # Signal critical operation
                        hit_breakpoint("critical_operation")

                        # Read the file back
                        try:
                            with open(test_file, "r") as f:
                                content = f.read()

                            # Record telemetry for successful read
                            record_telemetry(
                                metric_name="component.operation",
                                value=1,
                                source="test_component",
                                tags={"operation": "file_read"},
                            )

                        except Exception as e:
                            # Register error if read fails
                            error = SoftwareError(
                                f"Failed to read test file: {e}",
                                details={"file": str(test_file)},
                                cause=e,
                            )
                            register_error(error)

                    # Register a component watchdog
                    register_component_watchdog(
                        component_name="test_component",
                        callback=lambda: register_error(
                            SoftwareError("Component watchdog triggered")
                        ),
                        timeout=0.5,
                    )

                    # Perform the component activity
                    component_activity()

                    # Reset the watchdog to indicate the component is healthy
                    reset_component_watchdog("test_component")

                    # Verify the file was created
                    assert test_file.exists()

                    # Simulate resource threshold monitoring
                    def resource_threshold_handler(resource_type, usage, threshold):
                        record_telemetry(
                            metric_name=f"resource.threshold.{resource_type}",
                            value=usage,
                            source="system",
                            tags={
                                "threshold": str(threshold),
                                "exceeded": "true" if usage > threshold else "false",
                            },
                        )

                        # Log the event
                        logging.warning(
                            f"Resource {resource_type} at {usage}% "
                            f"(threshold: {threshold}%)"
                        )

                    # Register the resource handler
                    register_resource_threshold_handler(resource_threshold_handler)

                    # Sleep to allow all monitoring to run
                    time.sleep(0.3)

            finally:
                # Stop all monitoring systems
                stop_telemetry_collection()
                stop_resource_monitoring()


class TestErrorRecovery:
    """Integration tests for error recovery scenarios."""

    def test_error_recovery_flow(self):
        """
        Test the full error recovery flow.

        This test simulates a complete error detection, reporting, and recovery flow:
        1. Component fails (watchdog triggers)
        2. Error is registered
        3. Recovery is attempted
        4. Telemetry is recorded
        5. System is restored to normal operation
        """
        # Set up tracking variables
        error_detected = False
        recovery_attempted = False
        component_restarted = False

        # Start telemetry
        start_telemetry_collection()

        try:
            # Define component health check function
            def component_health_check():
                # Simulate a failing component
                return False

            # Define error handler
            def error_handler(error):
                nonlocal error_detected
                error_detected = True
                logging.error(f"Error detected: {error.message}")

                # Record telemetry
                record_telemetry(
                    metric_name="error.detected",
                    value=1,
                    source="test",
                    tags={
                        "error_type": error.__class__.__name__,
                        "severity": error.severity.name,
                    },
                )

                # Attempt recovery
                from pathfinder_pkg.reliability.error_handling.errors import (
                    attempt_recovery,
                )

                attempt_recovery(error)

            # Register error handler
            register_handler(PathfinderError, error_handler)

            # Define recovery handler
            def recovery_handler(error):
                nonlocal recovery_attempted, component_restarted
                recovery_attempted = True

                logging.info(f"Attempting recovery for error: {error.message}")

                # Record telemetry
                record_telemetry(
                    metric_name="error.recovery.attempted",
                    value=1,
                    source="test",
                    tags={"error_type": error.__class__.__name__},
                )

                # Simulate component restart
                time.sleep(0.1)
                component_restarted = True

                # Record telemetry for recovery result
                record_telemetry(
                    metric_name="error.recovery.result",
                    value=1,
                    source="test",
                    tags={"result": "success"},
                )

                return True

            # Register recovery handler
            from pathfinder_pkg.reliability.error_handling.errors import (
                register_recovery_handler,
            )

            register_recovery_handler(PathfinderError, recovery_handler)

            # Define watchdog callback
            def watchdog_callback():
                # Create and register an error
                error = SoftwareError(
                    "Component failed to respond",
                    details={"component": "test_component"},
                )
                register_error(error)

            # Register component watchdog
            register_component_watchdog(
                component_name="test_component",
                callback=watchdog_callback,
                timeout=0.1,
            )

            # Let the watchdog trigger (don't reset it)
            time.sleep(0.2)

            # Verify the error recovery flow
            assert error_detected, "Error should have been detected"
            assert recovery_attempted, "Recovery should have been attempted"
            assert component_restarted, "Component should have been restarted"

        finally:
            # Clean up
            unregister_component_watchdog("test_component")
            stop_telemetry_collection()


if __name__ == "__main__":
    # This allows running the tests directly with python
    pytest.main(["-v", __file__])
