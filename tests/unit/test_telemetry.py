"""
Unit tests for the telemetry collector module.
"""

import pytest
import time
import os
import json
import sqlite3
import tempfile
import shutil
from unittest.mock import Mock, patch

from pathfinder_pkg.diagnostics.telemetry.telemetry_collector import (
    TelemetryPoint,
    TelemetryStorage,
    MemoryTelemetryStorage,
    FileTelemetryStorage,
    SQLiteTelemetryStorage,
    TelemetryCollector,
    get_telemetry_collector,
    start_telemetry_collection,
    stop_telemetry_collection,
    register_telemetry_collector,
    unregister_telemetry_collector,
    record_telemetry,
)


class TestTelemetryPoint:
    """Tests for the TelemetryPoint class."""

    def test_initialization(self):
        """Test that the telemetry point is initialized with the correct values."""
        # Create a basic telemetry point
        point = TelemetryPoint(
            metric_name="test.metric",
            value=42,
        )

        assert point.metric_name == "test.metric"
        assert point.value == 42
        assert point.timestamp > 0  # Should be set to current time
        assert point.source is None
        assert point.tags == {}

        # Create a telemetry point with custom attributes
        timestamp = time.time()
        point = TelemetryPoint(
            metric_name="test.metric",
            value=42,
            timestamp=timestamp,
            source="test_source",
            tags={"tag1": "value1"},
        )

        assert point.metric_name == "test.metric"
        assert point.value == 42
        assert point.timestamp == timestamp
        assert point.source == "test_source"
        assert point.tags == {"tag1": "value1"}

    def test_to_dict(self):
        """Test converting a telemetry point to a dictionary."""
        # Create a telemetry point
        timestamp = time.time()
        point = TelemetryPoint(
            metric_name="test.metric",
            value=42,
            timestamp=timestamp,
            source="test_source",
            tags={"tag1": "value1"},
        )

        # Convert to dictionary
        data = point.to_dict()

        # Check dictionary contents
        assert data["metric_name"] == "test.metric"
        assert data["value"] == 42
        assert data["timestamp"] == timestamp
        assert data["source"] == "test_source"
        assert data["tags"] == {"tag1": "value1"}

    def test_from_dict(self):
        """Test creating a telemetry point from a dictionary."""
        # Create a dictionary
        timestamp = time.time()
        data = {
            "metric_name": "test.metric",
            "value": 42,
            "timestamp": timestamp,
            "source": "test_source",
            "tags": {"tag1": "value1"},
        }

        # Create telemetry point from dictionary
        point = TelemetryPoint.from_dict(data)

        # Check telemetry point attributes
        assert point.metric_name == "test.metric"
        assert point.value == 42
        assert point.timestamp == timestamp
        assert point.source == "test_source"
        assert point.tags == {"tag1": "value1"}


class TestMemoryTelemetryStorage:
    """Tests for the MemoryTelemetryStorage class."""

    def test_store_and_query(self):
        """Test storing and querying telemetry points."""
        storage = MemoryTelemetryStorage(max_points=10)

        # Create and store some telemetry points
        point1 = TelemetryPoint(metric_name="test.metric1", value=1)
        point2 = TelemetryPoint(metric_name="test.metric2", value=2)
        point3 = TelemetryPoint(
            metric_name="test.metric3",
            value=3,
            source="test_source",
            tags={"tag1": "value1"},
        )

        storage.store(point1)
        storage.store(point2)
        storage.store(point3)

        # Query all points
        points = storage.query()
        assert len(points) == 3
        assert points[0] == point1
        assert points[1] == point2
        assert points[2] == point3

        # Query by metric name
        points = storage.query(metric_name="test.metric1")
        assert len(points) == 1
        assert points[0] == point1

        # Query by source
        points = storage.query(source="test_source")
        assert len(points) == 1
        assert points[0] == point3

        # Query by tags
        points = storage.query(tags={"tag1": "value1"})
        assert len(points) == 1
        assert points[0] == point3

        # Query by non-existent tag
        points = storage.query(tags={"tag1": "non-existent"})
        assert len(points) == 0

    def test_max_points(self):
        """Test that the storage respects the max_points limit."""
        storage = MemoryTelemetryStorage(max_points=2)

        # Create and store more points than the limit
        point1 = TelemetryPoint(metric_name="test.metric1", value=1)
        point2 = TelemetryPoint(metric_name="test.metric2", value=2)
        point3 = TelemetryPoint(metric_name="test.metric3", value=3)

        storage.store(point1)
        storage.store(point2)
        storage.store(point3)

        # Query all points (should only contain the latest two)
        points = storage.query()
        assert len(points) == 2
        assert points[0] == point2  # The oldest point (point1) should be removed
        assert points[1] == point3


@pytest.fixture
def temp_file():
    """Fixture that provides a temporary file path."""
    fd, path = tempfile.mkstemp()
    os.close(fd)

    yield path

    # Clean up
    if os.path.exists(path):
        os.remove(path)


