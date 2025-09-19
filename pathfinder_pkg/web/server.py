"""
Web server module for PathfinderBot.

This module provides a Flask-based web server with responsive
design for controlling and monitoring the PathfinderBot.
"""

import os
import json
import time
import threading
from pathlib import Path
from datetime import datetime
from flask import (
    Flask,
    render_template,
    Response,
    request,
    jsonify,
    send_from_directory,
)
from pathfinder_pkg.utils.logging import get_logger

logger = get_logger(__name__)


class WebServer:
    """
    Web server for PathfinderBot control interface.

    This class implements a Flask-based web server that provides
    a responsive interface for controlling and monitoring the robot.

    Attributes:
        app (Flask): The Flask application instance.
        host (str): Host address to bind the server to.
        port (int): Port to listen on.
        static_folder (str): Path to static files (HTML, CSS, JS, etc.).
        template_folder (str): Path to template files.
        robot: The robot instance to control.
        ws_server: WebSocket server instance for real-time communication.
        record_path (str): Path to store recording files.
        recording (bool): Whether recording is active.
        playback (bool): Whether playback is active.
    """

    def __init__(
        self,
        host="0.0.0.0",
        port=5000,
        static_folder=None,
        template_folder=None,
        robot=None,
        ws_server=None,
    ):
        """
        Initialize the web server.

        Args:
            host (str, optional): Host address to bind the server to.
            port (int, optional): Port to listen on.
            static_folder (str, optional): Path to static files.
            template_folder (str, optional): Path to template files.
            robot: The robot instance to control.
            ws_server: WebSocket server instance for real-time communication.
        """
        self.host = host
        self.port = port

        # Set up paths
        pkg_dir = Path(__file__).parent.parent
        self.static_folder = static_folder or str(pkg_dir / "web" / "static")
        self.template_folder = template_folder or str(pkg_dir / "web" / "templates")

        # Create Flask app
        self.app = Flask(
            __name__,
            static_folder=self.static_folder,
            template_folder=self.template_folder,
        )

        self.robot = robot
        self.ws_server = ws_server

        # Recording and playback
        self.record_path = os.path.join(self.static_folder, "recordings")
        os.makedirs(self.record_path, exist_ok=True)
        self.recording = False
        self.playback = False
        self._record_thread = None
        self._playback_thread = None

        # Register routes
        self._register_routes()

    def _register_routes(self):
        """Register the Flask routes."""
        app = self.app

        # Home page
        @app.route("/")
        def index():
            return render_template("index.html")

        # Drive interface
        @app.route("/drive")
        def drive():
            return render_template("drive.html")

        # Arm control interface
        @app.route("/arm")
        def arm():
            return render_template("arm.html")

        # Block detection interface
        @app.route("/blocks")
        def blocks():
            return render_template("blocks.html")

        # Telemetry dashboard
        @app.route("/telemetry")
        def telemetry():
            return render_template("telemetry.html")

        # Settings page
        @app.route("/settings")
        def settings():
            return render_template("settings.html")

        # API endpoints
        @app.route("/api/status")
        def api_status():
            return jsonify(
                {
                    "status": "ok",
                    "robot_connected": self.robot is not None,
                    "websocket_active": self.ws_server is not None
                    and getattr(self.ws_server, "running", False),
                    "time": time.time(),
                }
            )

        @app.route("/api/robot/move", methods=["POST"])
        def api_robot_move():
            data = request.json
            if not self.robot:
                return (
                    jsonify({"status": "error", "message": "Robot not connected"}),
                    503,
                )

            try:
                x = float(data.get("x", 0))
                y = float(data.get("y", 0))
                rotation = float(data.get("rotation", 0))

                # Apply movement
                if hasattr(self.robot, "set_velocity"):
                    self.robot.set_velocity(x, y, rotation)
                elif hasattr(self.robot, "translation"):
                    if abs(rotation) < 0.01:
                        self.robot.translation(x, y)
                    else:
                        self.robot.rotation(rotation)

                return jsonify({"status": "ok"})
            except Exception as e:
                logger.error(f"Error moving robot: {e}")
                return jsonify({"status": "error", "message": str(e)}), 500

        @app.route("/api/robot/stop", methods=["POST"])
        def api_robot_stop():
            if not self.robot:
                return (
                    jsonify({"status": "error", "message": "Robot not connected"}),
                    503,
                )

            try:
                if hasattr(self.robot, "stop"):
                    self.robot.stop()
                elif hasattr(self.robot, "reset_motors"):
                    self.robot.reset_motors()

                return jsonify({"status": "ok"})
            except Exception as e:
                logger.error(f"Error stopping robot: {e}")
                return jsonify({"status": "error", "message": str(e)}), 500

        # Recording and playback
        @app.route("/api/recording/start", methods=["POST"])
        def api_recording_start():
            if self.recording:
                return jsonify({"status": "error", "message": "Already recording"})

            try:
                filename = request.json.get("filename")
                if not filename:
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    filename = f"recording_{timestamp}.json"

                self.start_recording(filename)
                return jsonify({"status": "ok", "filename": filename})
            except Exception as e:
                logger.error(f"Error starting recording: {e}")
                return jsonify({"status": "error", "message": str(e)}), 500

        @app.route("/api/recording/stop", methods=["POST"])
        def api_recording_stop():
            if not self.recording:
                return jsonify({"status": "error", "message": "Not recording"})

            try:
                self.stop_recording()
                return jsonify({"status": "ok"})
            except Exception as e:
                logger.error(f"Error stopping recording: {e}")
                return jsonify({"status": "error", "message": str(e)}), 500

        @app.route("/api/recording/list")
        def api_recording_list():
            try:
                recordings = []
                for file in os.listdir(self.record_path):
                    if file.endswith(".json"):
                        path = os.path.join(self.record_path, file)
                        size = os.path.getsize(path)
                        mtime = os.path.getmtime(path)
                        recordings.append(
                            {"filename": file, "size": size, "modified": mtime}
                        )

                recordings.sort(key=lambda x: x["modified"], reverse=True)
                return jsonify({"status": "ok", "recordings": recordings})
            except Exception as e:
                logger.error(f"Error listing recordings: {e}")
                return jsonify({"status": "error", "message": str(e)}), 500

        @app.route("/api/recording/play", methods=["POST"])
        def api_recording_play():
            if self.playback:
                return jsonify({"status": "error", "message": "Already playing back"})

            try:
                filename = request.json.get("filename")
                if not filename:
                    return jsonify(
                        {"status": "error", "message": "No filename provided"}
                    )

                self.start_playback(filename)
                return jsonify({"status": "ok", "filename": filename})
            except Exception as e:
                logger.error(f"Error starting playback: {e}")
                return jsonify({"status": "error", "message": str(e)}), 500

        @app.route("/api/recording/stop_playback", methods=["POST"])
        def api_recording_stop_playback():
            if not self.playback:
                return jsonify({"status": "error", "message": "Not playing back"})

            try:
                self.stop_playback()
                return jsonify({"status": "ok"})
            except Exception as e:
                logger.error(f"Error stopping playback: {e}")
                return jsonify({"status": "error", "message": str(e)}), 500

        @app.route("/api/recording/download/<filename>")
        def api_recording_download(filename):
            try:
                return send_from_directory(
                    self.record_path, filename, as_attachment=True
                )
            except Exception as e:
                logger.error(f"Error downloading recording: {e}")
                return jsonify({"status": "error", "message": str(e)}), 500

    def start(self, debug=False, threaded=True):
        """
        Start the web server.

        Args:
            debug (bool, optional): Whether to run in debug mode.
            threaded (bool, optional): Whether to run with threading.

        Returns:
            The result of app.run().
        """
        logger.info(f"Starting web server on {self.host}:{self.port}")
        return self.app.run(
            host=self.host, port=self.port, debug=debug, threaded=threaded
        )

    def start_recording(self, filename):
        """
        Start recording robot telemetry and commands.

        Args:
            filename (str): The filename to save the recording to.
        """
        if self.recording:
            logger.warning("Already recording")
            return

        self.recording = True

        # Make sure the directory exists
        os.makedirs(self.record_path, exist_ok=True)

        # Start recording in a separate thread
        def record_loop():
            filepath = os.path.join(self.record_path, filename)
            try:
                with open(filepath, "w") as f:
                    f.write('{"recordings":[\n')

                    last_write = time.time()
                    first_entry = True

                    while self.recording:
                        # Only record at a reasonable rate (e.g., 10 Hz)
                        now = time.time()
                        if now - last_write < 0.1:
                            time.sleep(0.01)
                            continue

                        # Get telemetry data
                        data = {}
                        if self.robot:
                            # Similar to WebSocket telemetry data
                            data = {
                                "timestamp": now,
                                "motors": getattr(
                                    self.robot, "get_motor_positions", lambda: []
                                )(),
                            }

                            # Add component data if available
                            if hasattr(self.robot, "get_component"):
                                for comp_name in ["camera", "sonar", "imu"]:
                                    comp = self.robot.get_component(comp_name)
                                    if comp:
                                        try:
                                            if hasattr(comp, "get_data"):
                                                data[comp_name] = comp.get_data()
                                            elif hasattr(comp, "get_reading"):
                                                data[comp_name] = comp.get_reading()
                                        except:
                                            pass

                        # Write to file
                        if not first_entry:
                            f.write(",\n")
                        else:
                            first_entry = False

                        json.dump({"time": now, "data": data}, f)
                        last_write = now

                    # Close the JSON array
                    f.write("\n]}\n")
                logger.info(f"Recording saved to {filepath}")
            except Exception as e:
                logger.error(f"Error during recording: {e}")
                self.recording = False

        self._record_thread = threading.Thread(target=record_loop)
        self._record_thread.daemon = True
        self._record_thread.start()

        logger.info(f"Started recording to {filename}")

    def stop_recording(self):
        """Stop recording."""
        if not self.recording:
            logger.warning("Not recording")
            return

        self.recording = False
        if self._record_thread:
            self._record_thread.join(timeout=2.0)
            self._record_thread = None

        logger.info("Recording stopped")

    def start_playback(self, filename):
        """
        Start playing back a recording.

        Args:
            filename (str): The filename to play back.
        """
        if self.playback:
            logger.warning("Already playing back")
            return

        filepath = os.path.join(self.record_path, filename)
        if not os.path.exists(filepath):
            raise FileNotFoundError(f"Recording file not found: {filepath}")

        self.playback = True

        # Start playback in a separate thread
        def playback_loop():
            try:
                with open(filepath, "r") as f:
                    recording = json.load(f)
                    entries = recording.get("recordings", [])

                    if not entries:
                        logger.warning(f"No entries found in recording: {filename}")
                        self.playback = False
                        return

                    # Get the first timestamp to use as a reference
                    start_time = entries[0]["time"]
                    real_start_time = time.time()

                    for i, entry in enumerate(entries):
                        if not self.playback:
                            break

                        # Calculate the time when this entry should be played
                        entry_offset = entry["time"] - start_time
                        play_at = real_start_time + entry_offset

                        # Wait until it's time to play this entry
                        wait_time = play_at - time.time()
                        if wait_time > 0:
                            time.sleep(wait_time)

                        # Apply the data if applicable
                        if self.robot and self.ws_server:
                            try:
                                # Broadcast telemetry via WebSocket
                                asyncio.run_coroutine_threadsafe(
                                    self.ws_server.broadcast(
                                        {"type": "playback", "data": entry["data"]}
                                    ),
                                    self.ws_server.loop,
                                )

                                # TODO: Actually control the robot based on the recorded data
                                # This would require additional data in the recording

                            except Exception as e:
                                logger.error(f"Error applying playback data: {e}")

                logger.info(f"Playback of {filename} completed")
            except Exception as e:
                logger.error(f"Error during playback: {e}")
            finally:
                self.playback = False

        self._playback_thread = threading.Thread(target=playback_loop)
        self._playback_thread.daemon = True
        self._playback_thread.start()

        logger.info(f"Started playback of {filename}")

    def stop_playback(self):
        """Stop playback."""
        if not self.playback:
            logger.warning("Not playing back")
            return

        self.playback = False
        if self._playback_thread:
            self._playback_thread.join(timeout=2.0)
            self._playback_thread = None

        logger.info("Playback stopped")


# Import asyncio for WebSocket communication
import asyncio
