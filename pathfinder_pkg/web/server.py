"""
Web server for PathfinderBot UI.

This module provides a web server for the PathfinderBot UI.
"""

import logging
import os
import threading
import time
from typing import Any, Dict, List, Optional, Union

import fastapi
from fastapi import FastAPI, Request, Response, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import uvicorn

from pathfinder_pkg.diagnostics.telemetry.telemetry_collector import (
    get_telemetry_collector,
    start_telemetry_collection,
)
from pathfinder_pkg.diagnostics.telemetry.websocket_handler import (
    start_telemetry_websocket,
)
from pathfinder_pkg.reliability.error_handling.errors import (
    register_error,
    SoftwareError,
    ErrorSeverity,
)
from pathfinder_pkg.reliability.resource_management.resource_monitor import (
    get_resource_monitor,
)

# Setup module logger
logger = logging.getLogger(__name__)

# Create the FastAPI app
app = FastAPI(
    title="PathfinderBot",
    description="Web interface for PathfinderBot",
    version="1.0.0",
)

# Define the path to the templates and static files
current_dir = os.path.dirname(os.path.abspath(__file__))
templates = Jinja2Templates(directory=os.path.join(current_dir, "templates"))

# Mount the static files directory
app.mount(
    "/static", StaticFiles(directory=os.path.join(current_dir, "static")), name="static"
)


@app.get("/", response_class=HTMLResponse)
async def root(request: Request) -> Response:
    """
    Render the home page.

    Args:
        request: FastAPI request object

    Returns:
        HTML response
    """
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/drive", response_class=HTMLResponse)
async def drive(request: Request) -> Response:
    """
    Render the drive control page.

    Args:
        request: FastAPI request object

    Returns:
        HTML response
    """
    return templates.TemplateResponse("drive.html", {"request": request})


@app.get("/telemetry", response_class=HTMLResponse)
async def telemetry(request: Request) -> Response:
    """
    Render the telemetry page.

    Args:
        request: FastAPI request object

    Returns:
        HTML response
    """
    return templates.TemplateResponse("telemetry.html", {"request": request})


@app.get("/api/system/status")
async def system_status() -> Dict[str, Any]:
    """
    Get the system status.

    Returns:
        System status information
    """
    # Get the resource monitor
    monitor = get_resource_monitor()
    if monitor is None:
        return {
            "status": "unavailable",
            "reason": "Resource monitor not initialized",
        }

    # Get system resources
    try:
        cpu_percent = monitor.get_cpu_percent()
        memory_percent = monitor.get_memory_percent()
        disk_percent = monitor.get_disk_percent()

        return {
            "status": "ok",
            "timestamp": time.time(),
            "cpu_percent": cpu_percent,
            "memory_percent": memory_percent,
            "disk_percent": disk_percent,
        }
    except Exception as e:
        logger.error(f"Error getting system status: {e}")
        register_error(
            SoftwareError(
                "Error getting system status",
                severity=ErrorSeverity.MEDIUM,
                cause=e,
            )
        )
        return {
            "status": "error",
            "reason": str(e),
        }


@app.get("/api/telemetry/metrics")
async def telemetry_metrics(
    metric_name: Optional[str] = None,
    source: Optional[str] = None,
    limit: int = 100,
) -> Dict[str, Any]:
    """
    Get telemetry metrics.

    Args:
        metric_name: Filter by metric name
        source: Filter by source
        limit: Maximum number of points to return

    Returns:
        Telemetry metrics
    """
    # Get the telemetry collector
    collector = get_telemetry_collector()
    if collector is None:
        return {
            "status": "unavailable",
            "reason": "Telemetry collector not initialized",
        }

    try:
        # Query the metrics
        points = collector.query(
            metric_name=metric_name,
            source=source,
            limit=limit,
        )

        # Convert to dictionary
        result = {
            "status": "ok",
            "timestamp": time.time(),
            "count": len(points),
            "metrics": [point.to_dict() for point in points],
        }

        return result
    except Exception as e:
        logger.error(f"Error getting telemetry metrics: {e}")
        register_error(
            SoftwareError(
                "Error getting telemetry metrics",
                severity=ErrorSeverity.MEDIUM,
                cause=e,
            )
        )
        return {
            "status": "error",
            "reason": str(e),
        }


@app.post("/api/telemetry/record")
async def record_telemetry(request: Request) -> Dict[str, Any]:
    """
    Record telemetry data.

    Args:
        request: FastAPI request object with JSON body containing:
            - metric_name: Name of the metric
            - value: Value of the metric
            - source: Source of the data (optional)
            - tags: Additional tags (optional)

    Returns:
        Status
    """
    # Get the telemetry collector
    collector = get_telemetry_collector()
    if collector is None:
        return {
            "status": "unavailable",
            "reason": "Telemetry collector not initialized",
        }

    try:
        # Parse the request body
        data = await request.json()
        if "metric_name" not in data or "value" not in data:
            return {
                "status": "error",
                "reason": "Missing required fields: metric_name, value",
            }

        # Record the telemetry
        collector.record(
            metric_name=data["metric_name"],
            value=data["value"],
            source=data.get("source"),
            tags=data.get("tags"),
        )

        return {
            "status": "ok",
            "timestamp": time.time(),
        }
    except Exception as e:
        logger.error(f"Error recording telemetry: {e}")
        register_error(
            SoftwareError(
                "Error recording telemetry",
                severity=ErrorSeverity.MEDIUM,
                cause=e,
            )
        )
        return {
            "status": "error",
            "reason": str(e),
        }


# Web server instance
server = None


def start_server(host: str = "0.0.0.0", port: int = 8000) -> None:
    """
    Start the web server.

    Args:
        host: Host to bind to
        port: Port to bind to
    """
    global server

    # Start telemetry collection
    start_telemetry_collection()

    # Start the telemetry WebSocket server
    start_telemetry_websocket()

    # Configure logging
    log_config = uvicorn.config.LOGGING_CONFIG
    log_config["loggers"]["uvicorn"]["level"] = "INFO"

    # Create the server
    server = uvicorn.Server(
        uvicorn.Config(
            app=app,
            host=host,
            port=port,
            log_config=log_config,
        )
    )

    # Run the server
    def run_server():
        server.run()

    # Start in a thread
    thread = threading.Thread(target=run_server, daemon=True)
    thread.start()

    logger.info(f"Web server started on http://{host}:{port}")


def stop_server() -> None:
    """Stop the web server."""
    global server
    if server:
        server.should_exit = True
        logger.info("Web server stopped")


if __name__ == "__main__":
    start_server()