class TestFileTelemetryStorage:
    """Tests for the FileTelemetryStorage class."""

    def test_store_and_query(self, temp_file):
        """Test storing and querying telemetry points."""
        storage = FileTelemetryStorage(file_path=temp_file, flush_interval=0.1)

        try:
            # Create and store some telemetry points
            point1 = TelemetryPoint(metric_name="test.metric1", value=1)
            point2 = TelemetryPoint(metric_name="test.metric2", value=2)
            point3 = TelemetryPoint(
                metric_name="test.metric3",
                value=3,
                source="test_source",
                tags={"tag1": "value1"},
            )

            storage.store(point1)
            storage.store(point2)
            storage.store(point3)

            # Wait for the flush interval to ensure data is written
            time.sleep(0.2)

            # Query all points
            points = storage.query()
            assert len(points) == 3
            assert points[0].metric_name == point1.metric_name
            assert points[0].value == point1.value
            assert points[1].metric_name == point2.metric_name
            assert points[1].value == point2.value
            assert points[2].metric_name == point3.metric_name
            assert points[2].value == point3.value
            assert points[2].source == point3.source
            assert points[2].tags == point3.tags

            # Query by metric name
            points = storage.query(metric_name="test.metric1")
            assert len(points) == 1
            assert points[0].metric_name == "test.metric1"

            # Query by source
            points = storage.query(source="test_source")
            assert len(points) == 1
            assert points[0].metric_name == "test.metric3"

            # Query by tags
            points = storage.query(tags={"tag1": "value1"})
            assert len(points) == 1
            assert points[0].metric_name == "test.metric3"
        finally:
            # Close the storage
            storage.close()


@pytest.fixture
def temp_db():
    """Fixture that provides a temporary SQLite database path."""
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)

    yield path

    # Clean up
    if os.path.exists(path):
        os.remove(path)


class TestSQLiteTelemetryStorage:
    """Tests for the SQLiteTelemetryStorage class."""

    def test_initialization(self, temp_db):
        """Test initializing the SQLite storage."""
        storage = SQLiteTelemetryStorage(db_path=temp_db)

        # Check that the database file was created
        assert os.path.exists(temp_db)

        # Check that the tables were created
        conn = sqlite3.connect(temp_db)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]
        conn.close()

        assert "telemetry" in tables

    def test_store_and_query(self, temp_db):
        """Test storing and querying telemetry points."""
        storage = SQLiteTelemetryStorage(db_path=temp_db)

        # Create and store some telemetry points
        point1 = TelemetryPoint(metric_name="test.metric1", value=1)
        point2 = TelemetryPoint(metric_name="test.metric2", value=2)
        point3 = TelemetryPoint(
            metric_name="test.metric3",
            value=3,
            source="test_source",
            tags={"tag1": "value1"},
        )
        point4 = TelemetryPoint(
            metric_name="test.metric4",
            value={"complex": "object", "nested": {"value": 42}},
        )

        storage.store(point1)
        storage.store(point2)
        storage.store(point3)
        storage.store(point4)

        # Query all points
        points = storage.query()
        assert len(points) == 4

        # Points are ordered by timestamp DESC, so the most recent is first
        assert points[3].metric_name == "test.metric1"
        assert points[3].value == "1"  # SQLite stores as string
        assert points[2].metric_name == "test.metric2"
        assert points[2].value == "2"
        assert points[1].metric_name == "test.metric3"
        assert points[1].value == "3"
        assert points[1].source == "test_source"
        assert points[1].tags == {"tag1": "value1"}
        assert points[0].metric_name == "test.metric4"
        assert isinstance(points[0].value, dict)
        assert points[0].value["complex"] == "object"
        assert points[0].value["nested"]["value"] == 42

        # Query by metric name
        points = storage.query(metric_name="test.metric1")
        assert len(points) == 1
        assert points[0].metric_name == "test.metric1"

        # Query by source
        points = storage.query(source="test_source")
        assert len(points) == 1
        assert points[0].metric_name == "test.metric3"

        # Query by tags
        points = storage.query(tags={"tag1": "value1"})
        assert len(points) == 1
        assert points[0].metric_name == "test.metric3"

        # Query with limit
        points = storage.query(limit=2)
        assert len(points) == 2
        assert points[0].metric_name == "test.metric4"
        assert points[1].metric_name == "test.metric3"


