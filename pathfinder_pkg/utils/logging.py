"""
Logging module for PathfinderBot

Provides a centralized logging configuration for the entire package.
"""

import logging
import os
import sys
from datetime import datetime


def get_logger(name, level=None):
    """
    Get a logger with the specified name and optional level.

    Args:
        name (str): The name of the logger, typically the module name using __name__.
        level (int, optional): The logging level. Defaults to logging.INFO.

    Returns:
        logging.Logger: A configured logger instance.
    """
    if level is None:
        # Default to INFO, but allow override through environment variable
        level = getattr(logging, os.environ.get("PATHFINDER_LOG_LEVEL", "INFO"))

    logger = logging.getLogger(name)

    # Only configure the logger if it hasn't been configured yet
    if not logger.handlers:
        logger.setLevel(level)

        # Console handler for terminal output
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(level)
        console_format = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
        console_handler.setFormatter(console_format)
        logger.addHandler(console_handler)

        # Check if we should log to file based on environment variable
        log_to_file = (
            os.environ.get("PATHFINDER_LOG_TO_FILE", "false").lower() == "true"
        )
        if log_to_file:
            log_dir = os.environ.get("PATHFINDER_LOG_DIR", "logs")

            # Create log directory if it doesn't exist
            if not os.path.exists(log_dir):
                os.makedirs(log_dir)

            # Use timestamped filename to avoid overwriting logs
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            log_file = os.path.join(log_dir, f"pathfinder_{timestamp}.log")

            file_handler = logging.FileHandler(log_file)
            file_handler.setLevel(level)
            file_format = logging.Formatter(
                "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
            )
            file_handler.setFormatter(file_format)
            logger.addHandler(file_handler)

    return logger


def set_log_level(logger_name, level):
    """
    Set the log level for a specific logger.

    Args:
        logger_name (str): The name of the logger.
        level (int): The logging level to set.
    """
    logger = logging.getLogger(logger_name)
    logger.setLevel(level)
    for handler in logger.handlers:
        handler.setLevel(level)


# Create the root logger for the package
logger = get_logger("pathfinder_pkg")
