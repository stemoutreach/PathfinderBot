"""
Debugging tools for PathfinderBot.

This module provides tools for debugging and diagnosing issues in the PathfinderBot system.
"""

import inspect
import logging
import os
import sys
import time
import threading
import traceback
from typing import Any, Dict, List, Optional, Set, Tuple, Callable, Union
import json
import pprint

from pathfinder_pkg.reliability.error_handling.errors import (
    register_error,
    SoftwareError,
    ErrorSeverity,
)

# Setup module logger
logger = logging.getLogger(__name__)


class DebugContext:
    """
    Context manager for debugging code blocks.

    This class provides a context manager that can be used to track execution time,
    log entry and exit, and capture variables for debugging purposes.
    """

    def __init__(
        self,
        name: str,
        log_level: int = logging.DEBUG,
        capture_vars: bool = False,
        log_entry_exit: bool = True,
    ):
        """
        Initialize a new debug context.

        Args:
            name: Name of the context (for logging)
            log_level: Logging level for messages
            capture_vars: Whether to capture local variables
            log_entry_exit: Whether to log entry and exit
        """
        self.name = name
        self.log_level = log_level
        self.capture_vars = capture_vars
        self.log_entry_exit = log_entry_exit
        self.start_time = 0
        self.end_time = 0
        self.duration = 0

    def __enter__(self) -> "DebugContext":
        """Enter the debug context."""
        self.start_time = time.time()

        if self.log_entry_exit:
            caller_frame = inspect.currentframe().f_back
            caller_info = inspect.getframeinfo(caller_frame)
            logger.log(
                self.log_level,
                f"ENTER {self.name} at {caller_info.filename}:{caller_info.lineno}",
            )

        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> bool:
        """
        Exit the debug context.

        Args:
            exc_type: Exception type, if an exception was raised
            exc_val: Exception value, if an exception was raised
            exc_tb: Exception traceback, if an exception was raised

        Returns:
            True if the exception should be suppressed, False otherwise
        """
        self.end_time = time.time()
        self.duration = self.end_time - self.start_time

        if self.log_entry_exit:
            if exc_type is None:
                logger.log(
                    self.log_level,
                    f"EXIT {self.name} (duration: {self.duration:.6f}s)",
                )
            else:
                logger.log(
                    self.log_level,
                    f"EXIT {self.name} with exception {exc_type.__name__}: {exc_val} "
                    f"(duration: {self.duration:.6f}s)",
                )

        if self.capture_vars and exc_type is None:
            caller_frame = inspect.currentframe().f_back
            local_vars = {
                name: value
                for name, value in caller_frame.f_locals.items()
                if not name.startswith("__")
            }
            logger.log(
                self.log_level,
                f"VARS {self.name}: {pprint.pformat(local_vars)}",
            )

        return False  # Don't suppress exceptions


def debug_context(
    name: Optional[str] = None,
    log_level: int = logging.DEBUG,
    capture_vars: bool = False,
    log_entry_exit: bool = True,
) -> DebugContext:
    """
    Create a debug context.

    Args:
        name: Name of the context (if None, the caller function name will be used)
        log_level: Logging level for messages
        capture_vars: Whether to capture local variables
        log_entry_exit: Whether to log entry and exit

    Returns:
        A debug context manager
    """
    if name is None:
        caller_frame = inspect.currentframe().f_back
        name = caller_frame.f_code.co_name

    return DebugContext(
        name=name,
        log_level=log_level,
        capture_vars=capture_vars,
        log_entry_exit=log_entry_exit,
    )


