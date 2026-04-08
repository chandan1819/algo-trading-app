"""Structured logging configuration with JSON formatting."""

from __future__ import annotations

import logging
import logging.handlers
import json
import os
import sys
from datetime import datetime, timezone
from typing import Any


class JSONFormatter(logging.Formatter):
    """Formats log records as single-line JSON objects."""

    def format(self, record: logging.LogRecord) -> str:
        log_entry: dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        if record.exc_info and record.exc_info[0] is not None:
            log_entry["exception"] = self.formatException(record.exc_info)

        if hasattr(record, "extra_data"):
            log_entry["data"] = record.extra_data  # type: ignore[attr-defined]

        return json.dumps(log_entry, default=str)


def setup_logging(log_level: str = "INFO", log_dir: str = "logs") -> None:
    """Configure root logger with JSON console and file handlers.

    Parameters
    ----------
    log_level:
        Minimum severity to emit (DEBUG, INFO, WARNING, ERROR, CRITICAL).
    log_dir:
        Directory where rotating log files are stored.
    """
    os.makedirs(log_dir, exist_ok=True)

    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, log_level.upper(), logging.INFO))

    # Remove any pre-existing handlers to avoid duplicates on re-init.
    root_logger.handlers.clear()

    json_formatter = JSONFormatter()

    # ── Console handler ──────────────────────────────────────────────────
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(json_formatter)
    root_logger.addHandler(console_handler)

    # ── Rotating file handler ────────────────────────────────────────────
    file_handler = logging.handlers.RotatingFileHandler(
        filename=os.path.join(log_dir, "app.log"),
        maxBytes=10 * 1024 * 1024,  # 10 MB
        backupCount=5,
        encoding="utf-8",
    )
    file_handler.setFormatter(json_formatter)
    root_logger.addHandler(file_handler)

    # ── Error-only file handler ──────────────────────────────────────────
    error_handler = logging.handlers.RotatingFileHandler(
        filename=os.path.join(log_dir, "error.log"),
        maxBytes=10 * 1024 * 1024,
        backupCount=5,
        encoding="utf-8",
    )
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(json_formatter)
    root_logger.addHandler(error_handler)

    # Quieten noisy third-party loggers.
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("websockets").setLevel(logging.WARNING)

    root_logger.info("Logging initialised at %s level", log_level.upper())
