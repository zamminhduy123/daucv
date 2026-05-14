"""
AI Service — LLM Waterfall Router with observability instrumentation.

Provides ``call_llm_with_fallback`` which tries multiple LLM providers in
sequence, logs every attempt via the JSONL logger, and returns a validated
Pydantic model.
"""

import asyncio
import logging
import time
from datetime import datetime, timezone
from typing import Any

from fastapi import BackgroundTasks, HTTPException
from pydantic import ValidationError

from app.core.config import PROVIDERS
from app.utils.llm_logger import LLMLogRecord, log_llm_request


async def call_llm_with_fallback(
    system_prompt: str,
    user_input: Any,
    response_model: type,
    *,
    feature_name: str = "unknown",
    prompt_version: str = "1.0.0",
    background_tasks: BackgroundTasks | None = None,
    max_retries: int = 1,
):
    """
    Tries multiple providers in a waterfall logic.
    If a provider fails, switches to the next one.

    Instruments every attempt with latency / token / success metrics and
    enqueues the log write as a FastAPI BackgroundTask so the caller is
    never blocked.
    """
    if "JSON" not in system_prompt.upper():
        system_prompt += "\n\nYou must return a valid JSON object matching the exact requested schema."

    messages = [{"role": "system", "content": system_prompt}]

    if isinstance(user_input, str):
        messages.append({"role": "user", "content": user_input})
    elif isinstance(user_input, list):
        messages.extend(user_input)

    last_error = None
    fallback_used = False

    for idx, provider in enumerate(PROVIDERS):
        client = provider["client"]
        model: str = provider["model"]
        name: str = provider["name"]

        if idx > 0:
            fallback_used = True

        for attempt in range(max_retries):
            start_time = time.perf_counter()
            input_tokens = 0
            output_tokens = 0
            json_valid = False
            error_message = ""

            try:
                response = await client.chat.completions.create(
                    model=model,
                    messages=messages,
                    response_format={"type": "json_object"},
                    temperature=0.7,
                )

                # --- Extract token usage (gracefully handle None) -----------
                if response.usage is not None:
                    input_tokens = response.usage.prompt_tokens or 0
                    output_tokens = response.usage.completion_tokens or 0

                content = response.choices[0].message.content
                if not content:
                    raise ValueError("Empty response content")

                # --- Validate JSON against Pydantic model -------------------
                try:
                    parsed = response_model.model_validate_json(content)
                    json_valid = True
                except ValidationError as ve:
                    json_valid = False
                    error_message = str(ve)
                    raise  # re-raise so outer except catches it

                # --- Log success --------------------------------------------
                latency_ms = int((time.perf_counter() - start_time) * 1000)
                record = LLMLogRecord(
                    timestamp=datetime.now(timezone.utc).isoformat(),
                    feature=feature_name,
                    provider=name,
                    model=model,
                    latency_ms=latency_ms,
                    success=True,
                    fallback_used=fallback_used,
                    json_valid=True,
                    prompt_version=prompt_version,
                    input_tokens=input_tokens,
                    output_tokens=output_tokens,
                )
                if background_tasks is not None:
                    background_tasks.add_task(log_llm_request, record)
                else:
                    log_llm_request(record)

                return parsed

            except Exception as e:
                latency_ms = int((time.perf_counter() - start_time) * 1000)
                last_error = str(e)

                # --- Log failure --------------------------------------------
                record = LLMLogRecord(
                    timestamp=datetime.now(timezone.utc).isoformat(),
                    feature=feature_name,
                    provider=name,
                    model=model,
                    latency_ms=latency_ms,
                    success=False,
                    fallback_used=fallback_used,
                    json_valid=json_valid,
                    prompt_version=prompt_version,
                    input_tokens=input_tokens,
                    output_tokens=output_tokens,
                    error_message=error_message or last_error,
                )
                if background_tasks is not None:
                    background_tasks.add_task(log_llm_request, record)
                else:
                    log_llm_request(record)

                logging.warning(
                    f"Provider {name} attempt {attempt + 1} failed: {last_error}. Switching to next..."
                )
                await asyncio.sleep(1)  # wait before retry

    raise HTTPException(
        status_code=503,
        detail=f"All AI providers are currently overloaded. Last error: {last_error}",
    )