class Breakpoint:
    """
    Breakpoint for debugging.

    This class provides a way to set breakpoints in code that will
    trigger a callback when hit.
    """

    _breakpoints: Dict[str, "Breakpoint"] = {}

    def __init__(
        self,
        name: str,
        callback: Optional[Callable[["Breakpoint"], None]] = None,
        condition: Optional[Callable[[], bool]] = None,
        enabled: bool = True,
    ):
        """
        Initialize a new breakpoint.

        Args:
            name: Name of the breakpoint
            callback: Function to call when the breakpoint is hit
            condition: Function that returns True if the breakpoint should be triggered
            enabled: Whether the breakpoint is enabled
        """
        self.name = name
        self.callback = callback
        self.condition = condition
        self.enabled = enabled
        self.hit_count = 0
        self.last_hit_time = 0
        self.locals_snapshot = {}

        # Register the breakpoint
        Breakpoint._breakpoints[name] = self

    def hit(self) -> bool:
        """
        Signal that the breakpoint has been hit.

        Returns:
            True if the breakpoint triggered the callback, False otherwise
        """
        if not self.enabled:
            return False

        if self.condition is not None and not self.condition():
            return False

        self.hit_count += 1
        self.last_hit_time = time.time()

        # Capture local variables
        caller_frame = inspect.currentframe().f_back
        self.locals_snapshot = {
            name: value
            for name, value in caller_frame.f_locals.items()
            if not name.startswith("__")
        }

        # Call the callback
        if self.callback is not None:
            try:
                self.callback(self)
            except Exception as e:
                logger.error(f"Error in breakpoint callback: {e}")
                logger.error(traceback.format_exc())

        return True

    @classmethod
    def get(cls, name: str) -> Optional["Breakpoint"]:
        """
        Get a breakpoint by name.

        Args:
            name: Name of the breakpoint

        Returns:
            The breakpoint, or None if not found
        """
        return cls._breakpoints.get(name)

    @classmethod
    def enable(cls, name: str) -> bool:
        """
        Enable a breakpoint.

        Args:
            name: Name of the breakpoint

        Returns:
            True if the breakpoint was found and enabled, False otherwise
        """
        bp = cls.get(name)
        if bp is not None:
            bp.enabled = True
            return True
        return False

    @classmethod
    def disable(cls, name: str) -> bool:
        """
        Disable a breakpoint.

        Args:
            name: Name of the breakpoint

        Returns:
            True if the breakpoint was found and disabled, False otherwise
        """
        bp = cls.get(name)
        if bp is not None:
            bp.enabled = False
            return True
        return False

    @classmethod
    def list_breakpoints(cls) -> List[str]:
        """
        Get a list of all breakpoints.

        Returns:
            List of breakpoint names
        """
        return list(cls._breakpoints.keys())


def set_breakpoint(
    name: str,
    callback: Optional[Callable[[Breakpoint], None]] = None,
    condition: Optional[Callable[[], bool]] = None,
    enabled: bool = True,
) -> Breakpoint:
    """
    Set a breakpoint.

    Args:
        name: Name of the breakpoint
        callback: Function to call when the breakpoint is hit
        condition: Function that returns True if the breakpoint should be triggered
        enabled: Whether the breakpoint is enabled

    Returns:
        The created breakpoint
    """
    return Breakpoint(
        name=name,
        callback=callback,
        condition=condition,
        enabled=enabled,
    )


def hit_breakpoint(name: str) -> bool:
    """
    Signal that a breakpoint has been hit.

    Args:
        name: Name of the breakpoint

    Returns:
        True if the breakpoint was found and triggered, False otherwise
    """
    bp = Breakpoint.get(name)
    if bp is not None:
        return bp.hit()
    return False


