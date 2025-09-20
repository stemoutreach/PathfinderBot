"""
Resource management for PathfinderBot.

This module provides tools for monitoring and managing system resources
such as memory, CPU, and file handles.
"""

import os
import time
import threading
import logging
import psutil
from typing import Dict, List, Callable, Optional, Any, Union, Tuple
from enum import Enum, auto
import traceback

from pathfinder_pkg.reliability.error_handling.errors import (
    register_error,
    SoftwareError,
    ErrorSeverity,
)

# Setup module logger
logger = logging.getLogger(__name__)


class ResourceType(Enum):
    """Enumeration of resource types."""

    CPU = auto()
    MEMORY = auto()
    DISK = auto()
    FILE_HANDLES = auto()
    NETWORK = auto()
    BATTERY = auto()


class ResourceThreshold:
    """Threshold configuration for resource monitoring."""

    def __init__(
        self,
        warning_level: float,
        critical_level: float,
        check_interval: float = 5.0,
        smoothing_factor: float = 0.3,
        callback: Optional[Callable[[str, float, float], None]] = None,
    ):
        """
        Initialize a new resource threshold.

        Args:
            warning_level: Warning threshold level (0.0-1.0)
            critical_level: Critical threshold level (0.0-1.0)
            check_interval: Interval between checks in seconds
            smoothing_factor: Exponential smoothing factor for measurements (0.0-1.0)
            callback: Function to call when threshold is exceeded
        """
        self.warning_level = warning_level
        self.critical_level = critical_level
        self.check_interval = check_interval
        self.smoothing_factor = smoothing_factor
        self.callback = callback
        self.last_value = 0.0
        self.smoothed_value = 0.0
        self.last_warning = 0.0  # Timestamp of last warning
        self.warning_cooldown = 60.0  # Seconds between repeated warnings


