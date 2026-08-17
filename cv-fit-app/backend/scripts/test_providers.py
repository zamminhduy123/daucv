"""Test call_llm_with_fallback and log_llm_input logging"""

import asyncio

from pydantic import BaseModel

from app.services.ai_service import call_llm_with_fallback


class TestModel(BaseModel):
    status: str
    summary: str


async def main():
    print("=== TESTING CALL_LLM_WITH_FALLBACK & INPUT LOGGING ===", flush=True)
    res = await call_llm_with_fallback(
        system_prompt="You are a CV analyzer. Return JSON with status='ok' and summary='Test passed'.",
        user_input="Test candidate prompt content",
        response_model=TestModel,
        feature_name="test_feature",
    )
    print(f"Result: {res}", flush=True)


if __name__ == "__main__":
    asyncio.run(main())
