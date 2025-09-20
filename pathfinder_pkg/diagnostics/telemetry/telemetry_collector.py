"""
Telemetry collection for PathfinderBot.

This module provides tools for collecting, storing, and analyzing telemetry
data from the PathfinderBot system.
"""

import os
import time
import threading
import logging
import json
import datetime
import sqlite3
from typing import Dict, List, Any, Optional, Union, Callable
from pathlib import Path
import traceback

from pathfinder_pkg.reliability.error_handling.errors import (
    register_error,
    SoftwareError,
    ErrorSeverity,
)

# Setup module logger
logger = logging.getLogger(__name__)


class TelemetryPoint:
    """Class representing a single telemetry data point."""

    def __init__(
        self,
        metric_name: str,
        value: Any,
        timestamp: Optional[float] = None,
        source: Optional[str] = None,
        tags: Optional[Dict[str, str]] = None,
    ):
        """
        Initialize a new telemetry data point.

        Args:
            metric_name: Name of the metric
            value: Value of the metric
            timestamp: Timestamp of the data point (if None, current time is used)
            source: Source of the data point (e.g., component name)
            tags: Additional tags for the data point
        """
        self.metric_name = metric_name
        self.value = value
        self.timestamp = timestamp if timestamp is not None else time.time()
        self.source = source
        self.tags = tags or {}

    def to_dict(self) -> Dict[str, Any]:
        """Convert the telemetry point to a dictionary."""
        result = {
            "metric_name": self.metric_name,
            "value": self.value,
            "timestamp": self.timestamp,
        }
        if self.source:
            result["source"] = self.source
        if self.tags:
            result["tags"] = self.tags
        return result

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TelemetryPoint":
        """
        Create a telemetry point from a dictionary.

        Args:
            data: Dictionary containing telemetry data

        Returns:
            A new TelemetryPoint object
        """
        return cls(
            metric_name=data["metric_name"],
            value=data["value"],
            timestamp=data.get("timestamp"),
            source=data.get("source"),
            tags=data.get("tags"),
        )


class TelemetryStorage:
    """Base class for telemetry storage backends."""

    def store(self, point: TelemetryPoint) -> bool:
        """
        Store a telemetry data point.

        Args:
            point: The data point to store

        Returns:
            True if the data point was successfully stored, False otherwise
        """
        raise NotImplementedError("Subclasses must implement store()")

    def query(
        self,
        metric_name: Optional[str] = None,
        source: Optional[str] = None,
        tags: Optional[Dict[str, str]] = None,
        start_time: Optional[float] = None,
        end_time: Optional[float] = None,
        limit: Optional[int] = None,
    ) -> List[TelemetryPoint]:
        """
        Query telemetry data points.

        Args:
            metric_name: Filter by metric name
            source: Filter by source
            tags: Filter by tags (all specified tags must match)
            start_time: Filter by start time (inclusive)
            end_time: Filter by end time (inclusive)
            limit: Maximum number of data points to return

        Returns:
            List of matching telemetry data points
        """
        raise NotImplementedError("Subclasses must implement query()")


class MemoryTelemetryStorage(TelemetryStorage):
    """In-memory storage for telemetry data."""

    def __init__(self, max_points: int = 10000):
        """
        Initialize new in-memory telemetry storage.

        Args:
            max_points: Maximum number of data points to store
        """
        self.max_points = max_points
        self.points: List[TelemetryPoint] = []
        self.lock = threading.RLock()

    def store(self, point: TelemetryPoint) -> bool:
        """
        Store a telemetry data point.

        Args:
            point: The data point to store

        Returns:
            True if the data point was successfully stored, False otherwise
        """
        with self.lock:
            # If we've reached the maximum number of points, remove the oldest one
            if len(self.points) >= self.max_points:
                self.points.pop(0)

            self.points.append(point)
            return True

    def query(
        self,
        metric_name: Optional[str] = None,
        source: Optional[str] = None,
        tags: Optional[Dict[str, str]] = None,
        start_time: Optional[float] = None,
        end_time: Optional[float] = None,
        limit: Optional[int] = None,
    ) -> List[TelemetryPoint]:
        """
        Query telemetry data points.

        Args:
            metric_name: Filter by metric name
            source: Filter by source
            tags: Filter by tags (all specified tags must match)
            start_time: Filter by start time (inclusive)
            end_time: Filter by end time (inclusive)
            limit: Maximum number of data points to return

        Returns:
            List of matching telemetry data points
        """
        result = []

        with self.lock:
            for point in self.points:
                # Apply filters
                if metric_name and point.metric_name != metric_name:
                    continue

                if source and point.source != source:
                    continue

                if tags:
                    match = True
                    for key, value in tags.items():
                        if key not in point.tags or point.tags[key] != value:
                            match = False
                            break
                    if not match:
                        continue

                if start_time and point.timestamp < start_time:
                    continue

                if end_time and point.timestamp > end_time:
                    continue

                result.append(point)

                # Apply limit
                if limit and len(result) >= limit:
                    break

        return result


