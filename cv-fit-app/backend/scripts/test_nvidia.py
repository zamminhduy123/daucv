import asyncio
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv
from pydantic import BaseModel

from app.core import config

load_dotenv()


class TestResult(BaseModel):
    status: str
    message: str


async def main():
    print("=" * 60)
    print("🚀 TESTING NVIDIA PROVIDER")
    print("=" * 60)

    nvidia_provider = None
    for p in config.PROVIDERS:
        if p.name == "NVIDIA":
            nvidia_provider = p
            break

    if not nvidia_provider:
        print("❌ NVIDIA provider not found in config.PROVIDERS")
        return

    print(f"📍 Model:    {nvidia_provider.model}")
    print(
        f"🔑 API Key:  {'Present (' + nvidia_provider.client.api_key[:8] + '...)' if nvidia_provider.client.api_key else 'MISSING'}"
    )
    print(f"🌐 Base URL: {nvidia_provider.client.base_url}")
    print("-" * 60)
    print("⏳ Sending test request to NVIDIA API...")

    try:
        res = await nvidia_provider.generate_structured(
            system_prompt="You are a status checker. Return JSON with status='ok' and message='NVIDIA provider is working'.",
            user_content="Respond to test.",
            response_model=TestResult,
            temperature=0.0,
        )
        print("\n✅ CONNECTION & API SUCCESSFUL!")
        print(f"Parsed Response: {res.data.model_dump_json(indent=2)}")
        print(
            f"📊 Token Usage: {res.input_tokens} input tokens / {res.output_tokens} output tokens"
        )
    except Exception as e:
        print("\n❌ NVIDIA API ERROR / FAILED!")
        print(f"Error Type: {type(e).__name__}")
        print(f"Details: {e!s}")
        if (
            "402" in str(e)
            or "quota" in str(e).lower()
            or "credit" in str(e).lower()
            or "payment" in str(e).lower()
            or "403" in str(e)
        ):
            print("\n🚨 OUT OF TOKENS / CREDITS OR FORBIDDEN!")


if __name__ == "__main__":
    asyncio.run(main())