class CallTracer:
    """
    Function call tracer for debugging.

    This class provides a way to trace function calls and their arguments.
    """

    def __init__(
        self,
        max_depth: int = 10,
        log_level: int = logging.DEBUG,
        include_args: bool = True,
        include_return: bool = True,
    ):
        """
        Initialize a new call tracer.

        Args:
            max_depth: Maximum depth of nested calls to trace
            log_level: Logging level for messages
            include_args: Whether to include function arguments in trace messages
            include_return: Whether to include return values in trace messages
        """
        self.max_depth = max_depth
        self.log_level = log_level
        self.include_args = include_args
        self.include_return = include_return
        self.depth = 0
        self.enabled = False
        self.traced_functions: Set[Callable] = set()

    def __call__(self, func: Callable) -> Callable:
        """
        Decorator for tracing function calls.

        Args:
            func: Function to trace

        Returns:
            Wrapped function that will be traced
        """
        # Register the function as traced
        self.traced_functions.add(func)

        def wrapper(*args: Any, **kwargs: Any) -> Any:
            if not self.enabled:
                return func(*args, **kwargs)

            # Increment depth
            self.depth += 1
            indent = " " * (self.depth - 1) * 2

            # Log function call
            call_str = f"{func.__name__}()"
            if self.include_args:
                arg_strs = []
                for arg in args:
                    try:
                        arg_str = str(arg)
                        if len(arg_str) > 100:
                            arg_str = arg_str[:97] + "..."
                        arg_strs.append(arg_str)
                    except Exception as e:
                        arg_strs.append(f"<error: {e}>")

                kwarg_strs = []
                for key, value in kwargs.items():
                    try:
                        value_str = str(value)
                        if len(value_str) > 100:
                            value_str = value_str[:97] + "..."
                        kwarg_strs.append(f"{key}={value_str}")
                    except Exception as e:
                        kwarg_strs.append(f"{key}=<error: {e}>")

                args_str = ", ".join(arg_strs + kwarg_strs)
                call_str = f"{func.__name__}({args_str})"

            logger.log(self.log_level, f"{indent}CALL {call_str}")

            # Call the function
            start_time = time.time()
            try:
                result = func(*args, **kwargs)

                # Log function return
                duration = time.time() - start_time
                return_str = "void"
                if self.include_return:
                    try:
                        return_str = str(result)
                        if len(return_str) > 100:
                            return_str = return_str[:97] + "..."
                    except Exception as e:
                        return_str = f"<error: {e}>"

                logger.log(
                    self.log_level,
                    f"{indent}RETURN {func.__name__} -> {return_str} ({duration:.6f}s)",
                )

                return result
            except Exception as e:
                # Log function exception
                duration = time.time() - start_time
                logger.log(
                    self.log_level,
                    f"{indent}EXCEPTION {func.__name__} -> {type(e).__name__}: {e} ({duration:.6f}s)",
                )
                raise
            finally:
                # Decrement depth
                self.depth -= 1

        return wrapper

    def start(self) -> None:
        """Start tracing."""
        self.enabled = True
        logger.info("Call tracing started")

    def stop(self) -> None:
        """Stop tracing."""
        self.enabled = False
        logger.info("Call tracing stopped")


# Global call tracer instance
call_tracer = CallTracer()


def trace(func: Callable) -> Callable:
    """
    Decorator for tracing function calls.

    Args:
        func: Function to trace

    Returns:
        Wrapped function that will be traced
    """
    return call_tracer(func)


