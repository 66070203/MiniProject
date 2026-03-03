"""Structured logging setup for ScamGuard."""

import logging
import os
import sys
from pathlib import Path


def get_logger(name: str, level: str | None = None) -> logging.Logger:
    """
    Create and return a named logger with consistent formatting.

    Args:
        name: Logger name (typically __name__)
        level: Log level string (DEBUG/INFO/WARNING/ERROR). Defaults to LOG_LEVEL env var or INFO.

    Returns:
        Configured Logger instance
    """
    if level is None:
        level = os.environ.get("LOG_LEVEL", "INFO").upper()

    logger = logging.getLogger(name)

    # Avoid adding duplicate handlers
    if logger.handlers:
        return logger

    logger.setLevel(getattr(logging, level, logging.INFO))

    # Console handler
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(getattr(logging, level, logging.INFO))

    formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)

    return logger
