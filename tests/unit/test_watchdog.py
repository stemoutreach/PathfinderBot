"""
Unit tests for the fault tolerance watchdog mechanisms.
"""

import pytest
import time
import threading
import logging
from unittest.mock import Mock, patch

from pathfinder_pkg.reliability.fault_tolerance.watchdog import (
    WatchdogState,
    Watchdog,
    ProcessWatchdog,
    ComponentWatchdogManager,
    get_component_watchdog_manager,
    register_component_watchdog,
    unregister_component_watchdog,
    reset_component_watchdog,
)


@pytest.fixture
def watchdog_callback():
    """Fixture that returns a mock callback function."""
    return Mock()


@pytest.fixture
def watchdog(watchdog_callback):
    """Fixture that returns a configured watchdog instance."""
    return Watchdog(timeout=0.1, callback=watchdog_callback, name="test_watchdog")


class TestWatchdog:
    """Tests for the Watchdog class."""

    def test_initialization(self, watchdog, watchdog_callback):
        """Test that the watchdog is initialized with the correct values."""
        assert watchdog.timeout == 0.1
        assert watchdog.callback == watchdog_callback
        assert watchdog.name == "test_watchdog"
        assert watchdog.state == WatchdogState.INACTIVE
        assert watchdog.last_reset == 0.0
        assert watchdog.thread is None

    def test_start_stop(self, watchdog):
        """Test starting and stopping the watchdog."""
        assert watchdog.state == WatchdogState.INACTIVE

        # Start the watchdog
        watchdog.start()
        assert watchdog.state == WatchdogState.ACTIVE
        assert watchdog.thread is not None
        assert watchdog.thread.is_alive()

        # Stop the watchdog
        watchdog.stop()
        assert watchdog.state == WatchdogState.INACTIVE
        assert not watchdog.thread.is_alive()

    def test_reset(self, watchdog):
        """Test resetting the watchdog timer."""
        # Start the watchdog
        watchdog.start()

        # Reset and check that the reset time is updated
        initial_reset = watchdog.last_reset
        time.sleep(0.05)  # Sleep a bit to ensure the reset time changes
        watchdog.reset()
        assert watchdog.last_reset > initial_reset

        # Stop the watchdog
        watchdog.stop()

    def test_trigger(self, watchdog, watchdog_callback):
        """Test that the watchdog triggers the callback when not reset in time."""
        # Start the watchdog
        watchdog.start()

        # Wait for the watchdog to trigger
        time.sleep(0.2)  # Longer than the timeout

        # Check that the callback was called
        watchdog_callback.assert_called_once()
        assert watchdog.state == WatchdogState.TRIGGERED

        # Verify that the thread has stopped
        assert not watchdog._stop_event.is_set()  # Event is cleared when thread exits

    def test_no_trigger_when_reset(self, watchdog, watchdog_callback):
        """Test that the watchdog does not trigger when reset regularly."""
        # Start the watchdog
        watchdog.start()

        # Reset the watchdog several times
        for _ in range(3):
            time.sleep(0.05)  # Less than the timeout
            watchdog.reset()

        # Wait a bit more to ensure the monitoring thread ran
        time.sleep(0.05)

        # Check that the callback was not called
        watchdog_callback.assert_not_called()
        assert watchdog.state == WatchdogState.ACTIVE

        # Stop the watchdog
        watchdog.stop()


@pytest.fixture
def process_watchdog():
    """Fixture that returns a configured process watchdog instance."""
    return ProcessWatchdog(
        process_name="test_process",
        restart_cmd="echo restarting",
        check_interval=0.1,
        max_restarts=2,
        restart_delay=0.01,
    )