class StateRecorder:
    """
    State recorder for debugging.

    This class provides a way to record the state of variables over time
    for later analysis.
    """

    def __init__(
        self,
        max_records: int = 1000,
        record_on_change: bool = True,
    ):
        """
        Initialize a new state recorder.

        Args:
            max_records: Maximum number of records to keep
            record_on_change: Whether to only record when the value changes
        """
        self.max_records = max_records
        self.record_on_change = record_on_change
        self.records: Dict[str, List[Tuple[float, Any]]] = {}
        self.last_values: Dict[str, Any] = {}
        self.enabled = True

    def record(self, name: str, value: Any) -> None:
        """
        Record a variable's value.

        Args:
            name: Name of the variable
            value: Value of the variable
        """
        if not self.enabled:
            return

        # Check if the value has changed
        if self.record_on_change and name in self.last_values:
            try:
                if self.last_values[name] == value:
                    return
            except Exception:
                # If comparison fails, assume the value has changed
                pass

        # Initialize record list if needed
        if name not in self.records:
            self.records[name] = []

        # Add record
        timestamp = time.time()
        self.records[name].append((timestamp, value))
        self.last_values[name] = value

        # Trim records if needed
        if len(self.records[name]) > self.max_records:
            self.records[name] = self.records[name][-self.max_records :]

    def get_records(
        self,
        name: str,
        start_time: Optional[float] = None,
        end_time: Optional[float] = None,
    ) -> List[Tuple[float, Any]]:
        """
        Get records for a variable.

        Args:
            name: Name of the variable
            start_time: Start time for filtering records (inclusive)
            end_time: End time for filtering records (inclusive)

        Returns:
            List of (timestamp, value) tuples
        """
        if name not in self.records:
            return []

        records = self.records[name]

        # Apply time filters
        if start_time is not None:
            records = [r for r in records if r[0] >= start_time]
        if end_time is not None:
            records = [r for r in records if r[0] <= end_time]

        return records

    def get_last_value(self, name: str) -> Any:
        """
        Get the last recorded value for a variable.

        Args:
            name: Name of the variable

        Returns:
            The last recorded value, or None if no records exist
        """
        if name not in self.records or not self.records[name]:
            return None
        return self.records[name][-1][1]

    def clear(self, name: Optional[str] = None) -> None:
        """
        Clear records.

        Args:
            name: Name of the variable to clear (if None, clear all records)
        """
        if name is not None:
            if name in self.records:
                self.records[name] = []
            if name in self.last_values:
                del self.last_values[name]
        else:
            self.records = {}
            self.last_values = {}

    def enable(self) -> None:
        """Enable recording."""
        self.enabled = True

    def disable(self) -> None:
        """Disable recording."""
        self.enabled = False

    def dump_to_file(self, file_path: str) -> bool:
        """
        Dump records to a file in JSON format.

        Args:
            file_path: Path to the file

        Returns:
            True if successful, False otherwise
        """
        try:
            # Prepare data for serialization
            data = {}
            for name, records in self.records.items():
                # We need to convert non-serializable objects to strings
                serializable_records = []
                for timestamp, value in records:
                    try:
                        # Try to serialize the value directly
                        json.dumps(value)
                        serializable_value = value
                    except (TypeError, OverflowError):
                        # If that fails, convert to string
                        serializable_value = str(value)

                    serializable_records.append([timestamp, serializable_value])

                data[name] = serializable_records

            # Write to file
            with open(file_path, "w") as f:
                json.dump(data, f, indent=2)

            return True
        except Exception as e:
            logger.error(f"Failed to dump records to file: {e}")
            logger.error(traceback.format_exc())
            return False


# Global state recorder instance
state_recorder = StateRecorder()


def record_state(name: str, value: Any) -> None:
    """
    Record a variable's state.

    Args:
        name: Name of the variable
        value: Value of the variable
    """
    state_recorder.record(name, value)


