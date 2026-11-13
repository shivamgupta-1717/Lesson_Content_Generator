"""Logging configuration for the Self-Evaluating Lesson Content Generator.

Provides consistent, timestamped, formatted logging to console and optional log files.
"""

import logging
import os
import sys
from typing import Optional


def setup_logger(
    name: str = "LessonGenerator",
    level: Optional[str] = None,
    log_file: Optional[str] = None,
) -> logging.Logger:
    """Configures and returns a named logger instance.

    Args:
        name: The name of the logger namespace.
        level: Log level string (DEBUG, INFO, WARNING, ERROR). Defaults to LOG_LEVEL env var or INFO.
        log_file: Optional path to append log file output.

    Returns:
        logging.Logger: Fully configured logger instance.
    """
    logger = logging.getLogger(name)

    if logger.handlers:
        return logger

    resolved_level = level or os.getenv("LOG_LEVEL", "INFO").upper()
    numeric_level = getattr(logging, resolved_level, logging.INFO)
    logger.setLevel(numeric_level)

    formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | [%(name)s:%(funcName)s:%(lineno)d] - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(numeric_level)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    if log_file:
        os.makedirs(os.path.dirname(log_file), exist_ok=True)
        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setLevel(numeric_level)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    logger.propagate = False
    return logger


logger = setup_logger()
