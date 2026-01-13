"""
Logging Configuration Module

Provides structured logging setup for the FinTrack API.
- JSON format for production (machine-readable)
- Human-readable format for development
- Configurable log levels based on DEBUG setting
"""
import logging
import sys
from typing import Optional
from functools import lru_cache

from .config import get_settings


class JSONFormatter(logging.Formatter):
    """JSON formatter for structured logging in production."""

    def format(self, record: logging.LogRecord) -> str:
        import json
        from datetime import datetime, timezone

        log_data = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        # Add extra fields if present
        if hasattr(record, "extra_data"):
            log_data["extra"] = record.extra_data

        return json.dumps(log_data)


class DevelopmentFormatter(logging.Formatter):
    """Human-readable formatter for development."""

    def __init__(self):
        super().__init__(
            fmt="%(asctime)s | %(levelname)-8s | %(name)s:%(funcName)s:%(lineno)d | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )


def setup_logging() -> None:
    """
    Configure logging for the application.

    - Sets up root logger with appropriate handler and formatter
    - Configures log level based on DEBUG setting
    - Uses JSON format for production, human-readable for development
    """
    settings = get_settings()

    # Determine log level
    log_level = logging.DEBUG if settings.debug else logging.INFO

    # Create handler
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(log_level)

    # Choose formatter based on environment
    if settings.debug:
        formatter = DevelopmentFormatter()
    else:
        formatter = JSONFormatter()

    handler.setFormatter(formatter)

    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)

    # Remove existing handlers to avoid duplicates
    root_logger.handlers.clear()
    root_logger.addHandler(handler)

    # Set specific log levels for noisy libraries
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)

    # Log startup message
    logger = get_logger(__name__)
    logger.info(
        "Logging initialized",
        extra={"debug_mode": settings.debug, "log_level": logging.getLevelName(log_level)}
    )


@lru_cache()
def get_logger(name: Optional[str] = None) -> logging.Logger:
    """
    Get a configured logger instance.

    Args:
        name: Logger name (typically __name__ of the calling module).
              If None, returns the root logger.

    Returns:
        Configured Logger instance.

    Usage:
        from app.core.logging_config import get_logger
        logger = get_logger(__name__)

        logger.debug("Debug message")
        logger.info("Info message")
        logger.warning("Warning message")
        logger.error("Error message")
        logger.exception("Error with traceback")  # Use in except blocks
    """
    return logging.getLogger(name)
