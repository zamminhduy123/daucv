import asyncio
import os
import sys
from pathlib import Path

# Add the parent directory to sys.path so we can import from 'app'
sys.path.append(str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv
from pydantic import BaseModel

from app.services.llm_provider import QwenCustomProvider

load_dotenv()


class TestResponse(BaseModel):
    summary: str
    score: int
    is_qwen: bool


async def test_qwen():
    # Setup local environment defaults for testing
    # These can be overridden by your actual .env file
    endpoint = os.getenv("QWEN_ENDPOINT", "http://localhost:8000/v1/chat/completions")
    api_key = os.getenv("QWEN_API_KEY", "not-needed")
    model = os.getenv("QWEN_MODEL", "qwen2.5-7b-instruct")

    os.environ["QWEN_ENDPOINT"] = endpoint
    os.environ["QWEN_API_KEY"] = api_key
    os.environ["QWEN_MODEL"] = model

    print("🚀 Testing Qwen Connection")
    print(f"📍 Endpoint: {endpoint}")
    print(f"🤖 Model:    {model}")
    print("-" * 50)

    provider = QwenCustomProvider("test", model, api_key, endpoint)

    system_prompt = "You are a helpful assistant. Return ONLY a JSON object."
    user_content = "Identify yourself. Return a JSON with 'summary', 'score' (100), and 'is_qwen' (true)."

    try:
        print("⏳ Sending structured request...")
        result = await provider.generate_structured(
            system_prompt=system_prompt,
            user_content=user_content,
            response_model=TestResponse,
            temperature=0.7,
        )

        print("\n✅ CONNECTION SUCCESSFUL!")
        print(f"Parsed Response: {result.model_dump_json(indent=2)}")

    except Exception as e:
        print("\n❌ CONNECTION FAILED!")
        print(f"Error type: {type(e).__name__}")
        print(f"Details: {e!s}")
        print(
            "\n💡 Tip: Make sure your Qwen server is running and the QWEN_ENDPOINT in your .env is correct.",
        )


if __name__ == "__main__":
    asyncio.run(test_qwen())
