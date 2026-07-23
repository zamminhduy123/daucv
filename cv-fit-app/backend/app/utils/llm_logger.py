"""LLMOps Observability Logger
============================
Thread-safe utility to log LLM request metrics into daily JSONL files.
Each line in the file is a self-contained JSON object for easy ingestion
by analytics pipelines or the admin metrics endpoint.

Error messages are sanitized through the PII sanitizer before being written
to prevent accidental leakage of identifiable data.
"""

import logging
import threading
from datetime import datetime, timezone

from pydantic import BaseModel, Field

from app.core.config import LOGS_DIR
from app.utils.pii_sanitizer import sanitize

_logger = logging.getLogger("app.llm_logger")

# A single lock shared by all threads writing to JSONL files.
_write_lock = threading.Lock()


# ---------------------------------------------------------------------------
# Pydantic model — strongly typed log record
# ---------------------------------------------------------------------------


class LLMLogRecord(BaseModel):
    """Schema for a single LLM request log entry."""

    timestamp: str = Field(
        ...,
        description="ISO-8601 timestamp of when the request completed.",
    )
    feature: str = Field(
        ...,
        description='Calling feature, e.g. "cv_analyzer", "mock_interview".',
    )
    provider: str = Field(
        ...,
        description='Provider name, e.g. "Gemini", "Groq", "OpenRouter".',
    )
    model: str = Field(..., description="Model identifier used for the request.")
    latency_ms: int = Field(
        ...,
        description="Wall-clock latency of the API call in milliseconds.",
    )
    success: bool = Field(
        ...,
        description="Whether the request returned a valid, parsed response.",
    )
    fallback_used: bool = Field(
        ...,
        description="True if a previous provider failed and we fell through to this one.",
    )
    json_valid: bool = Field(
        ...,
        description="Whether the raw LLM output was valid JSON matching the Pydantic schema.",
    )
    prompt_version: str = Field(
        ...,
        description='Semantic version of the prompt template, e.g. "1.0.0".',
    )
    input_tokens: int = Field(
        default=0,
        description="Number of prompt tokens (0 if usage data unavailable).",
    )
    output_tokens: int = Field(
        default=0,
        description="Number of completion tokens (0 if usage data unavailable).",
    )
    error_message: str = Field(
        default="",
        description="Error details when the request failed.",
    )


# ---------------------------------------------------------------------------
# Writer function
# ---------------------------------------------------------------------------


def _get_daily_log_path():
    """Return the path for today's log file, e.g. ``logs/2026-05-13-requests.jsonl``."""
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    return LOGS_DIR / f"{today}-requests.jsonl"


def log_llm_request(record: LLMLogRecord) -> None:
    """Append a single ``LLMLogRecord`` as a JSON line to the daily log file.

    Error messages are sanitized to mask PII.  This function is
    **thread-safe** — it acquires a module-level lock before writing so
    concurrent FastAPI background tasks never interleave lines.

    A structured log line is also emitted via the application logger so that
    the request is captured in the main ``app.jsonl`` log (with request_id
    context if available).
    """
    # Sanitize error message before writing to JSONL (PII safety)
    sanitized_error = sanitize(record.error_message) if record.error_message else ""
    if sanitized_error != record.error_message:
        record = record.model_copy(update={"error_message": sanitized_error})

    line = record.model_dump_json() + "\n"
    path = _get_daily_log_path()

    with _write_lock, open(path, "a", encoding="utf-8") as fh:
        fh.write(line)

    # Emit to application logger (structured JSON with PII sanitization)
    if record.success:
        _logger.info(
            "LLM request completed",
            extra={
                "feature": record.feature,
                "provider": record.provider,
                "status_code": 200 if record.success else 500,
            },
        )
    else:
        _logger.warning(
            "LLM request failed: %s",
            sanitized_error[:200],  # truncate to avoid huge log lines
            extra={
                "feature": record.feature,
                "provider": record.provider,
                "status_code": 500,
            },
        )