class TestProcessWatchdog:
    """Tests for the ProcessWatchdog class."""

    def test_initialization(self, process_watchdog):
        """Test that the process watchdog is initialized with the correct values."""
        assert process_watchdog.process_name == "test_process"
        assert process_watchdog.restart_cmd == "echo restarting"
        assert process_watchdog.check_interval == 0.1
        assert process_watchdog.max_restarts == 2
        assert process_watchdog.restart_delay == 0.01
        assert process_watchdog.restarts == 0
        assert not process_watchdog.running

    @patch("psutil.process_iter")
    def test_is_process_running(self, mock_process_iter, process_watchdog):
        """Test checking if a process is running."""
        # Mock a process that matches by name
        mock_process1 = Mock()
        mock_process1.name.return_value = "test_process"
        mock_process1.cmdline.return_value = ["cmd1", "arg1"]

        # Mock a process that doesn't match
        mock_process2 = Mock()
        mock_process2.name.return_value = "other_process"
        mock_process2.cmdline.return_value = ["cmd2", "arg2"]

        # Return the mocked processes
        mock_process_iter.return_value = [mock_process1, mock_process2]

        # Check that the process is detected
        assert process_watchdog._is_process_running()

        # Change the first process to not match
        mock_process1.name.return_value = "other_process2"
        mock_process1.cmdline.return_value = ["test_process", "arg1"]

        # Check that the process is still detected (by command line)
        assert process_watchdog._is_process_running()

        # Change the first process to not match at all
        mock_process1.name.return_value = "other_process2"
        mock_process1.cmdline.return_value = ["cmd3", "arg3"]

        # Check that the process is not detected
        assert not process_watchdog._is_process_running()

    @patch("os.system")
    @patch("time.sleep")
    def test_restart_process(self, mock_sleep, mock_system, process_watchdog):
        """Test restarting a process."""
        # Mock successful restart
        mock_system.return_value = 0

        # Restart the process
        process_watchdog._restart_process()

        # Check that sleep was called for the restart delay
        mock_sleep.assert_called_once_with(0.01)

        # Check that system was called with the restart command
        mock_system.assert_called_once_with("echo restarting")

        # Check that the restart counter was incremented
        assert process_watchdog.restarts == 1

        # Restart again
        process_watchdog._restart_process()

        # Check that the restart counter was incremented again
        assert process_watchdog.restarts == 2

        # Restart a third time (should not actually restart since max_restarts=2)
        process_watchdog._restart_process()

        # Check that system was not called a third time
        assert mock_system.call_count == 2

    @patch(
        "pathfinder_pkg.reliability.fault_tolerance.watchdog.ProcessWatchdog._is_process_running"
    )
    @patch(
        "pathfinder_pkg.reliability.fault_tolerance.watchdog.ProcessWatchdog._restart_process"
    )
    def test_monitor(self, mock_restart, mock_is_running, process_watchdog):
        """Test the process monitoring function."""
        # Set up the mocks
        mock_is_running.side_effect = [False, True, False]

        # Start the process watchdog
        process_watchdog.start()

        # Wait for a few monitoring cycles
        time.sleep(0.25)

        # Stop the process watchdog
        process_watchdog.stop()

        # Check that the restart method was called when the process was not running
        assert mock_restart.call_count >= 2


@pytest.fixture
def component_watchdog_manager():
    """Fixture that returns a component watchdog manager."""
    return ComponentWatchdogManager(default_timeout=0.1)