class ResourceMonitor:
    """
    Resource monitoring system for PathfinderBot.

    This class provides methods for monitoring CPU usage, memory usage,
    disk space, and other system resources. It can trigger callbacks when
    resource usage exceeds specified thresholds.
    """

    def __init__(
        self,
        check_interval: float = 5.0,
    ):
        """
        Initialize a new resource monitor.

        Args:
            check_interval: Default interval between checks in seconds
        """
        self.check_interval = check_interval
        self.thresholds: Dict[ResourceType, ResourceThreshold] = {}
        self.callbacks: Dict[str, Callable[[str, float, float], None]] = {}
        self.running = False
        self.thread = None
        self._stop_event = threading.Event()
        self._instance = None

        # Add default thresholds
        self._add_default_thresholds()

    def _add_default_thresholds(self) -> None:
        """Add default thresholds for common resources."""
        # CPU usage threshold (warning at 80%, critical at 90%)
        self.set_threshold(
            ResourceType.CPU,
            warning_level=0.8,
            critical_level=0.9,
        )

        # Memory usage threshold (warning at 80%, critical at 90%)
        self.set_threshold(
            ResourceType.MEMORY,
            warning_level=0.8,
            critical_level=0.9,
        )

        # Disk space threshold (warning at 80%, critical at 90%)
        self.set_threshold(
            ResourceType.DISK,
            warning_level=0.8,
            critical_level=0.9,
        )

    def set_threshold(
        self,
        resource_type: ResourceType,
        warning_level: float,
        critical_level: float,
        check_interval: Optional[float] = None,
        smoothing_factor: float = 0.3,
        callback: Optional[Callable[[str, float, float], None]] = None,
    ) -> None:
        """
        Set a threshold for a specific resource type.

        Args:
            resource_type: The type of resource to monitor
            warning_level: Warning threshold level (0.0-1.0)
            critical_level: Critical threshold level (0.0-1.0)
            check_interval: Interval between checks in seconds
            smoothing_factor: Exponential smoothing factor for measurements (0.0-1.0)
            callback: Function to call when threshold is exceeded
        """
        if check_interval is None:
            check_interval = self.check_interval

        threshold = ResourceThreshold(
            warning_level=warning_level,
            critical_level=critical_level,
            check_interval=check_interval,
            smoothing_factor=smoothing_factor,
            callback=callback,
        )

        self.thresholds[resource_type] = threshold
        logger.info(
            f"Set {resource_type.name} threshold: "
            f"warning={warning_level:.2f}, critical={critical_level:.2f}, "
            f"interval={check_interval}s"
        )

    def register_callback(
        self,
        callback_id: str,
        callback: Callable[[str, float, float], None],
    ) -> None:
        """
        Register a callback function for resource threshold events.

        Args:
            callback_id: Unique identifier for the callback
            callback: Function to call when threshold is exceeded
                      Arguments: (resource_name, current_value, threshold_value)
        """
        self.callbacks[callback_id] = callback
        logger.info(f"Registered resource callback: {callback_id}")

    def unregister_callback(self, callback_id: str) -> None:
        """
        Unregister a callback function.

        Args:
            callback_id: Unique identifier for the callback
        """
        if callback_id in self.callbacks:
            del self.callbacks[callback_id]
            logger.info(f"Unregistered resource callback: {callback_id}")
        else:
            logger.warning(f"Callback {callback_id} not found")

    def start(self) -> None:
        """Start the resource monitor."""
        if self.running:
            logger.warning("Resource monitor already running")
            return

        self.running = True
        self._stop_event.clear()
        self.thread = threading.Thread(
            target=self._monitor_loop,
            name="resource-monitor",
            daemon=True,
        )
        self.thread.start()
        logger.info("Resource monitor started")

    def stop(self) -> None:
        """Stop the resource monitor."""
        if not self.running:
            logger.warning("Resource monitor not running")
            return

        self.running = False
        self._stop_event.set()
        if self.thread:
            self.thread.join(timeout=1.0)
        logger.info("Resource monitor stopped")

    def _monitor_loop(self) -> None:
        """
        Main monitoring loop.
        """
        next_check: Dict[ResourceType, float] = {}

        for resource_type in self.thresholds:
            next_check[resource_type] = time.time()

        while not self._stop_event.is_set():
            try:
                current_time = time.time()

                # Check each resource
                for resource_type, threshold in self.thresholds.items():
                    if current_time >= next_check[resource_type]:
                        self._check_resource(resource_type, threshold)
                        next_check[resource_type] = (
                            current_time + threshold.check_interval
                        )

            except Exception as e:
                logger.error(f"Error in resource monitor: {e}")
                logger.error(traceback.format_exc())
                register_error(
                    SoftwareError(
                        "Error in resource monitor loop",
                        severity=ErrorSeverity.MEDIUM,
                        cause=e,
                    )
                )

            # Sleep for a short time
            self._stop_event.wait(0.5)

    def _check_resource(
        self,
        resource_type: ResourceType,
        threshold: ResourceThreshold,
    ) -> None:
        """
        Check a specific resource and trigger callbacks if thresholds are exceeded.

        Args:
            resource_type: The type of resource to check
            threshold: The threshold configuration
        """
        # Get current resource usage
        current_value = self._get_resource_usage(resource_type)
        if current_value is None:
            return

        # Apply smoothing
        if threshold.smoothed_value == 0.0:
            threshold.smoothed_value = current_value
        else:
            threshold.smoothed_value = (
                threshold.smoothing_factor * current_value
                + (1.0 - threshold.smoothing_factor) * threshold.smoothed_value
            )

        threshold.last_value = current_value
        smoothed_value = threshold.smoothed_value

        # Check thresholds
        current_time = time.time()
        time_since_warning = current_time - threshold.last_warning

        # Critical threshold check
        if smoothed_value >= threshold.critical_level:
            if time_since_warning >= threshold.warning_cooldown:
                threshold.last_warning = current_time
                message = (
                    f"CRITICAL: {resource_type.name} usage at {smoothed_value:.2f}, "
                    f"exceeds critical threshold of {threshold.critical_level:.2f}"
                )
                logger.error(message)

                # Call resource-specific callback
                if threshold.callback:
                    try:
                        threshold.callback(
                            resource_type.name,
                            smoothed_value,
                            threshold.critical_level,
                        )
                    except Exception as e:
                        logger.error(f"Error in resource callback: {e}")

                # Call generic callbacks
                for callback_id, callback in self.callbacks.items():
                    try:
                        callback(
                            resource_type.name, smoothed_value, threshold.critical_level
                        )
                    except Exception as e:
                        logger.error(f"Error in callback {callback_id}: {e}")

        # Warning threshold check
        elif smoothed_value >= threshold.warning_level:
            if time_since_warning >= threshold.warning_cooldown:
                threshold.last_warning = current_time
                message = (
                    f"WARNING: {resource_type.name} usage at {smoothed_value:.2f}, "
                    f"exceeds warning threshold of {threshold.warning_level:.2f}"
                )
                logger.warning(message)

                # Call resource-specific callback
                if threshold.callback:
                    try:
                        threshold.callback(
                            resource_type.name,
                            smoothed_value,
                            threshold.warning_level,
                        )
                    except Exception as e:
                        logger.error(f"Error in resource callback: {e}")

                # Call generic callbacks
                for callback_id, callback in self.callbacks.items():
                    try:
                        callback(
                            resource_type.name, smoothed_value, threshold.warning_level
                        )
                    except Exception as e:
                        logger.error(f"Error in callback {callback_id}: {e}")

    def _get_resource_usage(self, resource_type: ResourceType) -> Optional[float]:
        """
        Get the current usage of a specific resource.

        Args:
            resource_type: The type of resource to check

        Returns:
            Current resource usage as a value between 0.0 and 1.0,
            or None if the resource cannot be checked
        """
        try:
            if resource_type == ResourceType.CPU:
                return psutil.cpu_percent(interval=None) / 100.0

            elif resource_type == ResourceType.MEMORY:
                memory = psutil.virtual_memory()
                return memory.percent / 100.0

            elif resource_type == ResourceType.DISK:
                disk = psutil.disk_usage("/")
                return disk.percent / 100.0

            elif resource_type == ResourceType.FILE_HANDLES:
                if hasattr(psutil, "Process"):
                    process = psutil.Process()
                    if hasattr(process, "num_fds"):
                        # Linux: Get file descriptors count
                        fds = process.num_fds()
                        # Assuming a typical limit of 1024 fds per process
                        return fds / 1024.0
                    else:
                        logger.debug(
                            "File handle monitoring not available on this platform"
                        )
                return None

            elif resource_type == ResourceType.BATTERY:
                if hasattr(psutil, "sensors_battery"):
                    battery = psutil.sensors_battery()
                    if battery:
                        # Battery usage is inverted (0% means empty, 100% means full)
                        return 1.0 - (battery.percent / 100.0)
                    else:
                        logger.debug("No battery found")
                        return None
                else:
                    logger.debug("Battery monitoring not available on this platform")
                    return None

            else:
                logger.warning(f"Unknown resource type: {resource_type}")
                return None

        except Exception as e:
            logger.error(f"Error getting {resource_type.name} usage: {e}")
            return None


