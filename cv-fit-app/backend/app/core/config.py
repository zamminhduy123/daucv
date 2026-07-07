"""
Application configuration and LLM provider setup.
Loads environment variables and initialises the OpenAI-compatible provider list.
"""

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

# ---------------------------------------------------------------------------
# Project paths
# ---------------------------------------------------------------------------

BASE_DIR = Path(__file__).resolve().parent.parent.parent  # …/backend
LOGS_DIR = BASE_DIR / "logs"
LOGS_DIR.mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------------------------------
# CORS -- explicit origin allowlist (never "*" when credentials=True)
# ---------------------------------------------------------------------------

# Comma-separated origins, e.g.
#   "http://127.0.0.1:3000,https://cvfit.com"
# Default covers local development only.
_RAW_ORIGINS = os.getenv("CORS_ALLOWED_ORIGINS", "http://127.0.0.1:3000")
CORS_ALLOWED_ORIGINS: list[str] = [
    o.strip() for o in _RAW_ORIGINS.split(",") if o.strip()
]

# ---------------------------------------------------------------------------
# LLM Waterfall Provider Configuration
# ---------------------------------------------------------------------------

from app.services.llm_provider import OpenAIProvider, QwenCustomProvider  # noqa: E402

PROVIDERS = [
    # 1. Primary: Qwen llama-server
    QwenCustomProvider(
        name="Local-Qwen",
        model=os.getenv("QWEN_MODEL", "qwen2.5-7b-instruct"),
        api_key=os.getenv("QWEN_API_KEY", "not-needed"),
        endpoint=os.getenv(
            "QWEN_ENDPOINT", "http://localhost:8000/v1/chat/completions"
        ),
    ),
    # 2. Primary Fallback: Gemini (via OpenAI shim)
    OpenAIProvider(
        name="Gemini",
        model="gemini-2.5-flash",
        api_key=os.getenv("GEMINI_API_KEY", ""),
        base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
    ),
    # 3. Secondary Fallback: Groq
    OpenAIProvider(
        name="Groq",
        model="llama-3.3-70b-versatile",
        api_key=os.getenv("GROQ_API_KEY", ""),
        base_url="https://api.groq.com/openai/v1",
    ),
    # 4. Final Fallback: OpenRouter
    OpenAIProvider(
        name="OpenRouter",
        model="google/gemini-2.5-flash",
        api_key=os.getenv("OPENROUTER_API_KEY", ""),
        base_url="https://openrouter.ai/api/v1",
    ),
]