class TestComponentWatchdogManager:
    """Tests for the ComponentWatchdogManager class."""

    def test_initialization(self, component_watchdog_manager):
        """Test that the manager is initialized with the correct values."""
        assert component_watchdog_manager.default_timeout == 0.1
        assert component_watchdog_manager.watchdogs == {}
        assert component_watchdog_manager.callbacks == {}

    def test_register_watchdog(self, component_watchdog_manager, watchdog_callback):
        """Test registering a watchdog."""
        # Register a watchdog
        watchdog = component_watchdog_manager.register_watchdog(
            component_name="test_component",
            callback=watchdog_callback,
            timeout=0.2,
        )

        # Check that the watchdog was registered
        assert "test_component" in component_watchdog_manager.watchdogs
        assert component_watchdog_manager.watchdogs["test_component"] == watchdog
        assert (
            component_watchdog_manager.callbacks["test_component"] == watchdog_callback
        )

        # Check that the watchdog was started
        assert watchdog.state == WatchdogState.ACTIVE

        # Register with a different timeout
        watchdog2 = component_watchdog_manager.register_watchdog(
            component_name="test_component2",
            callback=watchdog_callback,
            timeout=None,  # Use default timeout
        )

        # Check that the default timeout was used
        assert watchdog2.timeout == component_watchdog_manager.default_timeout

        # Clean up
        component_watchdog_manager.stop_all()

    def test_unregister_watchdog(self, component_watchdog_manager, watchdog_callback):
        """Test unregistering a watchdog."""
        # Register a watchdog
        watchdog = component_watchdog_manager.register_watchdog(
            component_name="test_component",
            callback=watchdog_callback,
        )

        # Check that the watchdog is registered
        assert "test_component" in component_watchdog_manager.watchdogs

        # Unregister the watchdog
        component_watchdog_manager.unregister_watchdog("test_component")

        # Check that the watchdog was unregistered
        assert "test_component" not in component_watchdog_manager.watchdogs
        assert "test_component" not in component_watchdog_manager.callbacks

        # Verify that the watchdog was stopped
        assert watchdog.state == WatchdogState.INACTIVE

    def test_reset_watchdog(self, component_watchdog_manager, watchdog_callback):
        """Test resetting a watchdog."""
        # Register a watchdog
        watchdog = component_watchdog_manager.register_watchdog(
            component_name="test_component",
            callback=watchdog_callback,
        )

        # Reset the watchdog
        initial_reset = watchdog.last_reset
        time.sleep(0.05)  # Sleep a bit to ensure the reset time changes
        result = component_watchdog_manager.reset_watchdog("test_component")

        # Check that reset was successful
        assert result is True
        assert watchdog.last_reset > initial_reset

        # Try to reset a non-existent watchdog
        result = component_watchdog_manager.reset_watchdog("non_existent")

        # Check that reset failed
        assert result is False

        # Clean up
        component_watchdog_manager.stop_all()

    def test_start_all_stop_all(self, component_watchdog_manager, watchdog_callback):
        """Test starting and stopping all watchdogs."""
        # Register some watchdogs
        watchdog1 = component_watchdog_manager.register_watchdog(
            component_name="component1",
            callback=watchdog_callback,
            auto_start=False,  # Don't auto-start
        )

        watchdog2 = component_watchdog_manager.register_watchdog(
            component_name="component2",
            callback=watchdog_callback,
            auto_start=False,  # Don't auto-start
        )

        # Check that watchdogs are inactive
        assert watchdog1.state == WatchdogState.INACTIVE
        assert watchdog2.state == WatchdogState.INACTIVE

        # Start all watchdogs
        component_watchdog_manager.start_all()

        # Check that watchdogs are active
        assert watchdog1.state == WatchdogState.ACTIVE
        assert watchdog2.state == WatchdogState.ACTIVE

        # Stop all watchdogs
        component_watchdog_manager.stop_all()

        # Check that watchdogs are inactive
        assert watchdog1.state == WatchdogState.INACTIVE
        assert watchdog2.state == WatchdogState.INACTIVE


class TestGlobalWatchdogFunctions:
    """Tests for the global watchdog functions."""

    def test_get_component_watchdog_manager(self):
        """Test getting the global component watchdog manager."""
        manager = get_component_watchdog_manager()
        assert isinstance(manager, ComponentWatchdogManager)

        # Check that it returns the same instance
        manager2 = get_component_watchdog_manager()
        assert manager is manager2

    def test_register_component_watchdog(self, watchdog_callback):
        """Test registering a component watchdog using the global function."""
        # Clear any existing watchdogs
        manager = get_component_watchdog_manager()
        manager.watchdogs.clear()

        # Register a watchdog
        watchdog = register_component_watchdog(
            component_name="test_global",
            callback=watchdog_callback,
            timeout=0.2,
        )

        # Check that the watchdog was registered
        assert "test_global" in manager.watchdogs
        assert manager.watchdogs["test_global"] == watchdog

        # Clean up
        unregister_component_watchdog("test_global")

    def test_unregister_component_watchdog(self, watchdog_callback):
        """Test unregistering a component watchdog using the global function."""
        # Register a watchdog
        watchdog = register_component_watchdog(
            component_name="test_global",
            callback=watchdog_callback,
        )

        # Check that the watchdog is registered
        manager = get_component_watchdog_manager()
        assert "test_global" in manager.watchdogs

        # Unregister the watchdog
        unregister_component_watchdog("test_global")

        # Check that the watchdog was unregistered
        assert "test_global" not in manager.watchdogs

    def test_reset_component_watchdog(self, watchdog_callback):
        """Test resetting a component watchdog using the global function."""
        # Register a watchdog
        watchdog = register_component_watchdog(
            component_name="test_global",
            callback=watchdog_callback,
        )

        # Reset the watchdog
        initial_reset = watchdog.last_reset
        time.sleep(0.05)  # Sleep a bit to ensure the reset time changes
        result = reset_component_watchdog("test_global")

        # Check that reset was successful
        assert result is True
        assert watchdog.last_reset > initial_reset

        # Clean up
        unregister_component_watchdog("test_global")