class RemoteDebugServer:
    """
    Remote debugging server.

    This class provides a simple server for remote debugging.
    """

    def __init__(self, host: str = "localhost", port: int = 8888):
        """
        Initialize a new remote debug server.

        Args:
            host: Host to bind to
            port: Port to bind to
        """
        self.host = host
        self.port = port
        self.server = None
        self.thread = None
        self.running = False

    def start(self) -> bool:
        """
        Start the debug server.

        Returns:
            True if the server was started successfully, False otherwise
        """
        if self.running:
            logger.warning("Debug server already running")
            return False

        try:
            import socket

            # Create socket
            self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server.bind((self.host, self.port))
            self.server.listen(1)

            # Start server thread
            self.running = True
            self.thread = threading.Thread(
                target=self._server_loop,
                name="debug-server",
                daemon=True,
            )
            self.thread.start()

            logger.info(f"Debug server started on {self.host}:{self.port}")
            return True

        except Exception as e:
            logger.error(f"Failed to start debug server: {e}")
            logger.error(traceback.format_exc())
            return False

    def stop(self) -> bool:
        """
        Stop the debug server.

        Returns:
            True if the server was stopped successfully, False otherwise
        """
        if not self.running:
            logger.warning("Debug server not running")
            return False

        try:
            self.running = False

            if self.server:
                self.server.close()

            if self.thread:
                self.thread.join(timeout=2.0)

            logger.info("Debug server stopped")
            return True

        except Exception as e:
            logger.error(f"Failed to stop debug server: {e}")
            logger.error(traceback.format_exc())
            return False

    def _server_loop(self) -> None:
        """Server thread function."""
        import socket

        while self.running:
            try:
                # Wait for connection
                client, address = self.server.accept()
                logger.info(f"Debug client connected from {address}")

                # Handle client
                self._handle_client(client)

            except socket.timeout:
                continue

            except Exception as e:
                if self.running:
                    logger.error(f"Error in debug server: {e}")
                    logger.error(traceback.format_exc())

    def _handle_client(self, client: Any) -> None:
        """
        Handle a client connection.

        Args:
            client: Client socket
        """
        try:
            # Set timeout for client operations
            client.settimeout(1.0)

            # Handle client communication
            while self.running:
                try:
                    # Receive command
                    data = client.recv(4096)
                    if not data:
                        break

                    # Process command
                    command = data.decode("utf-8").strip()
                    response = self._process_command(command)

                    # Send response
                    client.send(response.encode("utf-8"))

                except TimeoutError:
                    continue

        except Exception as e:
            logger.error(f"Error handling debug client: {e}")
            logger.error(traceback.format_exc())

        finally:
            try:
                client.close()
                logger.info("Debug client disconnected")
            except Exception:
                pass

    def _process_command(self, command: str) -> str:
        """
        Process a debug command.

        Args:
            command: Command string

        Returns:
            Response string
        """
        try:
            # Parse command
            parts = command.split()
            if not parts:
                return "ERROR: Empty command"

            cmd = parts[0].lower()
            args = parts[1:]

            # Process command
            if cmd == "help":
                return self._cmd_help()
            elif cmd == "info":
                return self._cmd_info()
            elif cmd == "breakpoints":
                return self._cmd_breakpoints()
            elif cmd == "enable":
                if not args:
                    return "ERROR: Missing breakpoint name"
                return self._cmd_enable(args[0])
            elif cmd == "disable":
                if not args:
                    return "ERROR: Missing breakpoint name"
                return self._cmd_disable(args[0])
            elif cmd == "trace":
                if not args:
                    return "ERROR: Missing action (start/stop)"
                return self._cmd_trace(args[0])
            elif cmd == "state":
                if not args:
                    return "ERROR: Missing variable name"
                return self._cmd_state(args[0])
            else:
                return f"ERROR: Unknown command '{cmd}'"

        except Exception as e:
            logger.error(f"Error processing debug command: {e}")
            logger.error(traceback.format_exc())
            return f"ERROR: {type(e).__name__}: {e}"

    def _cmd_help(self) -> str:
        """
        Handle 'help' command.

        Returns:
            Response string
        """
        return (
            "Available commands:\n"
            "  help - Show this help message\n"
            "  info - Show system information\n"
            "  breakpoints - List breakpoints\n"
            "  enable <name> - Enable breakpoint\n"
            "  disable <name> - Disable breakpoint\n"
            "  trace start|stop - Start/stop call tracing\n"
            "  state <name> - Get state records for a variable\n"
        )

    def _cmd_info(self) -> str:
        """
        Handle 'info' command.

        Returns:
            Response string
        """
        import platform
        import sys

        return (
            f"PathfinderBot Debug Server\n"
            f"Python: {platform.python_version()}\n"
            f"Platform: {platform.platform()}\n"
            f"PID: {os.getpid()}\n"
            f"Threads: {threading.active_count()}\n"
        )

    def _cmd_breakpoints(self) -> str:
        """
        Handle 'breakpoints' command.

        Returns:
            Response string
        """
        breakpoints = Breakpoint.list_breakpoints()
        if not breakpoints:
            return "No breakpoints defined"

        result = "Breakpoints:\n"
        for name in breakpoints:
            bp = Breakpoint.get(name)
            if bp is None:
                continue

            result += f"  {name}: {'enabled' if bp.enabled else 'disabled'}, "
            result += f"hit {bp.hit_count} times"
            if bp.hit_count > 0:
                result += f", last hit at {time.ctime(bp.last_hit_time)}"
            result += "\n"

        return result

    def _cmd_enable(self, name: str) -> str:
        """
        Handle 'enable' command.

        Args:
            name: Breakpoint name

        Returns:
            Response string
        """
        if Breakpoint.enable(name):
            return f"Breakpoint '{name}' enabled"
        else:
            return f"ERROR: Breakpoint '{name}' not found"

    def _cmd_disable(self, name: str) -> str:
        """
        Handle 'disable' command.

        Args:
            name: Breakpoint name

        Returns:
            Response string
        """
        if Breakpoint.disable(name):
            return f"Breakpoint '{name}' disabled"
        else:
            return f"ERROR: Breakpoint '{name}' not found"

    def _cmd_trace(self, action: str) -> str:
        """
        Handle 'trace' command.

        Args:
            action: Action to perform (start/stop)

        Returns:
            Response string
        """
        if action.lower() == "start":
            call_tracer.start()
            return "Call tracing started"
        elif action.lower() == "stop":
            call_tracer.stop()
            return "Call tracing stopped"
        else:
            return f"ERROR: Invalid trace action '{action}', use 'start' or 'stop'"

    def _cmd_state(self, name: str) -> str:
        """
        Handle 'state' command.

        Args:
            name: Variable name

        Returns:
            Response string
        """
        records = state_recorder.get_records(name)
        if not records:
            return f"No records for variable '{name}'"

        result = f"Records for '{name}':\n"
        for timestamp, value in records:
            result += f"  {time.ctime(timestamp)}: {value}\n"

        return result


