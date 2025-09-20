"""
Watchdog mechanisms for PathfinderBot.

This module implements watchdog timers and process monitoring to detect and
recover from system failures.
"""

import time
import threading
import logging
import signal
import os
import psutil
import traceback
from typing import Dict, List, Callable, Optional, Any, Union
from enum import Enum, auto

from pathfinder_pkg.reliability.error_handling.errors import (
    register_error,
    SoftwareError,
    ErrorSeverity,
)

# Setup module logger
logger = logging.getLogger(__name__)


class WatchdogState(Enum):
    """Enumeration of watchdog states."""

    INACTIVE = auto()
    ACTIVE = auto()
    TRIGGERED = auto()


class Watchdog:
    """
    Watchdog timer that triggers a callback if not reset within a specified time.

    This class provides a simple watchdog timer mechanism that can be used to
    detect system hangs or deadlocks.
    """

    def __init__(
        self,
        timeout: float,
        callback: Callable[[], None],
        name: str = "watchdog",
    ):
        """
        Initialize a new watchdog timer.

        Args:
            timeout: Timeout in seconds
            callback: Function to call when the watchdog times out
            name: Name of the watchdog
        """
        self.timeout = timeout
        self.callback = callback
        self.name = name
        self.state = WatchdogState.INACTIVE
        self.last_reset = 0.0
        self.thread = None
        self._stop_event = threading.Event()

    def reset(self) -> None:
        """Reset the watchdog timer."""
        self.last_reset = time.time()
        if self.state == WatchdogState.INACTIVE:
            logger.warning(f"Attempted to reset inactive watchdog {self.name}")

    def start(self) -> None:
        """Start the watchdog timer."""
        if self.state != WatchdogState.INACTIVE:
            logger.warning(f"Watchdog {self.name} already active")
            return

        self.state = WatchdogState.ACTIVE
        self.last_reset = time.time()
        self._stop_event.clear()

        self.thread = threading.Thread(
            target=self._monitor, name=f"watchdog-{self.name}", daemon=True
        )
        self.thread.start()

        logger.info(f"Watchdog {self.name} started with timeout {self.timeout}s")

    def stop(self) -> None:
        """Stop the watchdog timer."""
        if self.state == WatchdogState.INACTIVE:
            logger.warning(f"Attempted to stop inactive watchdog {self.name}")
            return

        self._stop_event.set()
        if self.thread:
            self.thread.join(timeout=1.0)

        self.state = WatchdogState.INACTIVE
        logger.info(f"Watchdog {self.name} stopped")

    def _monitor(self) -> None:
        """
        Monitor thread that checks if the watchdog needs to be triggered.
        """
        while not self._stop_event.is_set():
            time_since_reset = time.time() - self.last_reset

            if time_since_reset > self.timeout:
                logger.warning(
                    f"Watchdog {self.name} triggered: no reset in {time_since_reset:.2f}s"
                )
                self.state = WatchdogState.TRIGGERED
                try:
                    self.callback()
                except Exception as e:
                    logger.error(f"Error in watchdog callback: {e}")
                    logger.error(traceback.format_exc())
                    register_error(
                        SoftwareError(
                            f"Error in watchdog {self.name} callback",
                            severity=ErrorSeverity.HIGH,
                            details={"watchdog": self.name, "timeout": self.timeout},
                            cause=e,
                        )
                    )

                # Stop the watchdog after triggering
                self._stop_event.set()
                break

            # Sleep for a short time before checking again
            self._stop_event.wait(min(0.1, self.timeout / 10))