class ResourceLimiter:
    """
    Resource limiter for PathfinderBot.

    This class provides methods for limiting resource usage by components
    of the PathfinderBot system.
    """

    def __init__(self, monitor: ResourceMonitor = None):
        """
        Initialize a new resource limiter.

        Args:
            monitor: The resource monitor to use for adaptive limiting
        """
        self.monitor = monitor
        self.resource_limits: Dict[str, Dict[str, float]] = {}
        self._instance = None

    def set_component_limit(
        self,
        component_id: str,
        resource_type: str,
        limit: float,
    ) -> None:
        """
        Set a resource limit for a component.

        Args:
            component_id: Identifier for the component
            resource_type: Type of resource (e.g., "memory", "cpu")
            limit: Maximum allowed resource usage
        """
        if component_id not in self.resource_limits:
            self.resource_limits[component_id] = {}

        self.resource_limits[component_id][resource_type] = limit
        logger.info(f"Set {resource_type} limit for {component_id}: {limit}")

    def get_component_limit(
        self,
        component_id: str,
        resource_type: str,
    ) -> Optional[float]:
        """
        Get a resource limit for a component.

        Args:
            component_id: Identifier for the component
            resource_type: Type of resource

        Returns:
            The resource limit, or None if not set
        """
        if (
            component_id in self.resource_limits
            and resource_type in self.resource_limits[component_id]
        ):
            return self.resource_limits[component_id][resource_type]
        else:
            return None

    def check_resource_limit(
        self,
        component_id: str,
        resource_type: str,
        current_usage: float,
    ) -> Tuple[bool, Optional[float]]:
        """
        Check if a component is within its resource limits.

        Args:
            component_id: Identifier for the component
            resource_type: Type of resource
            current_usage: Current resource usage

        Returns:
            Tuple of (is_within_limit, limit)
            where is_within_limit is True if usage is within limits,
            and limit is the configured limit or None if not set
        """
        limit = self.get_component_limit(component_id, resource_type)
        if limit is None:
            return True, None

        return current_usage <= limit, limit


