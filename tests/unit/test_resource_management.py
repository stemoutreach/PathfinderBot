"""
Unit tests for the resource management module.
"""

import pytest
import time
import os
import psutil
import threading
import tempfile
from unittest.mock import Mock, patch

from pathfinder_pkg.reliability.resource_management.resource_monitor import (
    ResourceUsage,
    ResourceThresholds,
    ResourceMonitor,
    register_resource_threshold_handler,
    unregister_resource_threshold_handler,
    get_resource_monitor,
    start_resource_monitoring,
    stop_resource_monitoring,
)


class TestResourceUsage:
    """Tests for the ResourceUsage class."""

    def test_initialization(self):
        """Test that the resource usage is initialized with the correct values."""
        # Create a basic resource usage object
        usage = ResourceUsage(
            cpu_percent=50.0,
            memory_percent=60.0,
            disk_percent=70.0,
            network_bytes_sent=1000,
            network_bytes_recv=2000,
            timestamp=12345.0,
        )

        assert usage.cpu_percent == 50.0
        assert usage.memory_percent == 60.0
        assert usage.disk_percent == 70.0
        assert usage.network_bytes_sent == 1000
        assert usage.network_bytes_recv == 2000
        assert usage.timestamp == 12345.0

    def test_to_dict(self):
        """Test converting a resource usage to a dictionary."""
        # Create a resource usage object
        usage = ResourceUsage(
            cpu_percent=50.0,
            memory_percent=60.0,
            disk_percent=70.0,
            network_bytes_sent=1000,
            network_bytes_recv=2000,
            timestamp=12345.0,
        )

        # Convert to dictionary
        data = usage.to_dict()

        # Check dictionary contents
        assert data["cpu_percent"] == 50.0
        assert data["memory_percent"] == 60.0
        assert data["disk_percent"] == 70.0
        assert data["network_bytes_sent"] == 1000
        assert data["network_bytes_recv"] == 2000
        assert data["timestamp"] == 12345.0


class TestResourceThresholds:
    """Tests for the ResourceThresholds class."""

    def test_initialization(self):
        """Test that the resource thresholds are initialized with the correct values."""
        # Create a basic resource thresholds object
        thresholds = ResourceThresholds(
            cpu_percent=80.0,
            memory_percent=90.0,
            disk_percent=95.0,
        )

        assert thresholds.cpu_percent == 80.0
        assert thresholds.memory_percent == 90.0
        assert thresholds.disk_percent == 95.0

    def test_check_thresholds_all_below(self):
        """Test checking thresholds when all usage is below thresholds."""
        # Create thresholds
        thresholds = ResourceThresholds(
            cpu_percent=80.0,
            memory_percent=90.0,
            disk_percent=95.0,
        )

        # Create a usage that is below all thresholds
        usage = ResourceUsage(
            cpu_percent=70.0,
            memory_percent=80.0,
            disk_percent=85.0,
            network_bytes_sent=1000,
            network_bytes_recv=2000,
            timestamp=12345.0,
        )

        # Check thresholds
        exceeded = thresholds.check_thresholds(usage)

        # Check that no thresholds were exceeded
        assert not exceeded["cpu_percent"]
        assert not exceeded["memory_percent"]
        assert not exceeded["disk_percent"]

    def test_check_thresholds_some_exceeded(self):
        """Test checking thresholds when some usage exceeds thresholds."""
        # Create thresholds
        thresholds = ResourceThresholds(
            cpu_percent=80.0,
            memory_percent=90.0,
            disk_percent=95.0,
        )

        # Create a usage that exceeds some thresholds
        usage = ResourceUsage(
            cpu_percent=85.0,  # Exceeds
            memory_percent=80.0,  # Below
            disk_percent=97.0,  # Exceeds
            network_bytes_sent=1000,
            network_bytes_recv=2000,
            timestamp=12345.0,
        )

        # Check thresholds
        exceeded = thresholds.check_thresholds(usage)

        # Check which thresholds were exceeded
        assert exceeded["cpu_percent"]
        assert not exceeded["memory_percent"]
        assert exceeded["disk_percent"]

    def test_check_thresholds_all_exceeded(self):
        """Test checking thresholds when all usage exceeds thresholds."""
        # Create thresholds
        thresholds = ResourceThresholds(
            cpu_percent=80.0,
            memory_percent=90.0,
            disk_percent=95.0,
        )

        # Create a usage that exceeds all thresholds
        usage = ResourceUsage(
            cpu_percent=85.0,
            memory_percent=95.0,
            disk_percent=99.0,
            network_bytes_sent=1000,
            network_bytes_recv=2000,
            timestamp=12345.0,
        )

        # Check thresholds
        exceeded = thresholds.check_thresholds(usage)

        # Check that all thresholds were exceeded
        assert exceeded["cpu_percent"]
        assert exceeded["memory_percent"]
        assert exceeded["disk_percent"]


