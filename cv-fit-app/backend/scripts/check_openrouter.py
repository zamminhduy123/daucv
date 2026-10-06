#!/usr/bin/env python3
"""Smoke-test the OpenRouter fallback provider with a small structured request.

Uses the same provider object, model list and data policy as the backend
(app.core.config.PROVIDERS), so a pass here means the waterfall fallback will
work. Each run costs one request from your free daily quota.

    cd backend && python scripts/check_openrouter.py
    OPENROUTER_MODEL=google/gemma-4-31b-it:free python scripts/check_openrouter.py
"""

import asyncio
import sys
import time
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))

from pydantic import BaseModel  # noqa: E402

from app.core import config  # noqa: E402

SYSTEM_PROMPT = (
    "Bạn là chuyên gia tuyển dụng. Trả về JSON đúng schema: "
    '{"match_score": <0-100 integer>, "missing_skills": [<string>], '
    '"summary_vi": "<one Vietnamese sentence>"}. Chỉ trả JSON.'
)
USER_CONTENT = (
    "CV: Kỹ sư phần mềm 3 năm kinh nghiệm React, Electron, TypeScript; "
    "từng làm ứng dụng desktop cho hàng triệu người dùng.\n"
    "JD: Tuyển Frontend Engineer, yêu cầu React, TypeScript, Next.js, testing."
)


class SmokeResult(BaseModel):
    match_score: int
    missing_skills: list[str]
    summary_vi: str


async def main() -> int:
    provider = next((p for p in config.PROVIDERS if p.name == "OpenRouter"), None)
    if provider is None:
        print("FAIL: no OpenRouter provider in config.PROVIDERS")
        return 1
    if not provider.is_configured:
        print("FAIL: OPENROUTER_API_KEY is not set in backend/.env")
        return 1

    body = config.openrouter_extra_body()
    print(f"models tried in order: {body['models']}")
    print(f"data_collection={body['provider']['data_collection']}")
    start = time.perf_counter()
    try:
        result = await provider.generate_structured(
            system_prompt=SYSTEM_PROMPT,
            user_content=USER_CONTENT,
            response_model=SmokeResult,
            temperature=0.2,
        )
    except Exception as exc:  # noqa: BLE001 - report any failure plainly
        print(
            f"FAIL after {time.perf_counter() - start:.1f}s: {type(exc).__name__}: {exc}"
        )
        if "data policy" in str(exc).lower() or "no endpoints" in str(exc).lower():
            print(
                "Hint: no free endpoint matches data_collection=deny for these "
                "models. Try another model, or set OPENROUTER_DATA_COLLECTION=allow "
                "only after checking its data policy."
            )
        return 1

    print(f"OK in {time.perf_counter() - start:.1f}s")
    print(f"tokens: in={result.input_tokens} out={result.output_tokens}")
    print(f"parsed: {result.data.model_dump()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