class ResourcePool:
    """
    Resource pool for managing shared resources.

    This class provides a simple mechanism for tracking and managing
    resources that need to be shared between components.
    """

    def __init__(self, name: str, size: int):
        """
        Initialize a new resource pool.

        Args:
            name: Name of the pool
            size: Maximum size of the pool
        """
        self.name = name
        self.size = size
        self.used = 0
        self.lock = threading.RLock()

    def acquire(self, amount: int = 1) -> bool:
        """
        Acquire resources from the pool.

        Args:
            amount: Amount of resources to acquire

        Returns:
            True if resources were successfully acquired, False otherwise
        """
        with self.lock:
            if self.used + amount <= self.size:
                self.used += amount
                logger.debug(
                    f"Acquired {amount} from pool {self.name}, {self.used}/{self.size} used"
                )
                return True
            else:
                logger.warning(
                    f"Failed to acquire {amount} from pool {self.name}, "
                    f"{self.used}/{self.size} already used"
                )
                return False

    def release(self, amount: int = 1) -> None:
        """
        Release resources back to the pool.

        Args:
            amount: Amount of resources to release
        """
        with self.lock:
            self.used = max(0, self.used - amount)
            logger.debug(
                f"Released {amount} to pool {self.name}, {self.used}/{self.size} used"
            )

    def available(self) -> int:
        """
        Get the number of available resources in the pool.

        Returns:
            Number of available resources
        """
        with self.lock:
            return self.size - self.used


class ResourceManager:
    """
    Central resource manager for PathfinderBot.

    This class provides centralized resource management capabilities,
    including monitoring, limiting, and pooling of resources.
    """

    def __init__(self):
        """Initialize a new resource manager."""
        self.monitor = ResourceMonitor()
        self.limiter = ResourceLimiter(self.monitor)
        self.pools: Dict[str, ResourcePool] = {}
        self._instance = None

    def start_monitoring(self) -> None:
        """Start resource monitoring."""
        self.monitor.start()

    def stop_monitoring(self) -> None:
        """Stop resource monitoring."""
        self.monitor.stop()

    def create_pool(self, name: str, size: int) -> ResourcePool:
        """
        Create a new resource pool.

        Args:
            name: Name of the pool
            size: Maximum size of the pool

        Returns:
            The created resource pool
        """
        if name in self.pools:
            logger.warning(f"Pool {name} already exists, returning existing pool")
            return self.pools[name]

        pool = ResourcePool(name, size)
        self.pools[name] = pool
        logger.info(f"Created resource pool {name} with size {size}")
        return pool

    def get_pool(self, name: str) -> Optional[ResourcePool]:
        """
        Get a resource pool by name.

        Args:
            name: Name of the pool

        Returns:
            The resource pool, or None if not found
        """
        return self.pools.get(name)

    def set_component_limit(
        self,
        component_id: str,
        resource_type: str,
        limit: float,
    ) -> None:
        """
        Set a resource limit for a component.

        Args:
            component_id: Identifier for the component
            resource_type: Type of resource (e.g., "memory", "cpu")
            limit: Maximum allowed resource usage
        """
        self.limiter.set_component_limit(component_id, resource_type, limit)

    def register_monitor_callback(
        self,
        callback_id: str,
        callback: Callable[[str, float, float], None],
    ) -> None:
        """
        Register a callback for resource monitoring events.

        Args:
            callback_id: Unique identifier for the callback
            callback: Function to call when threshold is exceeded
                      Arguments: (resource_name, current_value, threshold_value)
        """
        self.monitor.register_callback(callback_id, callback)


# Global resource manager instance
_resource_manager = None


def get_resource_manager() -> ResourceManager:
    """
    Get the global resource manager instance.

    Returns:
        The global resource manager
    """
    global _resource_manager
    if _resource_manager is None:
        _resource_manager = ResourceManager()
    return _resource_manager


def start_resource_monitoring() -> ResourceMonitor:
    """
    Start resource monitoring.

    Returns:
        The resource monitor instance
    """
    manager = get_resource_manager()
    manager.start_monitoring()
    return manager.monitor


def stop_resource_monitoring() -> None:
    """Stop resource monitoring."""
    if _resource_manager is not None:
        _resource_manager.stop_monitoring()


def create_resource_pool(name: str, size: int) -> ResourcePool:
    """
    Create a new resource pool.

    Args:
        name: Name of the pool
        size: Maximum size of the pool

    Returns:
        The created resource pool
    """
    return get_resource_manager().create_pool(name, size)


def get_resource_pool(name: str) -> Optional[ResourcePool]:
    """
    Get a resource pool by name.

    Args:
        name: Name of the pool

    Returns:
        The resource pool, or None if not found
    """
    return get_resource_manager().get_pool(name)
