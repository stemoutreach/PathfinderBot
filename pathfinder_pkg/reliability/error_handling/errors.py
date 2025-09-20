"""
Error handling module for PathfinderBot.

This module defines a comprehensive error hierarchy and handling utilities
for the PathfinderBot system.
"""

import logging
import traceback
from enum import Enum, auto
from typing import Optional, Dict, Any, List, Callable, Union, TypeVar, Generic, Tuple

# Setup module logger
logger = logging.getLogger(__name__)


class ErrorSeverity(Enum):
    """Enumeration of error severity levels."""

    INFO = auto()  # Informational, not an error
    LOW = auto()  # Minor issue, can continue
    MEDIUM = auto()  # Significant issue, may affect functionality
    HIGH = auto()  # Serious issue, functionality degraded
    CRITICAL = auto()  # Fatal error, cannot continue


class ErrorCategory(Enum):
    """Enumeration of error categories."""

    HARDWARE = auto()  # Hardware-related errors
    SENSOR = auto()  # Sensor-related errors
    ACTUATOR = auto()  # Actuator-related errors
    COMMUNICATION = auto()  # Communication-related errors
    SOFTWARE = auto()  # Software-related errors
    RESOURCE = auto()  # Resource-related errors
    SECURITY = auto()  # Security-related errors
    CONFIGURATION = auto()  # Configuration-related errors
    USER = auto()  # User-related errors
    EXTERNAL = auto()  # External system errors
    UNKNOWN = auto()  # Unknown errors


class PathfinderError(Exception):
    """Base class for all PathfinderBot errors."""

    def __init__(
        self,
        message: str,
        severity: ErrorSeverity = ErrorSeverity.MEDIUM,
        category: ErrorCategory = ErrorCategory.UNKNOWN,
        details: Optional[Dict[str, Any]] = None,
        cause: Optional[Exception] = None,
    ):
        """
        Initialize a new PathfinderError.

        Args:
            message: Error message
            severity: Error severity level
            category: Error category
            details: Additional error details
            cause: Underlying cause of the error
        """
        self.message = message
        self.severity = severity
        self.category = category
        self.details = details or {}
        self.cause = cause
        self.timestamp = None  # Will be set when error is registered

        # Initialize with the error message
        super().__init__(message)

    def __str__(self) -> str:
        """Return string representation of the error."""
        result = f"{self.severity.name} {self.category.name} error: {self.message}"
        if self.details:
            result += f" Details: {self.details}"
        if self.cause:
            result += f" Caused by: {str(self.cause)}"
        return result

    def to_dict(self) -> Dict[str, Any]:
        """Convert error to a dictionary representation."""
        result = {
            "message": self.message,
            "severity": self.severity.name,
            "category": self.category.name,
            "details": self.details,
            "timestamp": self.timestamp,
        }
        if self.cause:
            result["cause"] = str(self.cause)
        return result


# Hardware errors
class HardwareError(PathfinderError):
    """Base class for hardware-related errors."""

    def __init__(
        self,
        message: str,
        severity: ErrorSeverity = ErrorSeverity.HIGH,
        details: Optional[Dict[str, Any]] = None,
        cause: Optional[Exception] = None,
    ):
        super().__init__(message, severity, ErrorCategory.HARDWARE, details, cause)


class SensorError(PathfinderError):
    """Base class for sensor-related errors."""

    def __init__(
        self,
        message: str,
        sensor_id: str,
        severity: ErrorSeverity = ErrorSeverity.MEDIUM,
        details: Optional[Dict[str, Any]] = None,
        cause: Optional[Exception] = None,
    ):
        details = details or {}
        details["sensor_id"] = sensor_id
        super().__init__(message, severity, ErrorCategory.SENSOR, details, cause)


class ActuatorError(PathfinderError):
    """Base class for actuator-related errors."""

    def __init__(
        self,
        message: str,
        actuator_id: str,
        severity: ErrorSeverity = ErrorSeverity.MEDIUM,
        details: Optional[Dict[str, Any]] = None,
        cause: Optional[Exception] = None,
    ):
        details = details or {}
        details["actuator_id"] = actuator_id
        super().__init__(message, severity, ErrorCategory.ACTUATOR, details, cause)


# Communication errors
class CommunicationError(PathfinderError):
    """Base class for communication-related errors."""

    def __init__(
        self,
        message: str,
        severity: ErrorSeverity = ErrorSeverity.MEDIUM,
        details: Optional[Dict[str, Any]] = None,
        cause: Optional[Exception] = None,
    ):
        super().__init__(message, severity, ErrorCategory.COMMUNICATION, details, cause)


class ConnectionError(CommunicationError):
    """Error for connection issues."""

    def __init__(
        self,
        message: str,
        endpoint: str,
        severity: ErrorSeverity = ErrorSeverity.HIGH,
        details: Optional[Dict[str, Any]] = None,
        cause: Optional[Exception] = None,
    ):
        details = details or {}
        details["endpoint"] = endpoint
        super().__init__(message, severity, details, cause)