class ProcessWatchdog:
    """
    Watchdog that monitors a process and restarts it if it dies.

    This class provides a mechanism to monitor a process and automatically
    restart it if it dies or becomes unresponsive.
    """

    def __init__(
        self,
        process_name: str,
        restart_cmd: str,
        check_interval: float = 5.0,
        max_restarts: int = 3,
        restart_delay: float = 2.0,
    ):
        """
        Initialize a new process watchdog.

        Args:
            process_name: Name of the process to monitor
            restart_cmd: Command to restart the process
            check_interval: Interval between checks in seconds
            max_restarts: Maximum number of restart attempts
            restart_delay: Delay between restart attempts in seconds
        """
        self.process_name = process_name
        self.restart_cmd = restart_cmd
        self.check_interval = check_interval
        self.max_restarts = max_restarts
        self.restart_delay = restart_delay
        self.restarts = 0
        self.thread = None
        self._stop_event = threading.Event()
        self.running = False

    def start(self) -> None:
        """Start monitoring the process."""
        if self.running:
            logger.warning(f"Process watchdog for {self.process_name} already running")
            return

        self.running = True
        self._stop_event.clear()
        self.thread = threading.Thread(
            target=self._monitor, name=f"proc-watchdog-{self.process_name}", daemon=True
        )
        self.thread.start()

        logger.info(
            f"Process watchdog started for {self.process_name} "
            f"with check interval {self.check_interval}s"
        )

    def stop(self) -> None:
        """Stop monitoring the process."""
        if not self.running:
            logger.warning(f"Process watchdog for {self.process_name} not running")
            return

        self._stop_event.set()
        if self.thread:
            self.thread.join(timeout=1.0)

        self.running = False
        logger.info(f"Process watchdog stopped for {self.process_name}")

    def _monitor(self) -> None:
        """
        Monitor thread that checks if the process is running.
        """
        while not self._stop_event.is_set():
            try:
                # Check if process is running
                running = self._is_process_running()

                if not running:
                    logger.warning(
                        f"Process {self.process_name} not found, attempting restart"
                    )
                    self._restart_process()
                else:
                    logger.debug(f"Process {self.process_name} is running")

            except Exception as e:
                logger.error(f"Error in process watchdog: {e}")
                logger.error(traceback.format_exc())
                register_error(
                    SoftwareError(
                        f"Error in process watchdog for {self.process_name}",
                        severity=ErrorSeverity.MEDIUM,
                        details={"process": self.process_name},
                        cause=e,
                    )
                )

            # Wait for the next check interval
            self._stop_event.wait(self.check_interval)

    def _is_process_running(self) -> bool:
        """
        Check if the monitored process is running.

        Returns:
            True if the process is running, False otherwise
        """
        for proc in psutil.process_iter(["name", "cmdline"]):
            try:
                proc_name = proc.name()
                proc_cmdline = proc.cmdline() if hasattr(proc, "cmdline") else []

                # Check process name
                if proc_name == self.process_name:
                    return True

                # Check process command line
                if any(self.process_name in cmd for cmd in proc_cmdline):
                    return True

            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                continue

        return False

    def _restart_process(self) -> None:
        """
        Restart the monitored process.
        """
        if self.restarts >= self.max_restarts:
            logger.error(
                f"Process {self.process_name} has been restarted {self.restarts} times, "
                "giving up"
            )
            register_error(
                SoftwareError(
                    f"Failed to restart process {self.process_name} after {self.restarts} attempts",
                    severity=ErrorSeverity.HIGH,
                    details={"process": self.process_name, "restarts": self.restarts},
                )
            )
            self._stop_event.set()  # Stop the watchdog
            return

        # Increment restart counter
        self.restarts += 1

        logger.info(
            f"Restarting process {self.process_name} "
            f"(attempt {self.restarts}/{self.max_restarts})"
        )

        try:
            # Wait before restarting
            time.sleep(self.restart_delay)

            # Execute restart command
            exit_code = os.system(self.restart_cmd)
            if exit_code != 0:
                logger.error(
                    f"Failed to restart process {self.process_name}, exit code: {exit_code}"
                )
                register_error(
                    SoftwareError(
                        f"Failed to restart process {self.process_name}",
                        severity=ErrorSeverity.HIGH,
                        details={
                            "process": self.process_name,
                            "exit_code": exit_code,
                            "restart_cmd": self.restart_cmd,
                        },
                    )
                )
            else:
                logger.info(f"Process {self.process_name} restarted successfully")

        except Exception as e:
            logger.error(f"Error restarting process {self.process_name}: {e}")
            logger.error(traceback.format_exc())
            register_error(
                SoftwareError(
                    f"Error restarting process {self.process_name}",
                    severity=ErrorSeverity.HIGH,
                    details={
                        "process": self.process_name,
                        "restart_cmd": self.restart_cmd,
                    },
                    cause=e,
                )
            )


