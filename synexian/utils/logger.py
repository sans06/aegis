"""Logging configuration for the Aegis"""

#=====================================
#  2026 Synexian Labs Private Limited
# Proprietary and Confidential

import logging
import sys
from pathlib import Path
from typing import Optional


def setup_logger(
    name: str = "synexian",
    level: int = logging.INFO,
    log_file: Optional[Path] = None,
    format_string: Optional[str] = None,
) -> logging.Logger:
    """Set up and configure a logger.

    Args:
        name: Logger name
        level: Logging level
        log_file: Optional path to log file
        format_string: Optional custom format string

    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)
    logger.setLevel(level)

    # Remove existing handlers
    logger.handlers.clear()

    # Default format
    if format_string is None:
        format_string = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

    formatter = logging.Formatter(format_string)

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # File handler if specified
    if log_file:
        log_file.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(level)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    return logger


def get_log_level_from_verbosity(verbosity: int) -> int:
    """Convert verbosity level to logging level.

    Args:
        verbosity: Verbosity level (0=quiet, 1=normal, 2=verbose, 3=debug)

    Returns:
        Logging level constant
    """
    if verbosity == 0:
        return logging.WARNING
    elif verbosity == 1:
        return logging.INFO
    elif verbosity == 2:
        return logging.DEBUG
    else:
        return logging.DEBUG


def configure_logging(verbosity: int = 1, log_file: Optional[Path] = None) -> None:
    """Configure logging for the entire application.

    Args:
        verbosity: Verbosity level
        log_file: Optional log file path
    """
    level = get_log_level_from_verbosity(verbosity)
    setup_logger("synexian", level=level, log_file=log_file)
