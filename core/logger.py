"""
FinSight — Logging Configuration
===================================
Uses the stdlib ``logging`` module directly (no structlog dependency)
to avoid compatibility issues on Streamlit Cloud's managed environment.

Design decisions:
- Single ``get_logger`` factory — modules never create loggers directly.
- Dev: colourised, human-readable output via a custom Formatter.
- Prod: JSON-style key=value output suitable for log aggregators.
- Configured once at import time via ``_bootstrap()``; subsequent calls
  to ``get_logger`` are pure ``logging.getLogger`` wrappers.

Usage::

    from core.logger import get_logger
    log = get_logger(__name__)
    log.info("stock_fetched ticker=AAPL rows=252")
    log.warning("cache_miss key=%s", cache_key)
    log.error("api_error status=%d msg=%s", 429, exc)
"""

from __future__ import annotations

import logging
import os
import sys


# ── Custom formatter ──────────────────────────────────────────

class _DevFormatter(logging.Formatter):
    """Colourised, human-readable formatter for local development."""

    _GREY    = "\x1b[38;5;240m"
    _CYAN    = "\x1b[36m"
    _YELLOW  = "\x1b[33m"
    _RED     = "\x1b[31m"
    _BOLD_RED= "\x1b[31;1m"
    _RESET   = "\x1b[0m"

    _LEVEL_COLORS = {
        logging.DEBUG:    _GREY,
        logging.INFO:     _CYAN,
        logging.WARNING:  _YELLOW,
        logging.ERROR:    _RED,
        logging.CRITICAL: _BOLD_RED,
    }

    def format(self, record: logging.LogRecord) -> str:
        color  = self._LEVEL_COLORS.get(record.levelno, self._RESET)
        ts     = self.formatTime(record, "%H:%M:%S")
        level  = f"{color}{record.levelname:<8}{self._RESET}"
        name   = f"{self._GREY}{record.name}{self._RESET}"
        return f"{ts} {level} {name} — {record.getMessage()}"


class _ProdFormatter(logging.Formatter):
    """Key=value formatter suitable for log aggregation pipelines."""

    def format(self, record: logging.LogRecord) -> str:
        return (
            f"ts={self.formatTime(record, '%Y-%m-%dT%H:%M:%S')} "
            f"level={record.levelname} "
            f"logger={record.name} "
            f"msg={record.getMessage()!r}"
        )


# ── Bootstrap (runs once at import) ───────────────────────────

def _bootstrap() -> None:
    """Configure the root logger idempotently."""
    root = logging.getLogger()

    # Already configured — do not add duplicate handlers
    if root.handlers:
        return

    raw_level = os.getenv("LOG_LEVEL", "INFO").upper()
    level = getattr(logging, raw_level, logging.INFO)

    is_prod = os.getenv("APP_ENV", "development").lower() == "production"
    formatter: logging.Formatter = _ProdFormatter() if is_prod else _DevFormatter()

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)

    root.addHandler(handler)
    root.setLevel(level)

    # Silence noisy third-party loggers
    for noisy in ("urllib3", "httpx", "httpcore", "yfinance", "peewee"):
        logging.getLogger(noisy).setLevel(logging.WARNING)


_bootstrap()


# ── Public API ────────────────────────────────────────────────

def get_logger(name: str) -> logging.Logger:
    """Return a named logger scoped to *name*.

    Args:
        name: Typically ``__name__`` of the calling module.

    Returns:
        A standard :class:`logging.Logger` instance.  All configuration
        (level, handlers, formatters) is inherited from the root logger
        set up by :func:`_bootstrap`.
    """
    return logging.getLogger(name)
