"""
Performance monitoring utilities for PathfinderBot.

This module provides tools for monitoring CPU usage, memory usage,
and other performance metrics. It allows tracking performance over time
and implements adaptive resource management.
"""

import os
import time
import json
import threading
import logging
import psutil
from typing import Dict, List, Any, Callable, Union, Optional
from collections import deque
from threading import Lock
import traceback


class PerformanceMetric:
    """Class to store and calculate statistics for a performance metric."""

    def __init__(self, name: str, buffer_size: int = 100):
        """
        Initialize a new performance metric.

        Args:
            name: The name of the metric
            buffer_size: The number of values to keep in the history buffer
        """
        self.name = name
        self.buffer_size = buffer_size
        self.values = deque(maxlen=buffer_size)
        self.min_value = None
        self.max_value = None
        self.sum = 0
        self.count = 0
        self.last_update = 0

    def add_value(self, value: float) -> None:
        """
        Add a new value to the metric.

        Args:
            value: The value to add
        """
        self.values.append(value)

        if self.min_value is None or value < self.min_value:
            self.min_value = value

        if self.max_value is None or value > self.max_value:
            self.max_value = value

        self.sum += value
        self.count += 1
        self.last_update = time.time()

    def get_average(self) -> Optional[float]:
        """
        Get the average value of the metric.

        Returns:
            The average value, or None if no values have been added
        """
        if self.count == 0:
            return None
        return self.sum / self.count

    def get_recent_average(self, count: int = None) -> Optional[float]:
        """
        Get the average of the most recent values.

        Args:
            count: The number of recent values to average, or None for all values

        Returns:
            The average of the most recent values, or None if no values have been added
        """
        if not self.values:
            return None

        count = count or len(self.values)
        count = min(count, len(self.values))

        recent_values = list(self.values)[-count:]
        return sum(recent_values) / len(recent_values)

    def get_min(self) -> Optional[float]:
        """Get the minimum value."""
        return self.min_value

    def get_max(self) -> Optional[float]:
        """Get the maximum value."""
        return self.max_value

    def reset(self) -> None:
        """Reset the metric."""
        self.values.clear()
        self.min_value = None
        self.max_value = None
        self.sum = 0
        self.count = 0

    def to_dict(self) -> Dict[str, Any]:
        """Convert the metric to a dictionary."""
        avg = self.get_average()
        recent_avg = self.get_recent_average(10)

        return {
            "name": self.name,
            "current": self.values[-1] if self.values else None,
            "average": avg,
            "recent_average": recent_avg,
            "min": self.min_value,
            "max": self.max_value,
            "count": self.count,
            "last_update": self.last_update,
        }


class PerformanceTimer:
    """Context manager for timing code execution."""

    _timers = {}
    _lock = Lock()

    def __init__(self, name: str):
        """
        Initialize a new performance timer.

        Args:
            name: The name of the timer
        """
        self.name = name
        self.start_time = 0
        self.end_time = 0

    def __enter__(self):
        self.start_time = time.perf_counter()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.end_time = time.perf_counter()
        duration = self.end_time - self.start_time

        with PerformanceTimer._lock:
            if self.name not in PerformanceTimer._timers:
                PerformanceTimer._timers[self.name] = []
            PerformanceTimer._timers[self.name].append(duration)

            # Keep only the last 100 timings
            if len(PerformanceTimer._timers[self.name]) > 100:
                PerformanceTimer._timers[self.name].pop(0)

    @classmethod
    def get_average_time(cls, name: str) -> Optional[float]:
        """
        Get the average execution time for a timer.

        Args:
            name: The name of the timer

        Returns:
            The average time in seconds, or None if the timer doesn't exist
        """
        with cls._lock:
            if name not in cls._timers or not cls._timers[name]:
                return None
            return sum(cls._timers[name]) / len(cls._timers[name])

    @classmethod
    def get_all_timers(cls) -> Dict[str, Dict[str, Union[float, int]]]:
        """
        Get all timers and their statistics.

        Returns:
            A dictionary mapping timer names to statistics
        """
        result = {}
        with cls._lock:
            for name, times in cls._timers.items():
                if not times:
                    continue

                avg_time = sum(times) / len(times)
                min_time = min(times)
                max_time = max(times)

                result[name] = {
                    "average": avg_time,
                    "min": min_time,
                    "max": max_time,
                    "count": len(times),
                    "total": sum(times),
                }
        return result