@pytest.fixture
def resource_monitor():
    """Fixture that provides a configured resource monitor."""
    thresholds = ResourceThresholds(
        cpu_percent=80.0,
        memory_percent=90.0,
        disk_percent=95.0,
    )

    monitor = ResourceMonitor(
        thresholds=thresholds,
        monitoring_interval=0.1,
        max_history=10,
    )

    yield monitor

    # Stop the monitor if it's running
    if monitor.running:
        monitor.stop()


@patch("psutil.cpu_percent")
@patch("psutil.virtual_memory")
@patch("psutil.disk_usage")
@patch("psutil.net_io_counters")
class TestResourceMonitor:
    """Tests for the ResourceMonitor class."""

    def test_initialization(
        self, mock_net, mock_disk, mock_mem, mock_cpu, resource_monitor
    ):
        """Test that the resource monitor is initialized with the correct values."""
        assert resource_monitor.thresholds.cpu_percent == 80.0
        assert resource_monitor.thresholds.memory_percent == 90.0
        assert resource_monitor.thresholds.disk_percent == 95.0
        assert resource_monitor.monitoring_interval == 0.1
        assert resource_monitor.max_history == 10
        assert resource_monitor.history == []
        assert resource_monitor.running is False
        assert resource_monitor.handlers == {}

    def test_collect_resource_usage(
        self, mock_net, mock_disk, mock_mem, mock_cpu, resource_monitor
    ):
        """Test collecting resource usage."""
        # Mock system resource functions
        mock_cpu.return_value = 50.0

        mem_mock = Mock()
        mem_mock.percent = 60.0
        mock_mem.return_value = mem_mock

        disk_mock = Mock()
        disk_mock.percent = 70.0
        mock_disk.return_value = disk_mock

        net_mock = Mock()
        net_mock.bytes_sent = 1000
        net_mock.bytes_recv = 2000
        mock_net.return_value = net_mock

        # Collect usage
        usage = resource_monitor._collect_resource_usage()

        # Check usage values
        assert usage.cpu_percent == 50.0
        assert usage.memory_percent == 60.0
        assert usage.disk_percent == 70.0
        assert usage.network_bytes_sent == 1000
        assert usage.network_bytes_recv == 2000
        assert usage.timestamp > 0

    def test_start_stop(
        self, mock_net, mock_disk, mock_mem, mock_cpu, resource_monitor
    ):
        """Test starting and stopping the monitor."""
        # Start the monitor
        resource_monitor.start()

        # Check that the monitor is running
        assert resource_monitor.running
        assert resource_monitor.monitoring_thread is not None
        assert resource_monitor.monitoring_thread.is_alive()

        # Stop the monitor
        resource_monitor.stop()

        # Check that the monitor is stopped
        assert not resource_monitor.running
        assert (
            resource_monitor.monitoring_thread is None
            or not resource_monitor.monitoring_thread.is_alive()
        )

    def test_monitor_resources(
        self, mock_net, mock_disk, mock_mem, mock_cpu, resource_monitor
    ):
        """Test monitoring resources and recording history."""
        # Mock system resource functions
        mock_cpu.return_value = 50.0

        mem_mock = Mock()
        mem_mock.percent = 60.0
        mock_mem.return_value = mem_mock

        disk_mock = Mock()
        disk_mock.percent = 70.0
        mock_disk.return_value = disk_mock

        net_mock = Mock()
        net_mock.bytes_sent = 1000
        net_mock.bytes_recv = 2000
        mock_net.return_value = net_mock

        # Start the monitor
        resource_monitor.start()

        # Wait for some history to accumulate
        time.sleep(0.25)  # Wait for at least 2 monitoring cycles

        # Stop the monitor
        resource_monitor.stop()

        # Check that history was recorded
        assert len(resource_monitor.history) > 0

        # Check the latest history entry
        latest = resource_monitor.history[-1]
        assert latest.cpu_percent == 50.0
        assert latest.memory_percent == 60.0
        assert latest.disk_percent == 70.0

    def test_register_handler(
        self, mock_net, mock_disk, mock_mem, mock_cpu, resource_monitor
    ):
        """Test registering threshold handlers."""
        # Create a handler function
        handler_calls = []

        def test_handler(resource_type, usage_value, threshold):
            handler_calls.append((resource_type, usage_value, threshold))

        # Register the handler
        handler_id = resource_monitor.register_handler(test_handler)

        # Check that the handler was registered
        assert handler_id in resource_monitor.handlers
        assert resource_monitor.handlers[handler_id] == test_handler

        # Test triggering the handler
        mock_cpu.return_value = 90.0  # Exceeds threshold

        mem_mock = Mock()
        mem_mock.percent = 60.0
        mock_mem.return_value = mem_mock

        disk_mock = Mock()
        disk_mock.percent = 70.0
        mock_disk.return_value = disk_mock

        net_mock = Mock()
        net_mock.bytes_sent = 1000
        net_mock.bytes_recv = 2000
        mock_net.return_value = net_mock

        # Manually check thresholds
        usage = resource_monitor._collect_resource_usage()
        resource_monitor._check_thresholds(usage)

        # Check that the handler was called
        assert len(handler_calls) == 1
        assert handler_calls[0][0] == "cpu_percent"
        assert handler_calls[0][1] == 90.0
        assert handler_calls[0][2] == 80.0

    def test_unregister_handler(
        self, mock_net, mock_disk, mock_mem, mock_cpu, resource_monitor
    ):
        """Test unregistering threshold handlers."""
        # Create a handler function
        handler_calls = []

        def test_handler(resource_type, usage_value, threshold):
            handler_calls.append((resource_type, usage_value, threshold))

        # Register the handler
        handler_id = resource_monitor.register_handler(test_handler)

        # Unregister the handler
        resource_monitor.unregister_handler(handler_id)

        # Check that the handler was unregistered
        assert handler_id not in resource_monitor.handlers

        # Test that the handler is not called
        mock_cpu.return_value = 90.0  # Exceeds threshold

        mem_mock = Mock()
        mem_mock.percent = 60.0
        mock_mem.return_value = mem_mock

        disk_mock = Mock()
        disk_mock.percent = 70.0
        mock_disk.return_value = disk_mock

        net_mock = Mock()
        net_mock.bytes_sent = 1000
        net_mock.bytes_recv = 2000
        mock_net.return_value = net_mock

        # Manually check thresholds
        usage = resource_monitor._collect_resource_usage()
        resource_monitor._check_thresholds(usage)

        # Check that the handler was not called
        assert len(handler_calls) == 0

    def test_max_history(self, mock_net, mock_disk, mock_mem, mock_cpu):
        """Test that the history is limited to max_history entries."""
        # Create a monitor with a small max_history
        thresholds = ResourceThresholds(
            cpu_percent=80.0,
            memory_percent=90.0,
            disk_percent=95.0,
        )

        monitor = ResourceMonitor(
            thresholds=thresholds,
            monitoring_interval=0.01,
            max_history=3,
        )

        try:
            # Mock system resource functions
            mock_cpu.return_value = 50.0

            mem_mock = Mock()
            mem_mock.percent = 60.0
            mock_mem.return_value = mem_mock

            disk_mock = Mock()
            disk_mock.percent = 70.0
            mock_disk.return_value = disk_mock

            net_mock = Mock()
            net_mock.bytes_sent = 1000
            net_mock.bytes_recv = 2000
            mock_net.return_value = net_mock

            # Start the monitor
            monitor.start()

            # Wait for history to accumulate beyond max_history
            time.sleep(0.1)  # Should collect more than 3 entries

            # Stop the monitor
            monitor.stop()

            # Check that history is limited to max_history
            assert len(monitor.history) == 3
        finally:
            # Ensure the monitor is stopped
            if monitor.running:
                monitor.stop()


