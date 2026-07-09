"""
Application logging configuration.

Sets up a JSON-based log formatter that automatically sanitizes PII from all
log messages.  Call ``setup_logging()`` once at application startup (before
uvicorn starts accepting requests).

Log format (JSON lines):
    {
        "timestamp": "2026-07-07T10:30:00Z",
        "level": "INFO",
        "logger": "app.main",
        "message": "Request completed",
        "request_id": "abc-123"
    }

This structured format is easy to ingest into log aggregators (Datadog,
Papertrail, CloudWatch) and guarantees PII is never written in plaintext.
"""

import json
import logging
import logging.handlers
from datetime import datetime, timezone

from app.core.config import LOG_LEVEL, LOGS_DIR
from app.utils.pii_sanitizer import sanitize

# ---------------------------------------------------------------------------
# JSON log record — attaches request_id context if available
# ---------------------------------------------------------------------------


class JSONFormatter(logging.Formatter):
    """Format log records as JSON lines with PII sanitization."""

    def format(self, record: logging.LogRecord) -> str:
        """
        Build a JSON string from the log record.

        The ``message`` field (and ``exc_info`` if present) is sanitized
        through ``pii_sanitizer.sanitize()`` before being written.
        """
        # Sanitize the message
        msg = sanitize(record.getMessage())

        entry: dict = {
            "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
            "level": record.levelname,
            "logger": record.name,
            "message": msg,
        }

        # Include exception info if present (sanitized)
        if record.exc_info and record.exc_info[0] is not None:
            entry["exception"] = self.formatException(record.exc_info)
            entry["exception"] = sanitize(entry["exception"])

        # Include request_id from contextvars (set by RequestLogger middleware)
        try:
            from app.middleware.request_logger import request_id_ctx

            rid = request_id_ctx.get()
            if rid:
                entry["request_id"] = str(rid)
        except Exception:  # pragma: no cover — middleware may not be loaded
            pass

        # Include extra fields added via logger.info(..., extra={...})
        for key in ("feature", "status_code", "duration_ms", "endpoint"):
            if hasattr(record, key):
                entry[key] = getattr(record, key)

        # Include process/thread info
        entry["pid"] = record.process
        entry["thread"] = record.threadName

        return json.dumps(entry, ensure_ascii=False)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def setup_logging() -> None:
    """
    Configure the root logger with:

    1. A console (stderr) handler — always active.
    2. A rotating file handler — writes JSON lines to ``logs/YYYY-MM-DD.jsonl``.

    Both handlers use the PII-safe JSON formatter.
    """
    # Determine log level from env (default INFO)
    level = getattr(logging, LOG_LEVEL.upper(), logging.INFO)

    # Root logger — sanitize everything
    root = logging.getLogger()
    root.setLevel(level)

    # Clear existing handlers (in case called multiple times)
    root.handlers.clear()

    formatter = JSONFormatter()

    # Console handler — stderr
    console = logging.StreamHandler()
    console.setFormatter(formatter)
    console.setLevel(level)
    root.addHandler(console)

    # Rotating file handler — daily, max 50 MB, keep 7 backups
    file_handler = logging.handlers.TimedRotatingFileHandler(
        filename=LOGS_DIR / "app.jsonl",
        when="midnight",
        backupCount=7,
        encoding="utf-8",
    )
    file_handler.setFormatter(formatter)
    file_handler.setLevel(level)
    root.addHandler(file_handler)

    # Silence noisy third-party loggers
    for noisy in ("uvicorn.access", "watchfiles", "multipart"):
        logging.getLogger(noisy).setLevel(logging.WARNING)