class PerformanceMonitor:
    """
    Performance monitoring system for PathfinderBot.

    This class provides methods for monitoring CPU usage, memory usage,
    and other performance metrics. It can be used to track performance
    over time and implement adaptive resource management.
    """

    def __init__(
        self,
        sample_interval: float = 1.0,
        buffer_size: int = 100,
        metrics_file: str = None,
    ):
        """
        Initialize a new performance monitor.

        Args:
            sample_interval: The interval between samples in seconds
            buffer_size: The number of values to keep in the history buffer for each metric
            metrics_file: The file to save metrics to, or None to disable saving
        """
        self.sample_interval = sample_interval
        self.buffer_size = buffer_size
        self.metrics_file = metrics_file
        self.metrics: Dict[str, PerformanceMetric] = {}
        self.running = False
        self.monitoring_thread = None
        self.callbacks: Dict[str, Callable] = {}
        self.lock = Lock()

        # Initialize basic metrics
        self.register_metric("cpu_usage")
        self.register_metric("memory_usage")
        self.register_metric("memory_usage_mb")
        self.register_metric("cpu_temperature")
        self.register_metric("disk_usage")
        self.register_metric("websocket_latency")

    def register_metric(self, name: str) -> None:
        """
        Register a new metric to monitor.

        Args:
            name: The name of the metric
        """
        with self.lock:
            if name not in self.metrics:
                self.metrics[name] = PerformanceMetric(name, self.buffer_size)

    def add_metric_value(self, name: str, value: float) -> None:
        """
        Add a value to a metric.

        Args:
            name: The name of the metric
            value: The value to add
        """
        with self.lock:
            if name not in self.metrics:
                self.register_metric(name)
            self.metrics[name].add_value(value)

    def get_metric_average(self, name: str) -> Optional[float]:
        """
        Get the average value of a metric.

        Args:
            name: The name of the metric

        Returns:
            The average value, or None if the metric doesn't exist or has no values
        """
        with self.lock:
            if name not in self.metrics:
                return None
            return self.metrics[name].get_average()

    def get_metric_recent_average(
        self, name: str, count: int = None
    ) -> Optional[float]:
        """
        Get the average of the most recent values of a metric.

        Args:
            name: The name of the metric
            count: The number of recent values to average, or None for all values

        Returns:
            The average of the most recent values, or None if the metric doesn't exist or has no values
        """
        with self.lock:
            if name not in self.metrics:
                return None
            return self.metrics[name].get_recent_average(count)

    def register_callback(self, name: str, callback: Callable) -> None:
        """
        Register a callback function to be called during monitoring.

        Args:
            name: The name of the callback
            callback: The callback function
        """
        with self.lock:
            self.callbacks[name] = callback

    def unregister_callback(self, name: str) -> None:
        """
        Unregister a callback function.

        Args:
            name: The name of the callback
        """
        with self.lock:
            if name in self.callbacks:
                del self.callbacks[name]

    def start(self) -> None:
        """Start the performance monitor."""
        if self.running:
            return

        self.running = True
        self.monitoring_thread = threading.Thread(
            target=self._monitoring_loop, daemon=True
        )
        self.monitoring_thread.start()

    def stop(self) -> None:
        """Stop the performance monitor."""
        self.running = False
        if self.monitoring_thread:
            self.monitoring_thread.join(timeout=2.0)
            self.monitoring_thread = None

    def _monitoring_loop(self) -> None:
        """Main monitoring loop."""
        while self.running:
            try:
                # Sample system metrics
                self._sample_system_metrics()

                # Run registered callbacks
                self._run_callbacks()

                # Save metrics to file if configured
                self._save_metrics()

            except Exception as e:
                logging.error(f"Error in performance monitoring: {e}")
                logging.error(traceback.format_exc())

            # Sleep until next sample
            time.sleep(self.sample_interval)

    def _sample_system_metrics(self) -> None:
        """Sample system metrics."""
        try:
            # CPU usage
            cpu_usage = psutil.cpu_percent(interval=None)
            self.add_metric_value("cpu_usage", cpu_usage)

            # Memory usage
            memory = psutil.virtual_memory()
            self.add_metric_value("memory_usage", memory.percent)
            self.add_metric_value("memory_usage_mb", memory.used / (1024 * 1024))

            # Disk usage
            disk = psutil.disk_usage("/")
            self.add_metric_value("disk_usage", disk.percent)

            # CPU temperature (if available)
            if hasattr(psutil, "sensors_temperatures"):
                try:
                    temps = psutil.sensors_temperatures()
                    if temps:
                        # Get the first temperature sensor
                        for name, entries in temps.items():
                            if entries:
                                temp = entries[0].current
                                self.add_metric_value("cpu_temperature", temp)
                                break
                except Exception:
                    pass  # Temperature monitoring not available

        except Exception as e:
            logging.error(f"Error sampling system metrics: {e}")

    def _run_callbacks(self) -> None:
        """Run all registered callbacks."""
        with self.lock:
            callbacks = list(self.callbacks.items())

        for name, callback in callbacks:
            try:
                callback()
            except Exception as e:
                logging.error(f"Error in callback {name}: {e}")

    def _save_metrics(self) -> None:
        """Save metrics to file if configured."""
        if not self.metrics_file:
            return

        try:
            metrics_data = self.get_metrics_summary()

            # Create directory if it doesn't exist
            os.makedirs(os.path.dirname(self.metrics_file), exist_ok=True)

            # Save metrics to file
            with open(self.metrics_file, "w") as f:
                json.dump(metrics_data, f, indent=2)

        except Exception as e:
            logging.error(f"Error saving metrics: {e}")

    def get_metrics(self) -> Dict[str, PerformanceMetric]:
        """Get all metrics."""
        with self.lock:
            return self.metrics.copy()

    def get_metrics_summary(self) -> Dict[str, Any]:
        """
        Get a summary of all metrics.

        Returns:
            A dictionary containing the summary
        """
        result = {
            "timestamp": time.time(),
            "metrics": {},
            "timers": PerformanceTimer.get_all_timers(),
        }

        with self.lock:
            for name, metric in self.metrics.items():
                result["metrics"][name] = metric.to_dict()

        return result

    def reset_metrics(self) -> None:
        """Reset all metrics."""
        with self.lock:
            for metric in self.metrics.values():
                metric.reset()


# Singleton instance
_performance_monitor = None


def start_monitoring(
    sample_interval: float = 1.0, buffer_size: int = 100, metrics_file: str = None
) -> PerformanceMonitor:
    """
    Start the performance monitoring system.

    Args:
        sample_interval: The interval between samples in seconds
        buffer_size: The number of values to keep in the history buffer for each metric
        metrics_file: The file to save metrics to, or None to disable saving

    Returns:
        The PerformanceMonitor instance
    """
    global _performance_monitor

    if _performance_monitor is None:
        _performance_monitor = PerformanceMonitor(
            sample_interval=sample_interval,
            buffer_size=buffer_size,
            metrics_file=metrics_file,
        )
        _performance_monitor.start()

    return _performance_monitor


def get_performance_monitor() -> Optional[PerformanceMonitor]:
    """
    Get the performance monitor instance.

    Returns:
        The PerformanceMonitor instance, or None if monitoring hasn't been started
    """
    return _performance_monitor


def stop_monitoring() -> None:
    """Stop the performance monitoring system."""
    global _performance_monitor

    if _performance_monitor is not None:
        _performance_monitor.stop()
        _performance_monitor = None
