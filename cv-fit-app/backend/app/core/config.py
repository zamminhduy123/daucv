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

_RAW_ORIGINS = os.getenv(
    "CORS_ALLOWED_ORIGINS",
    "http://localhost:3000,http://127.0.0.1:3000,https://www.daucv.com,https://daucv.com",
)
CORS_ALLOWED_ORIGINS: list[str] = [
    o.strip() for o in _RAW_ORIGINS.split(",") if o.strip()
]

# ---------------------------------------------------------------------------
# PDF upload size limit (bytes) — protects against OOM DoS
# ---------------------------------------------------------------------------

PDF_MAX_SIZE = int(os.getenv("PDF_MAX_SIZE", str(10 * 1024 * 1024)))  # 10 MB default

# ---------------------------------------------------------------------------
# Database & Authentication
# ---------------------------------------------------------------------------

ENV = os.getenv("ENV", "development").lower()

DATABASE_URL = os.getenv(
    "DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/postgres"
)

# Enforce NEXTAUTH_SECRET
NEXTAUTH_SECRET = os.getenv("NEXTAUTH_SECRET")
if not NEXTAUTH_SECRET:
    raise ValueError("CRITICAL: NEXTAUTH_SECRET is required in all environments.")

# Gate mock billing route in production
ALLOW_MOCK_BILLING = os.getenv("ALLOW_MOCK_BILLING", "true").lower() == "true"
if ENV == "production":
    ALLOW_MOCK_BILLING = os.getenv("ALLOW_MOCK_BILLING", "false").lower() == "true"

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

# Log level: DEBUG, INFO, WARNING, ERROR, CRITICAL
# INFO in production (suppresses DEBUG noise).
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

# ---------------------------------------------------------------------------
# LLM Waterfall Provider Configuration
# ---------------------------------------------------------------------------

from app.services.llm_provider import OpenAIProvider, QwenCustomProvider  # noqa: E402

LOCAL_LLM_TIMEOUT = float(os.getenv("LOCAL_LLM_TIMEOUT", "15.0"))
CLOUD_LLM_TIMEOUT = float(os.getenv("CLOUD_LLM_TIMEOUT", "30.0"))

PROVIDERS = [
    # 1. Primary: Qwen llama-server
    QwenCustomProvider(
        name="Local-Qwen",
        model=os.getenv("QWEN_MODEL", "qwen2.5-7b-instruct"),
        api_key=os.getenv("QWEN_API_KEY", "not-needed"),
        endpoint=os.getenv(
            "QWEN_ENDPOINT", "http://localhost:8000/v1/chat/completions"
        ),
        timeout=LOCAL_LLM_TIMEOUT,
    ),
    # 2. Primary Fallback: Gemini (via OpenAI shim)
    OpenAIProvider(
        name="Gemini",
        model="gemini-2.5-flash",
        api_key=os.getenv("GEMINI_API_KEY", ""),
        base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
        timeout=CLOUD_LLM_TIMEOUT,
    ),
    # 3. Secondary Fallback: Groq
    OpenAIProvider(
        name="Groq",
        model="llama-3.3-70b-versatile",
        api_key=os.getenv("GROQ_API_KEY", ""),
        base_url="https://api.groq.com/openai/v1",
        timeout=CLOUD_LLM_TIMEOUT,
    ),
    # 4. Final Fallback: OpenRouter
    OpenAIProvider(
        name="OpenRouter",
        model="google/gemini-2.5-flash",
        api_key=os.getenv("OPENROUTER_API_KEY", ""),
        base_url="https://openrouter.ai/api/v1",
        timeout=CLOUD_LLM_TIMEOUT,
    ),
]