class ComponentWatchdogManager:
    """
    Manager for watchdogs monitoring different components.

    This class provides a centralized mechanism to manage multiple watchdogs
    for different system components.
    """

    def __init__(self, default_timeout: float = 10.0):
        """
        Initialize a new component watchdog manager.

        Args:
            default_timeout: Default timeout for watchdogs in seconds
        """
        self.default_timeout = default_timeout
        self.watchdogs: Dict[str, Watchdog] = {}
        self.callbacks: Dict[str, Callable[[], None]] = {}
        self.lock = threading.RLock()
        self._instance = None

    def register_watchdog(
        self,
        component_name: str,
        callback: Callable[[], None],
        timeout: Optional[float] = None,
        auto_start: bool = True,
    ) -> Watchdog:
        """
        Register a watchdog for a component.

        Args:
            component_name: Name of the component
            callback: Function to call when the watchdog times out
            timeout: Timeout in seconds (if None, use default_timeout)
            auto_start: Whether to automatically start the watchdog

        Returns:
            The created watchdog
        """
        with self.lock:
            if component_name in self.watchdogs:
                logger.warning(
                    f"Watchdog for component {component_name} already registered, "
                    "replacing with new one"
                )
                self.watchdogs[component_name].stop()

            # Use default timeout if not specified
            if timeout is None:
                timeout = self.default_timeout

            # Create watchdog
            watchdog = Watchdog(
                timeout=timeout,
                callback=callback,
                name=f"component-{component_name}",
            )

            # Store watchdog and callback
            self.watchdogs[component_name] = watchdog
            self.callbacks[component_name] = callback

            # Start watchdog if auto_start is True
            if auto_start:
                watchdog.start()

            logger.info(
                f"Registered watchdog for component {component_name} "
                f"with timeout {timeout}s"
            )

            return watchdog

    def unregister_watchdog(self, component_name: str) -> None:
        """
        Unregister a watchdog.

        Args:
            component_name: Name of the component
        """
        with self.lock:
            if component_name in self.watchdogs:
                logger.info(f"Unregistering watchdog for component {component_name}")
                self.watchdogs[component_name].stop()
                del self.watchdogs[component_name]
                del self.callbacks[component_name]
            else:
                logger.warning(f"No watchdog registered for component {component_name}")

    def reset_watchdog(self, component_name: str) -> bool:
        """
        Reset a component's watchdog.

        Args:
            component_name: Name of the component

        Returns:
            True if the watchdog was reset, False otherwise
        """
        with self.lock:
            if component_name in self.watchdogs:
                self.watchdogs[component_name].reset()
                return True
            else:
                logger.warning(
                    f"Attempted to reset unregistered watchdog for component {component_name}"
                )
                return False

    def start_all(self) -> None:
        """Start all registered watchdogs."""
        with self.lock:
            logger.info("Starting all watchdogs")
            for name, watchdog in self.watchdogs.items():
                try:
                    watchdog.start()
                except Exception as e:
                    logger.error(f"Failed to start watchdog for component {name}: {e}")
                    logger.error(traceback.format_exc())

    def stop_all(self) -> None:
        """Stop all registered watchdogs."""
        with self.lock:
            logger.info("Stopping all watchdogs")
            for name, watchdog in self.watchdogs.items():
                try:
                    watchdog.stop()
                except Exception as e:
                    logger.error(f"Failed to stop watchdog for component {name}: {e}")
                    logger.error(traceback.format_exc())


# Global component watchdog manager
_component_watchdog_manager = ComponentWatchdogManager()


def get_component_watchdog_manager() -> ComponentWatchdogManager:
    """
    Get the global component watchdog manager.

    Returns:
        The global component watchdog manager
    """
    return _component_watchdog_manager


def register_component_watchdog(
    component_name: str,
    callback: Callable[[], None],
    timeout: Optional[float] = None,
    auto_start: bool = True,
) -> Watchdog:
    """
    Register a watchdog for a component in the global manager.

    Args:
        component_name: Name of the component
        callback: Function to call when the watchdog times out
        timeout: Timeout in seconds (if None, use default_timeout)
        auto_start: Whether to automatically start the watchdog

    Returns:
        The created watchdog
    """
    return _component_watchdog_manager.register_watchdog(
        component_name, callback, timeout, auto_start
    )


def unregister_component_watchdog(component_name: str) -> None:
    """
    Unregister a component watchdog from the global manager.

    Args:
        component_name: Name of the component
    """
    _component_watchdog_manager.unregister_watchdog(component_name)


def reset_component_watchdog(component_name: str) -> bool:
    """
    Reset a component's watchdog in the global manager.

    Args:
        component_name: Name of the component

    Returns:
        True if the watchdog was reset, False otherwise
    """
    return _component_watchdog_manager.reset_watchdog(component_name)