@patch(
    "pathfinder_pkg.reliability.resource_management.resource_monitor.ResourceMonitor"
)
class TestGlobalResourceFunctions:
    """Tests for the global resource monitoring functions."""

    def test_get_resource_monitor(self, mock_resource_monitor):
        """Test getting the global resource monitor."""
        # Set up the mock
        mock_instance = Mock()
        mock_resource_monitor.return_value = mock_instance

        # First call should create a new instance
        monitor1 = get_resource_monitor()
        assert monitor1 == mock_instance
        mock_resource_monitor.assert_called_once()

        # Second call should return the same instance
        monitor2 = get_resource_monitor()
        assert monitor2 == mock_instance
        assert mock_resource_monitor.call_count == 1

    def test_start_stop_resource_monitoring(self, mock_resource_monitor):
        """Test starting and stopping resource monitoring."""
        # Set up the mock
        mock_instance = Mock()
        mock_resource_monitor.return_value = mock_instance

        # Start monitoring
        start_resource_monitoring()

        # Check that the monitor was started
        mock_instance.start.assert_called_once()

        # Stop monitoring
        stop_resource_monitoring()

        # Check that the monitor was stopped
        mock_instance.stop.assert_called_once()

    def test_register_unregister_resource_threshold_handler(
        self, mock_resource_monitor
    ):
        """Test registering and unregistering threshold handlers."""
        # Set up the mock
        mock_instance = Mock()
        mock_instance.register_handler.return_value = "test-handler-id"
        mock_resource_monitor.return_value = mock_instance

        # Create a handler function
        def test_handler(resource_type, usage_value, threshold):
            pass

        # Register the handler
        handler_id = register_resource_threshold_handler(test_handler)

        # Check that the handler was registered
        assert handler_id == "test-handler-id"
        mock_instance.register_handler.assert_called_once_with(test_handler)

        # Unregister the handler
        unregister_resource_threshold_handler(handler_id)

        # Check that the handler was unregistered
        mock_instance.unregister_handler.assert_called_once_with(handler_id)


