#!/usr/bin/env python3
"""Measure normal JSON versus schema-constrained LLM #1 mapper throughput.

Uses a synthetic CV only. It never sends a user's CV to the benchmark endpoint.
"""

from __future__ import annotations

import argparse
import asyncio
import sys
import time
from copy import copy
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import httpx

sys.path.append(str(Path(__file__).resolve().parent.parent))

from app.core.config import CV_STRUCTURING_MAX_OUTPUT_TOKENS, PROVIDERS
from app.models.cv_structuring import LLMSemanticCVResponse
from app.prompts.system_prompts import (
    build_block_parsing_prompt,
    format_raw_extraction_blocks,
)
from app.services.cv_structuring_service import build_manual_text_extraction
from app.services.llm_provider import QwenCustomProvider

_SYNTHETIC_CV = """Mai Tran
Machine Learning Engineer
mai.tran@example.test | Ho Chi Minh City, Vietnam

Experience
ML Engineer | Example Labs | 2023 - Present
- Built a PyTorch inference service for document classification.
- Added FastAPI endpoints and Docker deployment.

Education
B.Sc. Computer Science | Example University | 2019 - 2023

Skills
Python, PyTorch, FastAPI, Docker
"""


@dataclass(frozen=True)
class BenchmarkResult:
    mode: str
    elapsed_seconds: float
    input_tokens: int | None
    output_tokens: int | None
    output_characters: int
    finish_reason: str | None

    @property
    def tokens_per_second(self) -> float | None:
        if not self.output_tokens or self.elapsed_seconds <= 0:
            return None
        return self.output_tokens / self.elapsed_seconds


def _remote_qwen() -> QwenCustomProvider:
    provider = next(
        (candidate for candidate in PROVIDERS if candidate.name == "Remote-Qwen"),
        None,
    )
    if not isinstance(provider, QwenCustomProvider):
        raise RuntimeError("Remote-Qwen is not configured as QwenCustomProvider.")
    return provider


async def _normal_json_request(
    provider: QwenCustomProvider,
    *,
    system_prompt: str,
    user_content: str,
    max_output_tokens: int,
) -> BenchmarkResult:
    started = time.perf_counter()
    async with httpx.AsyncClient() as client:
        response = await client.post(
            provider.endpoint,
            headers={
                "Authorization": f"Bearer {provider.api_key}",
                "Connection": "close",
            },
            json={
                "model": provider.model,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_content},
                ],
                "temperature": 0.0,
                "response_format": {"type": "json_object"},
                "chat_template_kwargs": {"enable_thinking": False},
                "max_tokens": max_output_tokens,
            },
            timeout=provider.timeout,
        )
    response.raise_for_status()
    payload: dict[str, Any] = response.json()
    message = payload["choices"][0]["message"]
    content = message.get("content") or message.get("reasoning_content") or ""
    usage = payload.get("usage", {})
    return BenchmarkResult(
        mode="normal_json",
        elapsed_seconds=time.perf_counter() - started,
        input_tokens=usage.get("prompt_tokens"),
        output_tokens=usage.get("completion_tokens"),
        output_characters=len(content),
        finish_reason=payload["choices"][0].get("finish_reason"),
    )


async def _schema_request(
    provider: QwenCustomProvider,
    *,
    system_prompt: str,
    user_content: str,
    max_output_tokens: int,
) -> BenchmarkResult:
    bounded_provider = copy(provider)
    bounded_provider.max_output_tokens = max_output_tokens
    started = time.perf_counter()
    response = await bounded_provider.generate_structured(
        system_prompt=system_prompt,
        user_content=user_content,
        response_model=LLMSemanticCVResponse,
        temperature=0.0,
    )
    return BenchmarkResult(
        mode="full_schema",
        elapsed_seconds=time.perf_counter() - started,
        input_tokens=response.input_tokens,
        output_tokens=response.output_tokens,
        output_characters=len(response.raw_response),
        finish_reason=None,
    )


def _print_result(result: BenchmarkResult) -> None:
    token_rate = (
        f"{result.tokens_per_second:.2f} tok/s"
        if result.tokens_per_second is not None
        else "n/a"
    )
    print(
        f"{result.mode}: {result.elapsed_seconds:.2f}s | "
        f"input={result.input_tokens or 'n/a'} | "
        f"output={result.output_tokens or 'n/a'} | "
        f"rate={token_rate} | chars={result.output_characters} | "
        f"finish={result.finish_reason or 'n/a'}",
        flush=True,
    )


async def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--max-output-tokens",
        type=int,
        default=CV_STRUCTURING_MAX_OUTPUT_TOKENS,
    )
    parser.add_argument(
        "--mode",
        choices=("normal_json", "full_schema", "both"),
        default="both",
    )
    args = parser.parse_args()
    if args.max_output_tokens < 1:
        raise SystemExit("--max-output-tokens must be positive")

    raw = build_manual_text_extraction(_SYNTHETIC_CV)
    prompt = build_block_parsing_prompt()
    blocks = format_raw_extraction_blocks(raw)
    provider = _remote_qwen()

    print("Synthetic input only. Endpoint:", provider.endpoint, flush=True)
    print("Model label:", provider.model, flush=True)
    print("Output cap:", args.max_output_tokens, flush=True)
    if args.mode in ("normal_json", "both"):
        _print_result(
            await _normal_json_request(
                provider,
                system_prompt=prompt,
                user_content=blocks,
                max_output_tokens=args.max_output_tokens,
            )
        )
    if args.mode in ("full_schema", "both"):
        _print_result(
            await _schema_request(
                provider,
                system_prompt=prompt,
                user_content=blocks,
                max_output_tokens=args.max_output_tokens,
            )
        )


if __name__ == "__main__":
    asyncio.run(main())