# Global remote debug server instance
remote_debug_server = RemoteDebugServer()


def start_debug_server(host: str = "localhost", port: int = 8888) -> bool:
    """
    Start the remote debug server.

    Args:
        host: Host to bind to
        port: Port to bind to

    Returns:
        True if the server was started successfully, False otherwise
    """
    global remote_debug_server
    remote_debug_server = RemoteDebugServer(host=host, port=port)
    return remote_debug_server.start()


def stop_debug_server() -> bool:
    """
    Stop the remote debug server.

    Returns:
        True if the server was stopped successfully, False otherwise
    """
    return remote_debug_server.stop()


def dump_stack(thread_id: Optional[int] = None) -> str:
    """
    Get a stack trace for a thread.

    Args:
        thread_id: Thread ID (if None, use current thread)

    Returns:
        Stack trace string
    """
    if thread_id is None:
        return "".join(traceback.format_stack())

    for thread in threading.enumerate():
        if thread.ident == thread_id:
            frame = sys._current_frames().get(thread_id)
            if frame is not None:
                return "".join(traceback.format_stack(frame))
            break

    return f"Thread {thread_id} not found or no stack information available"


def dump_threads() -> Dict[str, str]:
    """
    Get stack traces for all threads.

    Returns:
        Dictionary mapping thread names to stack traces
    """
    result = {}

    for thread in threading.enumerate():
        if thread.ident is None:
            continue

        frame = sys._current_frames().get(thread.ident)
        if frame is None:
            continue

        stack = "".join(traceback.format_stack(frame))
        result[thread.name] = stack

    return result
