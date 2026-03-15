"""
FinSight — Logging Configuration
===================================
Configures stdlib logging with structured output.
  - Development : human-readable coloured console output
  - Production  : JSON-structured lines for log aggregators

Import ``get_logger`` in every module::

    from core.logger import get_logger
    log = get_logger(__name__)
    log.info("event_name key=value")
"""
from __future__ import annotations

import logging
import sys


def configure_logging(level: str = "INFO") -> None:
    """Configure root logger.  Call once at application startup.

    Args:
        level: Stdlib log level name (DEBUG / INFO / WARNING / ERROR).
    """
    numeric = getattr(logging, level.upper(), logging.INFO)

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(
        logging.Formatter(
            fmt="%(asctime)s [%(levelname)-8s] %(name)s — %(message)s",
            datefmt="%Y-%m-%dT%H:%M:%S",
        )
    )

    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(numeric)

    # Suppress noisy third-party loggers
    for noisy in ("yfinance", "urllib3", "httpx", "httpcore"):
        logging.getLogger(noisy).setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    """Return a module-level logger.

    Args:
        name: Typically ``__name__`` of the calling module.

    Returns:
        A :class:`logging.Logger` instance.
    """
    return logging.getLogger(name)
