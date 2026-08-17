"""AI Service — LLM Waterfall Router with observability instrumentation.

Provides ``call_llm_with_fallback`` which tries multiple LLM providers in
sequence, logs every attempt via the JSONL logger, and returns a validated
Pydantic model.
"""

import asyncio
import logging
import time
from collections.abc import Awaitable, Callable
from copy import copy
from datetime import datetime, timezone
from typing import Any

from fastapi import BackgroundTasks, HTTPException
from pydantic import ValidationError

from app.core import config
from app.utils.llm_logger import LLMLogRecord, log_llm_input, log_llm_request
from app.utils.pii_sanitizer import sanitize

_logger = logging.getLogger("app.ai_service")

# A disconnected client does not necessarily stop llama-server decoding. Keep
# only one long Remote Qwen request in flight per backend process so cancelled
# CV jobs cannot consume every server slot and starve later requests.
_remote_qwen_semaphore: asyncio.Semaphore | None = None


def _get_remote_qwen_semaphore() -> asyncio.Semaphore:
    global _remote_qwen_semaphore
    if _remote_qwen_semaphore is None:
        _remote_qwen_semaphore = asyncio.Semaphore(config.REMOTE_QWEN_MAX_CONCURRENT)
    return _remote_qwen_semaphore


async def call_llm_with_fallback(
    system_prompt: str,
    user_input: Any,
    response_model: type,
    *,
    feature_name: str = "unknown",
    prompt_version: str = "1.0.0",
    background_tasks: BackgroundTasks | None = None,
    max_retries: int = 1,
    max_output_tokens: int | None = None,
    temperature: float = 0.7,
    result_validator: Callable[[Any], None] | None = None,
    on_retry: Callable[[int, int], Awaitable[None]] | None = None,
) -> Any:
    """Tries multiple providers in a waterfall logic.
    If a provider fails, switches to the next one.

    Instruments every attempt with latency / token / success metrics and
    enqueues the log write as a FastAPI BackgroundTask so the caller is
    never blocked.
    """
    if "JSON" not in system_prompt.upper():
        system_prompt += "\n\nYou must return a valid JSON object matching the exact requested schema."
    if max_output_tokens is not None and max_output_tokens <= 0:
        raise ValueError("max_output_tokens must be positive")

    messages = [{"role": "system", "content": system_prompt}]

    if isinstance(user_input, str):
        messages.append({"role": "user", "content": user_input})
    elif isinstance(user_input, list):
        messages.extend(user_input)

    last_error = None
    fallback_used = False

    configured_providers = [
        p for p in config.PROVIDERS if getattr(p, "is_configured", True)
    ]
    active_providers = (
        configured_providers if configured_providers else config.PROVIDERS
    )

    total_attempts = len(active_providers) * max_retries
    completed_attempts = 0

    for idx, provider in enumerate(active_providers):
        if idx > 0:
            fallback_used = True

        for attempt in range(max_retries):
            start_time = time.perf_counter()
            input_tokens = 0
            output_tokens = 0
            json_valid = False
            error_message = ""

            try:
                # --- Delegate to the provider class ---
                provider_for_attempt = copy(provider)
                if max_output_tokens is not None:
                    provider_for_attempt.max_output_tokens = max_output_tokens

                _logger.info(
                    "Waterfall router attempting provider %s (model: %s, attempt %d/%d)",
                    provider.name,
                    provider.model,
                    attempt + 1,
                    max_retries,
                )

                # Persist raw system prompt, user input, and expected schema to file before calling provider
                log_llm_input(
                    feature=feature_name,
                    provider=provider.name,
                    model=provider.model,
                    system_prompt=system_prompt,
                    user_content=user_input,
                    prompt_version=prompt_version,
                    response_model=response_model,
                )

                if provider.name == "Remote-Qwen":
                    _logger.info("Waiting for Remote Qwen request slot")
                    semaphore = _get_remote_qwen_semaphore()
                    try:
                        async with asyncio.timeout(config.REMOTE_QWEN_QUEUE_TIMEOUT):
                            await semaphore.acquire()
                    except TimeoutError as exc:
                        raise TimeoutError(
                            "Remote Qwen queue wait timed out after "
                            f"{config.REMOTE_QWEN_QUEUE_TIMEOUT:g}s"
                        ) from exc
                    try:
                        _logger.info("Acquired Remote Qwen request slot")
                        result = await provider_for_attempt.generate_structured(
                            system_prompt=system_prompt,
                            user_content=user_input,
                            response_model=response_model,
                            temperature=temperature,
                        )
                    finally:
                        semaphore.release()
                else:
                    result = await provider_for_attempt.generate_structured(
                        system_prompt=system_prompt,
                        user_content=user_input,
                        response_model=response_model,
                        temperature=temperature,
                    )
                _logger.info(
                    "Waterfall router received successful response from provider %s",
                    provider.name,
                )
                input_tokens = result.input_tokens
                output_tokens = result.output_tokens
                json_valid = True  # If it didn't raise ValidationError, it's valid
                if result_validator is not None:
                    result_validator(result.data)

                # --- Log success --------------------------------------------
                latency_ms = int((time.perf_counter() - start_time) * 1000)
                record = LLMLogRecord(
                    timestamp=datetime.now(timezone.utc).isoformat(),
                    feature=feature_name,
                    provider=provider.name,
                    model=provider.model,
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

                return result.data

            except Exception as e:
                completed_attempts += 1
                latency_ms = int((time.perf_counter() - start_time) * 1000)
                last_error = str(e)

                if isinstance(e, ValidationError):
                    json_valid = False
                    error_message = f"Schema Validation Error: {last_error}"
                else:
                    error_message = last_error

                # --- Log failure --------------------------------------------
                record = LLMLogRecord(
                    timestamp=datetime.now(timezone.utc).isoformat(),
                    feature=feature_name,
                    provider=provider.name,
                    model=provider.model,
                    latency_ms=latency_ms,
                    success=False,
                    fallback_used=fallback_used,
                    json_valid=json_valid,
                    prompt_version=prompt_version,
                    input_tokens=input_tokens,
                    output_tokens=output_tokens,
                    error_message=error_message,
                )
                if background_tasks is not None:
                    background_tasks.add_task(log_llm_request, record)
                else:
                    log_llm_request(record)

                _logger.warning(
                    "Provider %s attempt %d failed: %s. Switching to next...",
                    provider.name,
                    attempt + 1,
                    sanitize(last_error),
                )

                # Fail fast on auth / API key errors without wasting retries
                err_str = last_error.lower()
                is_auth_error = (
                    "401" in err_str
                    or "403" in err_str
                    or "unauthorized" in err_str
                    or "api_key" in err_str
                    or "invalid api key" in err_str
                )

                if completed_attempts < total_attempts:
                    if on_retry is not None:
                        await on_retry(completed_attempts + 1, total_attempts)
                    await asyncio.sleep(1)  # wait before retry

                if is_auth_error:
                    _logger.warning(
                        "Provider %s has authentication error. Skipping remaining retries...",
                        provider.name,
                    )
                    break

    raise HTTPException(
        status_code=503,
        detail=f"All AI providers are currently overloaded. Last error: {last_error}",
    )
