import asyncio
import logging
import os
import sys

# Ensure we can import from the parent 'backend' directory
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from pydantic import BaseModel

from app.core import config
from app.services.ai_service import call_llm_with_fallback
from app.services.llm_provider import OpenAIProvider

# Reduce logging clutter for the test
logging.basicConfig(level=logging.WARNING)


class MockTestResponse(BaseModel):
    test_message: str
    success: bool


async def test_individual_providers():
    print("\n" + "=" * 50)
    print("🚀 TESTING INDIVIDUAL PROVIDERS")
    print("=" * 50)

    for provider in config.PROVIDERS:
        print(f"\n⏳ Testing {provider.name} (Model: {provider.model})...")
        try:
            result = await provider.generate_structured(
                system_prompt="You are a test bot. Return a JSON object with 'test_message'='Hello' and 'success'=true.",
                user_content="Say hello!",
                response_model=MockTestResponse,
                temperature=0.0,
            )
            print(
                f"✅ {provider.name} SUCCESS! Response: {result.data.model_dump_json()}"
            )
            print(f"📈 Tokens: {result.input_tokens} in / {result.output_tokens} out")
        except Exception as e:
            print(f"❌ {provider.name} FAILED! Error: {e}")


async def test_real_fallback_with_bad_key():
    print("\n" + "=" * 50)
    print("🎭 TESTING REAL FALLBACK WITH BAD MAIN KEY")
    print("=" * 50)

    # 1. Save original
    original_providers = config.PROVIDERS.copy()

    # Find a valid provider to act as our safety net
    valid_provider = None
    for p in original_providers:
        # Check if it has a likely valid key
        if (
            isinstance(p, OpenAIProvider)
            and p.client.api_key
            and p.client.api_key != ""
        ):
            valid_provider = p
            break

    if not valid_provider:
        print("⚠️ No valid fallback provider found. Skipping real fallback test.")
        return

    print(f"Using {valid_provider.name} as the valid fallback.")

    # 2. Setup Providers: Fake Gemini (Will Fail) -> Real Provider (Will Succeed)
    config.PROVIDERS = [
        OpenAIProvider(
            name="IntentionallyBadGemini",
            model="gemini-1.5-flash",
            api_key="bad_invalid_key_12345",
            base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
        ),
        valid_provider,
    ]

    print("Injecting 2 providers into config.PROVIDERS:")
    print("  1. IntentionallyBadGemini (Expected to fail auth)")
    print(f"  2. {valid_provider.name} (Expected to succeed)")

    try:
        result = await call_llm_with_fallback(
            system_prompt="You are a test bot. Return a JSON object with 'test_message'='Fallback Worked' and 'success'=true.",
            user_input="Hello",
            response_model=MockTestResponse,
            max_retries=1,
        )
        print(
            f"\n✅ Real Fallback logic successfully bypassed the bad key! Result: {result}"
        )
    except Exception as e:
        print(f"\n❌ Real Fallback logic failed: {e}")
    finally:
        config.PROVIDERS = original_providers


async def test_fallback_mechanism():
    print("\n" + "=" * 50)
    print("🔄 TESTING WATERFALL FALLBACK MECHANISM (MOCKS)")
    print("=" * 50)

    # 1. Save original providers
    original_providers = config.PROVIDERS.copy()

    # 2. Setup mock providers
    from app.services.llm_provider import BaseAIProvider, ProviderResult

    class MockFailProvider(BaseAIProvider):
        async def generate_structured(self, *args, **kwargs):
            raise Exception("Simulated Provider Rate Limit / Error!")

    class MockSuccessProvider(BaseAIProvider):
        async def generate_structured(self, *args, **kwargs):
            return ProviderResult(
                data=MockTestResponse(
                    test_message="Recovered via mock fallback!", success=True
                ),
                input_tokens=10,
                output_tokens=10,
                raw_response="{}",
            )

    # 3. Inject mock providers
    config.PROVIDERS = [
        MockFailProvider(name="MockFail_1", model="fail-1"),
        MockFailProvider(name="MockFail_2", model="fail-2"),
        MockSuccessProvider(name="MockSuccess", model="success-1"),
    ]

    print("Injecting 3 mock providers:")
    print("  1. MockFail_1 (Will fail)")
    print("  2. MockFail_2 (Will fail)")
    print("  3. MockSuccess (Will succeed)")

    try:
        result = await call_llm_with_fallback(
            system_prompt="Return a valid JSON",
            user_input="Hello",
            response_model=MockTestResponse,
            max_retries=1,
        )
        print(
            f"\n✅ Fallback logic successfully bypassed errors and retrieved: {result}"
        )
    except Exception as e:
        print(f"\n❌ Fallback logic failed unexpectedly: {e}")
    finally:
        config.PROVIDERS = original_providers


async def run_tests():
    await test_individual_providers()
    await test_real_fallback_with_bad_key()
    await test_fallback_mechanism()
    print("\n🎉 All tests completed!\n")


if __name__ == "__main__":
    asyncio.run(run_tests())
