"""Structured local logging.

Writes JSON lines to a size-capped, auto-rotating local log file
(~/.breaktime/logs/breaktime.log). Deliberately simple stdlib logging rather than a
distributed-tracing framework (structlog/OpenTelemetry) -- this is a local single-user
desktop app, not a service with logs to correlate across machines.

Hard rule: only derived, non-sensitive fields may be logged (state transitions, counts,
durations, error codes). Never log raw camera frames or anything derived pixel-for-pixel
from one. Call sites are responsible for honoring this; see CONTRIBUTING.md.
"""

from __future__ import annotations

import json
import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Any

_LOG_DIR = Path.home() / ".breaktime" / "logs"
_LOG_FILE = _LOG_DIR / "breaktime.log"
_MAX_BYTES = 10 * 1024 * 1024
_BACKUP_COUNT = 5
_ROOT_LOGGER_NAME = "breaktime"


class _JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": self.formatTime(record, "%Y-%m-%dT%H:%M:%S%z"),
            "level": record.levelname,
            "event": record.getMessage(),
            "logger": record.name,
        }
        fields = getattr(record, "fields", None)
        if fields:
            payload.update(fields)
        if record.exc_info:
            payload["exc_info"] = self.formatException(record.exc_info)
        return json.dumps(payload)


def configure_logging(*, level: int = logging.INFO, console: bool = False) -> None:
    """Configure the root `breaktime` logger. Call once at app startup."""
    _LOG_DIR.mkdir(parents=True, exist_ok=True)

    logger = logging.getLogger(_ROOT_LOGGER_NAME)
    logger.setLevel(level)
    logger.handlers.clear()

    file_handler = RotatingFileHandler(
        _LOG_FILE, maxBytes=_MAX_BYTES, backupCount=_BACKUP_COUNT, encoding="utf-8"
    )
    file_handler.setFormatter(_JsonFormatter())
    logger.addHandler(file_handler)

    if console:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(_JsonFormatter())
        logger.addHandler(console_handler)

    logger.propagate = False


def get_logger(name: str) -> logging.Logger:
    """Get a child logger under the `breaktime` namespace, e.g. get_logger("vision")."""
    return logging.getLogger(f"{_ROOT_LOGGER_NAME}.{name}")


def log_event(logger: logging.Logger, event: str, /, **fields: Any) -> None:
    """Log one structured event with a short stable name plus typed fields.

    Example: log_event(logger, "break_verified", duration_seconds=22.4)

    Never pass frame/image data as a field.
    """
    logger.info(event, extra={"fields": fields})