class TestTelemetryCollector:
    """Tests for the TelemetryCollector class."""

    @pytest.fixture
    def collector(self):
        """Fixture that provides a telemetry collector with memory storage."""
        storage = MemoryTelemetryStorage(max_points=100)
        collector = TelemetryCollector(storage=storage, collection_interval=0.1)

        yield collector

        # Stop the collector if it's running
        if collector.running:
            collector.stop()

    def test_record(self, collector):
        """Test recording individual telemetry points."""
        # Record some metrics
        collector.record(metric_name="test.metric1", value=1)
        collector.record(
            metric_name="test.metric2",
            value=2,
            source="test_source",
            tags={"tag1": "value1"},
        )

        # Query the metrics
        points = collector.query()
        assert len(points) == 2
        assert points[0].metric_name == "test.metric1"
        assert points[0].value == 1
        assert points[1].metric_name == "test.metric2"
        assert points[1].value == 2
        assert points[1].source == "test_source"
        assert points[1].tags == {"tag1": "value1"}

    def test_register_collector(self, collector):
        """Test registering and collecting from collector functions."""

        # Define some collector functions
        def collector1():
            return {
                "metric1": 1,
                "metric2": 2,
            }

        def collector2():
            return {
                "metric3": 3,
            }

        # Register the collectors
        collector.register_collector("test_collector1", collector1)
        collector.register_collector("test_collector2", collector2)

        # Collect data
        points = collector.collect()

        # Check that the expected points were collected
        assert len(points) == 3
        metric_names = [p.metric_name for p in points]
        assert "test_collector1.metric1" in metric_names
        assert "test_collector1.metric2" in metric_names
        assert "test_collector2.metric3" in metric_names

    def test_unregister_collector(self, collector):
        """Test unregistering collector functions."""

        # Define some collector functions
        def collector1():
            return {
                "metric1": 1,
            }

        def collector2():
            return {
                "metric2": 2,
            }

        # Register the collectors
        collector.register_collector("test_collector1", collector1)
        collector.register_collector("test_collector2", collector2)

        # Unregister one collector
        collector.unregister_collector("test_collector1")

        # Collect data
        points = collector.collect()

        # Check that only the expected points were collected
        assert len(points) == 1
        assert points[0].metric_name == "test_collector2.metric2"

    def test_start_stop(self, collector):
        """Test starting and stopping the collector."""
        # Define a collector function
        values = [0]

        def test_collector():
            values[0] += 1
            return {"value": values[0]}

        # Register the collector
        collector.register_collector("test", test_collector)

        # Start the collector
        collector.start()

        # Wait for a few collection cycles
        time.sleep(0.25)

        # Stop the collector
        collector.stop()

        # Query the collected data
        points = collector.query(metric_name="test.value")

        # Check that some data was collected
        assert len(points) > 0
        values = [p.value for p in points]
        assert values == list(range(1, len(values) + 1))


class TestGlobalTelemetryFunctions:
    """Tests for the global telemetry functions."""

    @pytest.fixture
    def clean_state(self):
        """Fixture that ensures a clean global telemetry state."""
        # Stop any running collector
        stop_telemetry_collection()

        # Save and clear the global collector
        global_collector = getattr(
            get_telemetry_collector.__globals__, "_telemetry_collector", None
        )
        setattr(get_telemetry_collector.__globals__, "_telemetry_collector", None)

        yield

        # Restore the global collector
        setattr(
            get_telemetry_collector.__globals__,
            "_telemetry_collector",
            global_collector,
        )

        # Ensure any running collector is stopped
        stop_telemetry_collection()

    def test_get_telemetry_collector(self, clean_state):
        """Test getting the global telemetry collector."""
        collector = get_telemetry_collector()
        assert isinstance(collector, TelemetryCollector)

        # Check that it returns the same instance
        collector2 = get_telemetry_collector()
        assert collector is collector2

        # Check that a storage is created
        assert isinstance(collector.storage, SQLiteTelemetryStorage)

    def test_record_telemetry(self, clean_state):
        """Test recording telemetry using the global function."""
        # Record some metrics
        record_telemetry("test.metric1", 1)
        record_telemetry(
            metric_name="test.metric2",
            value=2,
            source="test_source",
            tags={"tag1": "value1"},
        )

        # Get the collector and query the metrics
        collector = get_telemetry_collector()
        points = collector.query()
        assert len(points) == 2
        assert points[0].metric_name == "test.metric1"
        assert points[0].value == 1
        assert points[1].metric_name == "test.metric2"
        assert points[1].value == 2
        assert points[1].source == "test_source"
        assert points[1].tags == {"tag1": "value1"}

    def test_register_telemetry_collector(self, clean_state):
        """Test registering a telemetry collector using the global function."""

        # Define a collector function
        def test_collector():
            return {"metric1": 1}

        # Register the collector
        register_telemetry_collector("test", test_collector)

        # Get the collector and check that the function was registered
        collector = get_telemetry_collector()
        assert "test" in collector.collectors
        assert collector.collectors["test"] is test_collector

        # Unregister the collector
        unregister_telemetry_collector("test")
        assert "test" not in collector.collectors

    @patch(
        "pathfinder_pkg.diagnostics.telemetry.telemetry_collector.register_system_collectors"
    )
    def test_start_stop_telemetry_collection(
        self, mock_register_system_collectors, clean_state
    ):
        """Test starting and stopping telemetry collection."""
        # Start collection
        start_telemetry_collection()

        # Check that the collector is running
        collector = get_telemetry_collector()
        assert collector.running
        assert collector.collection_thread is not None
        assert collector.collection_thread.is_alive()

        # Check that system collectors were registered
        mock_register_system_collectors.assert_called_once()

        # Stop collection
        stop_telemetry_collection()

        # Check that the collector is stopped
        assert not collector.running
        assert (
            collector.collection_thread is None
            or not collector.collection_thread.is_alive()
        )