# Software errors
class SoftwareError(PathfinderError):
    """Base class for software-related errors."""

    def __init__(
        self,
        message: str,
        severity: ErrorSeverity = ErrorSeverity.MEDIUM,
        details: Optional[Dict[str, Any]] = None,
        cause: Optional[Exception] = None,
    ):
        super().__init__(message, severity, ErrorCategory.SOFTWARE, details, cause)


class ConfigurationError(PathfinderError):
    """Base class for configuration-related errors."""

    def __init__(
        self,
        message: str,
        config_key: Optional[str] = None,
        severity: ErrorSeverity = ErrorSeverity.MEDIUM,
        details: Optional[Dict[str, Any]] = None,
        cause: Optional[Exception] = None,
    ):
        details = details or {}
        if config_key:
            details["config_key"] = config_key
        super().__init__(message, severity, ErrorCategory.CONFIGURATION, details, cause)


# Error registry for tracking and analysis
class ErrorRegistry:
    """Registry for tracking and analyzing errors."""

    def __init__(self):
        """Initialize a new error registry."""
        self.errors: List[PathfinderError] = []
        self.error_handlers: Dict[str, List[Callable[[PathfinderError], None]]] = {}
        self.recovery_handlers: Dict[str, List[Callable[[PathfinderError], bool]]] = {}
        self._instance = None

    def register_error(self, error: PathfinderError) -> None:
        """
        Register an error in the registry.

        Args:
            error: The error to register
        """
        import time

        # Set timestamp if not already set
        if not error.timestamp:
            error.timestamp = time.time()

        # Add error to registry
        self.errors.append(error)

        # Log the error
        if error.severity >= ErrorSeverity.HIGH:
            logger.error(str(error))
            if error.cause:
                logger.error(f"Caused by: {traceback.format_exc()}")
        elif error.severity == ErrorSeverity.MEDIUM:
            logger.warning(str(error))
        else:
            logger.info(str(error))

        # Call error handlers
        self._call_handlers(error)

    def register_handler(
        self,
        error_type: Union[type, str],
        handler: Callable[[PathfinderError], None],
        handler_id: Optional[str] = None,
    ) -> str:
        """
        Register a handler for a specific error type.

        Args:
            error_type: The error type or category name to handle
            handler: The handler function
            handler_id: Optional ID for the handler

        Returns:
            The handler ID
        """
        # Generate a handler ID if not provided
        if not handler_id:
            handler_id = f"handler_{len(self.error_handlers) + 1}"

        # Convert error_type to string key
        if isinstance(error_type, type):
            key = error_type.__name__
        else:
            key = str(error_type)

        # Initialize handler list for this key if needed
        if key not in self.error_handlers:
            self.error_handlers[key] = []

        # Add handler to list
        self.error_handlers[key].append(handler)

        return handler_id

    def register_recovery_handler(
        self,
        error_type: Union[type, str],
        handler: Callable[[PathfinderError], bool],
        handler_id: Optional[str] = None,
    ) -> str:
        """
        Register a recovery handler for a specific error type.

        Args:
            error_type: The error type or category name to handle
            handler: The recovery handler function that returns True if recovery was successful
            handler_id: Optional ID for the handler

        Returns:
            The handler ID
        """
        # Generate a handler ID if not provided
        if not handler_id:
            handler_id = f"recovery_{len(self.recovery_handlers) + 1}"

        # Convert error_type to string key
        if isinstance(error_type, type):
            key = error_type.__name__
        else:
            key = str(error_type)

        # Initialize handler list for this key if needed
        if key not in self.recovery_handlers:
            self.recovery_handlers[key] = []

        # Add handler to list
        self.recovery_handlers[key].append(handler)

        return handler_id

    def _call_handlers(self, error: PathfinderError) -> None:
        """
        Call all registered handlers for an error.

        Args:
            error: The error to handle
        """
        # Get error type name
        error_type = type(error).__name__

        # Call handlers for this specific error type
        if error_type in self.error_handlers:
            for handler in self.error_handlers[error_type]:
                try:
                    handler(error)
                except Exception as e:
                    logger.error(f"Error in error handler for {error_type}: {e}")

        # Call handlers for the error category
        category_name = error.category.name
        if category_name in self.error_handlers:
            for handler in self.error_handlers[category_name]:
                try:
                    handler(error)
                except Exception as e:
                    logger.error(f"Error in error handler for {category_name}: {e}")

        # Call generic handlers
        if "PathfinderError" in self.error_handlers:
            for handler in self.error_handlers["PathfinderError"]:
                try:
                    handler(error)
                except Exception as e:
                    logger.error(f"Error in generic error handler: {e}")

    def attempt_recovery(self, error: PathfinderError) -> bool:
        """
        Attempt to recover from an error using registered recovery handlers.

        Args:
            error: The error to recover from

        Returns:
            True if recovery was successful, False otherwise
        """
        # Get error type name
        error_type = type(error).__name__

        # Try specific error type handlers first
        if error_type in self.recovery_handlers:
            for handler in self.recovery_handlers[error_type]:
                try:
                    if handler(error):
                        logger.info(f"Successfully recovered from {error_type}")
                        return True
                except Exception as e:
                    logger.error(f"Error in recovery handler for {error_type}: {e}")

        # Try category handlers
        category_name = error.category.name
        if category_name in self.recovery_handlers:
            for handler in self.recovery_handlers[category_name]:
                try:
                    if handler(error):
                        logger.info(
                            f"Successfully recovered from {category_name} error"
                        )
                        return True
                except Exception as e:
                    logger.error(f"Error in recovery handler for {category_name}: {e}")

        # Try generic handlers
        if "PathfinderError" in self.recovery_handlers:
            for handler in self.recovery_handlers["PathfinderError"]:
                try:
                    if handler(error):
                        logger.info("Successfully recovered from error")
                        return True
                except Exception as e:
                    logger.error(f"Error in generic recovery handler: {e}")

        return False

    def get_errors_by_severity(self, severity: ErrorSeverity) -> List[PathfinderError]:
        """
        Get all errors with a specific severity.

        Args:
            severity: The severity level

        Returns:
            List of errors with the specified severity
        """
        return [e for e in self.errors if e.severity == severity]

    def get_errors_by_category(self, category: ErrorCategory) -> List[PathfinderError]:
        """
        Get all errors in a specific category.

        Args:
            category: The error category

        Returns:
            List of errors in the specified category
        """
        return [e for e in self.errors if e.category == category]

    def get_error_statistics(self) -> Dict[str, Any]:
        """
        Get statistics about recorded errors.

        Returns:
            Dictionary with error statistics
        """
        stats = {
            "total_errors": len(self.errors),
            "by_severity": {},
            "by_category": {},
        }

        # Count by severity
        for severity in ErrorSeverity:
            stats["by_severity"][severity.name] = len(
                self.get_errors_by_severity(severity)
            )

        # Count by category
        for category in ErrorCategory:
            stats["by_category"][category.name] = len(
                self.get_errors_by_category(category)
            )

        return stats

    def clear(self) -> None:
        """Clear all errors from the registry."""
        self.errors = []


