import sys
import os
import asyncio
import logging
from pydantic import BaseModel

# Ensure we can import from the parent 'backend' directory
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import main

# Reduce logging clutter for the test
logging.basicConfig(level=logging.WARNING)

class TestResponse(BaseModel):
    test_message: str
    success: bool

async def test_individual_providers():
    print("\n" + "="*50)
    print("🚀 TESTING INDIVIDUAL PROVIDERS")
    print("="*50)
    
    for provider in main.PROVIDERS:
        name = provider["name"]
        model = provider["model"]
        client = provider["client"]
        
        print(f"\n⏳ Testing {name} (Model: {model})...")
        try:
            response = await client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": "You are a test bot. Return a JSON object with 'test_message'='Hello' and 'success'=true."},
                    {"role": "user", "content": "Say hello!"}
                ],
                response_format={"type": "json_object"},
                temperature=0.0,
                max_tokens=50
            )
            content = response.choices[0].message.content
            print(f"✅ {name} SUCCESS! Response: {content}")
        except Exception as e:
            print(f"❌ {name} FAILED! Error: {e}")

async def test_real_fallback_with_bad_key():
    print("\n" + "="*50)
    print("🎭 TESTING REAL FALLBACK WITH BAD MAIN KEY")
    print("="*50)
    
    # 1. Save original
    original_providers = main.PROVIDERS.copy()
    
    # Check if we have at least one valid key to test fallback
    valid_provider = None
    for p in original_providers:
        if p["client"].api_key and p["client"].api_key != "dummy":
            valid_provider = p
            break
            
    if not valid_provider:
        print("⚠️ No valid API keys found in .env to test real fallback. Skipping.")
        return

    print(f"Using {valid_provider['name']} as the valid fallback provider.")
    
    from openai import AsyncOpenAI
    
    # 2. Setup Providers: Fake Gemini (Will Fail) -> Real Provider (Will Succeed)
    main.PROVIDERS = [
        {
            "name": "IntentionallyBadGemini",
            "client": AsyncOpenAI(api_key="bad_invalid_key_12345", base_url="https://generativelanguage.googleapis.com/v1beta/openai/"),
            "model": "gemini-1.5-flash"
        },
        valid_provider
    ]
    
    print("Injecting 2 providers into main.PROVIDERS:")
    print("  1. IntentionallyBadGemini (Expected to fail auth)")
    print(f"  2. {valid_provider['name']} (Expected to succeed)")
    
    try:
        result = await main.call_llm_with_fallback(
            system_prompt="You are a test bot. Return a JSON object with 'test_message'='Fallback Worked' and 'success'=true.",
            user_input="Hello",
            response_model=TestResponse,
            max_retries=1
        )
        print(f"\n✅ Real Fallback logic successfully bypassed the bad key! Result: {result}")
    except Exception as e:
        print(f"\n❌ Real Fallback logic failed: {e}")
    finally:
        main.PROVIDERS = original_providers

async def test_fallback_mechanism():
    print("\n" + "="*50)
    print("🔄 TESTING WATERFALL FALLBACK MECHANISM")
    print("="*50)
    
    # 1. Save original providers
    original_providers = main.PROVIDERS.copy()
    
    # 2. Setup mock clients
    class MockFailedClient:
        class chat:
            class completions:
                @staticmethod
                async def create(*args, **kwargs):
                    raise Exception("Simulated Provider Rate Limit / Error!")
                    
    class MockSuccessClient:
        class chat:
            class completions:
                @staticmethod
                async def create(*args, **kwargs):
                    class Message:
                        content = '{"test_message": "Recovered successfully via fallback!", "success": true}'
                    class Choice:
                        message = Message()
                    class MockResponse:
                        choices = [Choice()]
                    return MockResponse()

    # 3. Inject mock providers directly into main.py's state
    main.PROVIDERS = [
        {"name": "MockFailBot_1", "client": MockFailedClient(), "model": "fail-model-1"},
        {"name": "MockFailBot_2", "client": MockFailedClient(), "model": "fail-model-2"},
        {"name": "MockSuccessBot", "client": MockSuccessClient(), "model": "success-model"},
    ]
    
    print("Injecting 3 mock providers:")
    print("  1. MockFailBot_1 (Will fail)")
    print("  2. MockFailBot_2 (Will fail)")
    print("  3. MockSuccessBot (Will succeed)")
    print("\nRunning `call_llm_with_fallback`...")
    
    try:
        result = await main.call_llm_with_fallback(
            system_prompt="Return a valid JSON",
            user_input="Hello",
            response_model=TestResponse,
            max_retries=1
        )
        print(f"\n✅ Fallback logic successfully bypassed errors and retrieved: {result}")
    except Exception as e:
        print(f"\n❌ Fallback logic failed unexpectedly: {e}")
    finally:
        # Restore real providers
        main.PROVIDERS = original_providers

async def run_tests():
    await test_individual_providers()
    await test_real_fallback_with_bad_key()
    await test_fallback_mechanism()
    print("\n🎉 All tests completed!\n")

if __name__ == "__main__":
    asyncio.run(run_tests())