class TestSystemIntegration:
    """Integration tests that interact with the actual system resources."""

    @pytest.mark.skipif(
        os.environ.get("SKIP_SYSTEM_TESTS") == "1",
        reason="System tests are disabled",
    )
    def test_actual_resource_usage(self):
        """Test collecting actual system resource usage."""
        # Create a resource monitor
        thresholds = ResourceThresholds(
            cpu_percent=99.0,  # Set high to avoid triggering
            memory_percent=99.0,
            disk_percent=99.0,
        )

        monitor = ResourceMonitor(
            thresholds=thresholds,
            monitoring_interval=0.1,
            max_history=10,
        )

        try:
            # Collect usage directly
            usage = monitor._collect_resource_usage()

            # Check that the usage values are reasonable
            assert 0.0 <= usage.cpu_percent <= 100.0
            assert 0.0 <= usage.memory_percent <= 100.0
            assert 0.0 <= usage.disk_percent <= 100.0
            assert usage.network_bytes_sent >= 0
            assert usage.network_bytes_recv >= 0
            assert usage.timestamp > 0

            # Start the monitor
            monitor.start()

            # Wait for some history to accumulate
            time.sleep(0.25)

            # Stop the monitor
            monitor.stop()

            # Check that history was recorded
            assert len(monitor.history) > 0
        finally:
            # Ensure the monitor is stopped
            if monitor.running:
                monitor.stop()