# Global error registry instance
_error_registry = ErrorRegistry()


def get_error_registry() -> ErrorRegistry:
    """
    Get the global error registry instance.

    Returns:
        The global error registry
    """
    return _error_registry


def register_error(error: PathfinderError) -> None:
    """
    Register an error in the global registry.

    Args:
        error: The error to register
    """
    _error_registry.register_error(error)


def register_handler(
    error_type: Union[type, str],
    handler: Callable[[PathfinderError], None],
    handler_id: Optional[str] = None,
) -> str:
    """
    Register a handler for a specific error type in the global registry.

    Args:
        error_type: The error type or category name to handle
        handler: The handler function
        handler_id: Optional ID for the handler

    Returns:
        The handler ID
    """
    return _error_registry.register_handler(error_type, handler, handler_id)


def register_recovery_handler(
    error_type: Union[type, str],
    handler: Callable[[PathfinderError], bool],
    handler_id: Optional[str] = None,
) -> str:
    """
    Register a recovery handler for a specific error type in the global registry.

    Args:
        error_type: The error type or category name to handle
        handler: The recovery handler function that returns True if recovery was successful
        handler_id: Optional ID for the handler

    Returns:
        The handler ID
    """
    return _error_registry.register_recovery_handler(error_type, handler, handler_id)


def attempt_recovery(error: PathfinderError) -> bool:
    """
    Attempt to recover from an error using the global registry.

    Args:
        error: The error to recover from

    Returns:
        True if recovery was successful, False otherwise
    """
    return _error_registry.attempt_recovery(error)


# Result type for operations that might fail
T = TypeVar("T")
Result = Union[T, PathfinderError]


def ok(value: T) -> Tuple[T, None]:
    """
    Create a successful result.

    Args:
        value: The result value

    Returns:
        A tuple containing the value and None for the error
    """
    return value, None


def err(error: PathfinderError) -> Tuple[None, PathfinderError]:
    """
    Create a failed result.

    Args:
        error: The error that occurred

    Returns:
        A tuple containing None for the value and the error
    """
    # Register the error
    register_error(error)
    return None, error


def safe_call(func: Callable, *args, **kwargs) -> Any:
    """
    Safely call a function, catching and registering any exceptions.

    Args:
        func: The function to call
        *args: Positional arguments to pass to the function
        **kwargs: Keyword arguments to pass to the function

    Returns:
        The result of the function call, or None if an exception occurred
    """
    try:
        return func(*args, **kwargs)
    except PathfinderError as e:
        register_error(e)
        return None
    except Exception as e:
        error = SoftwareError(
            f"Unhandled exception in function {func.__name__}",
            severity=ErrorSeverity.HIGH,
            details={"args": args, "kwargs": kwargs},
            cause=e,
        )
        register_error(error)
        return None