class FileTelemetryStorage(TelemetryStorage):
    """File-based storage for telemetry data."""

    def __init__(self, file_path: str, flush_interval: int = 10):
        """
        Initialize new file-based telemetry storage.

        Args:
            file_path: Path to the file to store data in
            flush_interval: Interval in seconds to flush data to disk
        """
        self.file_path = file_path
        self.flush_interval = flush_interval
        self.buffer: List[TelemetryPoint] = []
        self.lock = threading.RLock()
        self.last_flush = time.time()
        self.flush_thread = None
        self.running = False

        # Create the directory if it doesn't exist
        dir_path = os.path.dirname(file_path)
        if dir_path and not os.path.exists(dir_path):
            os.makedirs(dir_path)

        # Start the flush thread
        self._start_flush_thread()

    def _start_flush_thread(self) -> None:
        """Start the background thread that flushes data to disk."""
        if self.flush_thread is not None:
            return

        self.running = True
        self.flush_thread = threading.Thread(
            target=self._flush_loop,
            name="telemetry-flush",
            daemon=True,
        )
        self.flush_thread.start()

    def _stop_flush_thread(self) -> None:
        """Stop the background flush thread."""
        self.running = False
        if self.flush_thread:
            self.flush_thread.join(timeout=2.0)
            self.flush_thread = None

    def _flush_loop(self) -> None:
        """Background thread that periodically flushes data to disk."""
        while self.running:
            try:
                time.sleep(self.flush_interval)
                self._flush()
            except Exception as e:
                logger.error(f"Error in telemetry flush loop: {e}")
                logger.error(traceback.format_exc())

    def _flush(self) -> None:
        """Flush buffered data to disk."""
        with self.lock:
            if not self.buffer:
                return

            try:
                # Convert buffer to list of dictionaries
                data = [point.to_dict() for point in self.buffer]

                # Write to file (append mode)
                with open(self.file_path, "a") as f:
                    for point_dict in data:
                        # Write each point as a separate JSON line (newline-delimited JSON)
                        f.write(json.dumps(point_dict) + "\n")

                # Clear the buffer
                self.buffer = []
                self.last_flush = time.time()

            except Exception as e:
                logger.error(f"Failed to flush telemetry data: {e}")
                logger.error(traceback.format_exc())
                register_error(
                    SoftwareError(
                        "Failed to flush telemetry data to file",
                        severity=ErrorSeverity.MEDIUM,
                        details={"file_path": self.file_path},
                        cause=e,
                    )
                )

    def store(self, point: TelemetryPoint) -> bool:
        """
        Store a telemetry data point.

        Args:
            point: The data point to store

        Returns:
            True if the data point was successfully stored, False otherwise
        """
        with self.lock:
            self.buffer.append(point)

            # Flush if buffer is getting too large
            if len(self.buffer) > 1000:
                self._flush()

            return True

    def query(
        self,
        metric_name: Optional[str] = None,
        source: Optional[str] = None,
        tags: Optional[Dict[str, str]] = None,
        start_time: Optional[float] = None,
        end_time: Optional[float] = None,
        limit: Optional[int] = None,
    ) -> List[TelemetryPoint]:
        """
        Query telemetry data points.

        Args:
            metric_name: Filter by metric name
            source: Filter by source
            tags: Filter by tags (all specified tags must match)
            start_time: Filter by start time (inclusive)
            end_time: Filter by end time (inclusive)
            limit: Maximum number of data points to return

        Returns:
            List of matching telemetry data points
        """
        # First flush any buffered data
        self._flush()

        result = []

        # Check if file exists
        if not os.path.exists(self.file_path):
            return result

        try:
            with open(self.file_path, "r") as f:
                for line in f:
                    if not line.strip():
                        continue

                    try:
                        point_dict = json.loads(line)
                        point = TelemetryPoint.from_dict(point_dict)

                        # Apply filters
                        if metric_name and point.metric_name != metric_name:
                            continue

                        if source and point.source != source:
                            continue

                        if tags:
                            match = True
                            for key, value in tags.items():
                                if key not in point.tags or point.tags[key] != value:
                                    match = False
                                    break
                            if not match:
                                continue

                        if start_time and point.timestamp < start_time:
                            continue

                        if end_time and point.timestamp > end_time:
                            continue

                        result.append(point)

                        # Apply limit
                        if limit and len(result) >= limit:
                            break

                    except json.JSONDecodeError:
                        logger.warning(f"Failed to parse telemetry data: {line}")
                        continue

        except Exception as e:
            logger.error(f"Failed to read telemetry data: {e}")
            logger.error(traceback.format_exc())
            register_error(
                SoftwareError(
                    "Failed to read telemetry data from file",
                    severity=ErrorSeverity.MEDIUM,
                    details={"file_path": self.file_path},
                    cause=e,
                )
            )

        return result

    def close(self) -> None:
        """Close the storage and flush any remaining data."""
        self._flush()
        self._stop_flush_thread()


