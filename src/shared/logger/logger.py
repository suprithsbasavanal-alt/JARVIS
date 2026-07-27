"""Structured Logger Abstraction for Jarvis."""

import logging
import sys


def get_logger(name: str) -> logging.Logger:
    """Retrieves a configured logger instance."""
    logger = logging.getLogger(f"jarvis.{name}")
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        formatter = logging.Formatter(
            "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
    return logger
