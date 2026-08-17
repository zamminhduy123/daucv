"""LLMOps Observability Logger
============================
Thread-safe utility to log LLM request metrics into daily JSONL files.
Each line in the file is a self-contained JSON object for easy ingestion
by analytics pipelines or the admin metrics endpoint.

Error messages are sanitized through the PII sanitizer before being written
to prevent accidental leakage of identifiable data.
"""

import json
import logging
import threading
from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, Field

from app.core.config import LOGS_DIR
from app.utils.pii_sanitizer import sanitize

_logger = logging.getLogger("app.llm_logger")

# A single lock shared by all threads writing to JSONL files.
_write_lock = threading.Lock()

PROMPTS_DIR = LOGS_DIR / "prompts"
PROMPTS_DIR.mkdir(parents=True, exist_ok=True)


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


def log_llm_input(
    feature: str,
    provider: str,
    model: str,
    system_prompt: str,
    user_content: Any,
    prompt_version: str = "1.0.0",
    response_model: type[BaseModel] | None = None,
) -> str:
    """Save raw LLM system prompt, user input, and expected JSON schema to file BEFORE sending request.

    Saves to:
    1. Daily JSONL file: logs/YYYY-MM-DD-llm-inputs.jsonl
    2. Readable text file: logs/prompts/YYYYMMDD_HHMMSS_{feature}_{provider}.txt
    """
    now = datetime.now(timezone.utc)
    timestamp_str = now.isoformat()
    date_str = now.strftime("%Y-%m-%d")
    time_file_str = now.strftime("%Y%m%d_%H%M%S_%f")[:19]

    user_str = str(user_content)

    schema_dict = None
    schema_str = ""
    if response_model is not None:
        try:
            if hasattr(response_model, "model_json_schema"):
                schema_dict = response_model.model_json_schema()
            schema_str = (
                json.dumps(schema_dict, indent=2, ensure_ascii=False)
                if schema_dict
                else str(response_model)
            )
        except Exception:
            schema_str = str(response_model)

    record = {
        "timestamp": timestamp_str,
        "feature": feature,
        "provider": provider,
        "model": model,
        "prompt_version": prompt_version,
        "response_schema": schema_dict,
        "system_prompt": system_prompt,
        "user_content": user_str,
    }

    # 1. Append to daily JSONL file
    jsonl_path = LOGS_DIR / f"{date_str}-llm-inputs.jsonl"
    line = json.dumps(record, ensure_ascii=False) + "\n"

    # 2. Write human-readable prompt text file
    txt_filename = f"{time_file_str}_{feature}_{provider}.txt"
    txt_path = PROMPTS_DIR / txt_filename

    schema_section = (
        f"--- EXPECTED RESPONSE JSON SCHEMA ---\n{schema_str}\n\n" if schema_str else ""
    )

    readable_content = (
        f"=== TIMESTAMP: {timestamp_str} ===\n"
        f"=== FEATURE: {feature} | PROVIDER: {provider} | MODEL: {model} ===\n"
        f"=== PROMPT VERSION: {prompt_version} ===\n\n"
        f"{schema_section}"
        f"--- SYSTEM PROMPT ---\n{system_prompt}\n\n"
        f"--- USER CONTENT ---\n{user_str}\n"
    )

    try:
        with _write_lock:
            with open(jsonl_path, "a", encoding="utf-8") as fh:
                fh.write(line)
            with open(txt_path, "w", encoding="utf-8") as fh:
                fh.write(readable_content)
        _logger.info("Saved LLM input prompt to %s", txt_path)
    except Exception as err:
        _logger.error("Failed to write LLM input log: %s", err)

    return str(txt_path)