class SQLiteTelemetryStorage(TelemetryStorage):
    """SQLite-based storage for telemetry data."""

    def __init__(self, db_path: str):
        """
        Initialize new SQLite-based telemetry storage.

        Args:
            db_path: Path to the SQLite database file
        """
        self.db_path = db_path
        self.lock = threading.RLock()

        # Create the directory if it doesn't exist
        dir_path = os.path.dirname(db_path)
        if dir_path and not os.path.exists(dir_path):
            os.makedirs(dir_path)

        # Initialize the database
        self._init_db()

    def _init_db(self) -> None:
        """Initialize the database schema."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()

                # Create telemetry table
                cursor.execute(
                    """
                CREATE TABLE IF NOT EXISTS telemetry (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    metric_name TEXT NOT NULL,
                    value TEXT NOT NULL,
                    timestamp REAL NOT NULL,
                    source TEXT,
                    tags TEXT
                )
                """
                )

                # Create index on timestamp for faster queries
                cursor.execute(
                    """
                CREATE INDEX IF NOT EXISTS idx_telemetry_timestamp ON telemetry (timestamp)
                """
                )

                # Create index on metric_name for faster queries
                cursor.execute(
                    """
                CREATE INDEX IF NOT EXISTS idx_telemetry_metric_name ON telemetry (metric_name)
                """
                )

                conn.commit()

        except Exception as e:
            logger.error(f"Failed to initialize telemetry database: {e}")
            logger.error(traceback.format_exc())
            register_error(
                SoftwareError(
                    "Failed to initialize telemetry database",
                    severity=ErrorSeverity.HIGH,
                    details={"db_path": self.db_path},
                    cause=e,
                )
            )

    def _get_connection(self) -> sqlite3.Connection:
        """
        Get a connection to the SQLite database.

        Returns:
            SQLite database connection
        """
        return sqlite3.connect(self.db_path)

    def store(self, point: TelemetryPoint) -> bool:
        """
        Store a telemetry data point.

        Args:
            point: The data point to store

        Returns:
            True if the data point was successfully stored, False otherwise
        """
        with self.lock:
            try:
                with self._get_connection() as conn:
                    cursor = conn.cursor()

                    # Convert tags to JSON string
                    tags_json = json.dumps(point.tags) if point.tags else None

                    # Convert value to JSON string if it's not a primitive type
                    value = point.value
                    if not isinstance(value, (str, int, float, bool, type(None))):
                        value = json.dumps(value)

                    # Insert data
                    cursor.execute(
                        """
                        INSERT INTO telemetry (metric_name, value, timestamp, source, tags)
                        VALUES (?, ?, ?, ?, ?)
                        """,
                        (
                            point.metric_name,
                            str(value),
                            point.timestamp,
                            point.source,
                            tags_json,
                        ),
                    )

                    conn.commit()
                    return True

            except Exception as e:
                logger.error(f"Failed to store telemetry data: {e}")
                logger.error(traceback.format_exc())
                register_error(
                    SoftwareError(
                        "Failed to store telemetry data in database",
                        severity=ErrorSeverity.MEDIUM,
                        details={"db_path": self.db_path},
                        cause=e,
                    )
                )
                return False

    def query(
        self,
        metric_name: Optional[str] = None,
        source: Optional[str] = None,
        tags: Optional[Dict[str, str]] = None,
        start_time: Optional[float] = None,
        end_time: Optional[float] = None,
        limit: Optional[int] = None,
    ) -> List[TelemetryPoint]:
        """
        Query telemetry data points.

        Args:
            metric_name: Filter by metric name
            source: Filter by source
            tags: Filter by tags (all specified tags must match)
            start_time: Filter by start time (inclusive)
            end_time: Filter by end time (inclusive)
            limit: Maximum number of data points to return

        Returns:
            List of matching telemetry data points
        """
        with self.lock:
            try:
                with self._get_connection() as conn:
                    cursor = conn.cursor()

                    # Build query
                    query = "SELECT metric_name, value, timestamp, source, tags FROM telemetry WHERE 1=1"
                    params = []

                    if metric_name:
                        query += " AND metric_name = ?"
                        params.append(metric_name)

                    if source:
                        query += " AND source = ?"
                        params.append(source)

                    if start_time:
                        query += " AND timestamp >= ?"
                        params.append(start_time)

                    if end_time:
                        query += " AND timestamp <= ?"
                        params.append(end_time)

                    # Order by timestamp
                    query += " ORDER BY timestamp DESC"

                    # Apply limit
                    if limit:
                        query += f" LIMIT {limit}"

                    # Execute query
                    cursor.execute(query, params)

                    # Process results
                    result = []
                    for row in cursor.fetchall():
                        metric_name, value, timestamp, source, tags_json = row

                        # Parse tags
                        tags_dict = json.loads(tags_json) if tags_json else {}

                        # Apply tags filter (can't do this in SQL easily)
                        if tags:
                            match = True
                            for key, value in tags.items():
                                if key not in tags_dict or tags_dict[key] != value:
                                    match = False
                                    break
                            if not match:
                                continue

                        # Try to parse value as JSON if it looks like it
                        try:
                            if value and value[0] in "[{" and value[-1] in "]}":
                                value = json.loads(value)
                        except (json.JSONDecodeError, TypeError):
                            pass  # Keep original value

                        # Create telemetry point
                        point = TelemetryPoint(
                            metric_name=metric_name,
                            value=value,
                            timestamp=timestamp,
                            source=source,
                            tags=tags_dict,
                        )

                        result.append(point)

                    return result

            except Exception as e:
                logger.error(f"Failed to query telemetry data: {e}")
                logger.error(traceback.format_exc())
                register_error(
                    SoftwareError(
                        "Failed to query telemetry data from database",
                        severity=ErrorSeverity.MEDIUM,
                        details={"db_path": self.db_path},
                        cause=e,
                    )
                )
                return []


class TelemetryCollector:
    """
    Telemetry collector for PathfinderBot.

    This class collects telemetry data from various sources and
    stores it in a storage backend.
    """

    def __init__(
        self,
        storage: Optional[TelemetryStorage] = None,
        collection_interval: float = 5.0,
    ):
        """
        Initialize a new telemetry collector.

        Args:
            storage: Storage backend for telemetry data
            collection_interval: Interval between automatic collection in seconds
        """
        self.storage = storage or MemoryTelemetryStorage()
        self.collection_interval = collection_interval
        self.collectors: Dict[str, Callable[[], Dict[str, Any]]] = {}
        self.running = False
        self.collection_thread = None
        self._stop_event = threading.Event()
        self._instance = None

    def start(self) -> None:
        """Start collecting telemetry data."""
        if self.running:
            logger.warning("Telemetry collector already running")
            return

        self.running = True
        self._stop_event.clear()
        self.collection_thread = threading.Thread(
            target=self._collection_loop,
            name="telemetry-collector",
            daemon=True,
        )
        self.collection_thread.start()
        logger.info("Telemetry collector started")

    def stop(self) -> None:
        """Stop collecting telemetry data."""
        if not self.running:
            logger.warning("Telemetry collector not running")
            return

        self.running = False
        self._stop_event.set()
        if self.collection_thread:
            self.collection_thread.join(timeout=2.0)
            self.collection_thread = None

        logger.info("Telemetry collector stopped")

        # Close storage if it supports it
        if hasattr(self.storage, "close") and callable(self.storage.close):
            self.storage.close()

    def register_collector(
        self,
        name: str,
        collector: Callable[[], Dict[str, Any]],
    ) -> None:
        """
        Register a function that collects telemetry data.

        Args:
            name: Name of the collector (used as a prefix for metric names)
            collector: Function that returns a dictionary of metric values
        """
        self.collectors[name] = collector
        logger.info(f"Registered telemetry collector: {name}")

    def unregister_collector(self, name: str) -> None:
        """
        Unregister a telemetry collector.

        Args:
            name: Name of the collector to unregister
        """
        if name in self.collectors:
            del self.collectors[name]
            logger.info(f"Unregistered telemetry collector: {name}")
        else:
            logger.warning(f"Telemetry collector not found: {name}")

    def collect(self) -> List[TelemetryPoint]:
        """
        Collect telemetry data from all registered collectors.

        Returns:
            List of collected telemetry points
        """
        points = []

        # Run all collectors
        for name, collector in self.collectors.items():
            try:
                # Call the collector function
                metrics = collector()

                # Create telemetry points for each metric
                for metric_name, value in metrics.items():
                    point = TelemetryPoint(
                        metric_name=f"{name}.{metric_name}",
                        value=value,
                        source=name,
                    )
                    points.append(point)

                    # Store the point
                    self.storage.store(point)

            except Exception as e:
                logger.error(f"Error in telemetry collector {name}: {e}")
                logger.error(traceback.format_exc())
                register_error(
                    SoftwareError(
                        f"Error in telemetry collector {name}",
                        severity=ErrorSeverity.MEDIUM,
                        cause=e,
                    )
                )

        return points

    def _collection_loop(self) -> None:
        """Background thread that periodically collects telemetry data."""
        while not self._stop_event.is_set():
            try:
                # Collect telemetry data
                self.collect()
            except Exception as e:
                logger.error(f"Error in telemetry collection loop: {e}")
                logger.error(traceback.format_exc())

            # Wait for the next collection interval or until stopped
            self._stop_event.wait(self.collection_interval)

    def record(
        self,
        metric_name: str,
        value: Any,
        source: Optional[str] = None,
        tags: Optional[Dict[str, str]] = None,
    ) -> bool:
        """
        Record a single telemetry point.

        Args:
            metric_name: Name of the metric
            value: Value of the metric
            source: Source of the data point (e.g., component name)
            tags: Additional tags for the data point

        Returns:
            True if the data point was successfully recorded, False otherwise
        """
        point = TelemetryPoint(
            metric_name=metric_name,
            value=value,
            source=source,
            tags=tags,
        )

        return self.storage.store(point)

    def query(
        self,
        metric_name: Optional[str] = None,
        source: Optional[str] = None,
        tags: Optional[Dict[str, str]] = None,
        start_time: Optional[float] = None,
        end_time: Optional[float] = None,
        limit: Optional[int] = None,
    ) -> List[TelemetryPoint]:
        """
        Query telemetry data.

        Args:
            metric_name: Filter by metric name
            source: Filter by source
            tags: Filter by tags (all specified tags must match)
            start_time: Filter by start time (inclusive)
            end_time: Filter by end time (inclusive)
            limit: Maximum number of data points to return

        Returns:
            List of matching telemetry points
        """
        return self.storage.query(
            metric_name=metric_name,
            source=source,
            tags=tags,
            start_time=start_time,
            end_time=end_time,
            limit=limit,
        )


# Global telemetry collector
_telemetry_collector = None


def get_telemetry_collector() -> TelemetryCollector:
    """
    Get the global telemetry collector.

    Returns:
        The global telemetry collector
    """
    global _telemetry_collector
    if _telemetry_collector is None:
        # Use an SQLite storage backend by default
        storage_dir = os.path.expanduser("~/.pathfinder/telemetry")
        os.makedirs(storage_dir, exist_ok=True)

        db_path = os.path.join(storage_dir, "telemetry.db")
        storage = SQLiteTelemetryStorage(db_path)

        _telemetry_collector = TelemetryCollector(storage=storage)
    return _telemetry_collector


def start_telemetry_collection() -> None:
    """Start collecting telemetry data."""
    collector = get_telemetry_collector()
    collector.start()

    # Register some built-in collectors
    register_system_collectors()


def stop_telemetry_collection() -> None:
    """Stop collecting telemetry data."""
    if _telemetry_collector:
        _telemetry_collector.stop()


def register_telemetry_collector(
    name: str,
    collector: Callable[[], Dict[str, Any]],
) -> None:
    """
    Register a function that collects telemetry data.

    Args:
        name: Name of the collector (used as a prefix for metric names)
        collector: Function that returns a dictionary of metric values
    """
    get_telemetry_collector().register_collector(name, collector)


def unregister_telemetry_collector(name: str) -> None:
    """
    Unregister a telemetry collector.

    Args:
        name: Name of the collector to unregister
    """
    if _telemetry_collector:
        _telemetry_collector.unregister_collector(name)


def record_telemetry(
    metric_name: str,
    value: Any,
    source: Optional[str] = None,
    tags: Optional[Dict[str, str]] = None,
) -> bool:
    """
    Record a single telemetry point.

    Args:
        metric_name: Name of the metric
        value: Value of the metric
        source: Source of the data point (e.g., component name)
        tags: Additional tags for the data point

    Returns:
        True if the data point was successfully recorded, False otherwise
    """
    return get_telemetry_collector().record(
        metric_name=metric_name,
        value=value,
        source=source,
        tags=tags,
    )


def register_system_collectors() -> None:
    """Register collectors for system metrics."""

    # System info collector
    def collect_system_info() -> Dict[str, Any]:
        """Collect basic system information."""
        import platform

        return {
            "platform": platform.platform(),
            "python_version": platform.python_version(),
            "processor": platform.processor(),
        }

    register_telemetry_collector("system_info", collect_system_info)

    # System resource collector
    def collect_system_resources() -> Dict[str, Any]:
        """Collect system resource metrics."""
        import psutil

        cpu_percent = psutil.cpu_percent(interval=None)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage("/")

        metrics = {
            "cpu_percent": cpu_percent,
            "memory_percent": memory.percent,
            "memory_used": memory.used,
            "memory_available": memory.available,
            "disk_percent": disk.percent,
            "disk_used": disk.used,
            "disk_free": disk.free,
        }

        # Add battery info if available
        if hasattr(psutil, "sensors_battery"):
            battery = psutil.sensors_battery()
            if battery:
                metrics["battery_percent"] = battery.percent
                metrics["battery_power_plugged"] = battery.power_plugged

        return metrics

    register_telemetry_collector("system_resources", collect_system_resources)

    # Process info collector
    def collect_process_info() -> Dict[str, Any]:
        """Collect process information."""
        import psutil
        import os

        process = psutil.Process(os.getpid())

        return {
            "cpu_percent": process.cpu_percent(interval=None),
            "memory_percent": process.memory_percent(),
            "memory_rss": process.memory_info().rss,
            "threads_count": process.num_threads(),
            "uptime": time.time() - process.create_time(),
        }

    register_telemetry_collector("process_info", collect_process_info)
