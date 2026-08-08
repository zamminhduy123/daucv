"""Application configuration and LLM provider setup.
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
    "http://127.0.0.1:3000,http://127.0.0.1:3000,http://0.0.0.0:3000,"
    "http://127.0.0.1:3001,http://127.0.0.1:3001,http://0.0.0.0:3001,"
    "https://www.daucv.com,https://daucv.com",
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
    "DATABASE_URL",
    "postgresql://postgres:postgres@127.0.0.1:5432/postgres",
)

# Supabase Storage Configuration
SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", os.getenv("SUPABASE_SERVICE_ROLE_KEY", ""))
SUPABASE_BUCKET = os.getenv("SUPABASE_BUCKET", "cv")


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

LOCAL_LLM_TIMEOUT = float(os.getenv("LOCAL_LLM_TIMEOUT", "120.0"))
CLOUD_LLM_TIMEOUT = float(os.getenv("CLOUD_LLM_TIMEOUT", "300.0"))
LLM_MAX_OUTPUT_TOKENS = int(os.getenv("LLM_MAX_OUTPUT_TOKENS", "8192"))
CV_ANALYSIS_REQUEST_TIMEOUT = float(
    os.getenv("CV_ANALYSIS_REQUEST_TIMEOUT", "300.0"),
)

PROVIDERS = [
    # 1. Primary: NVIDIA (Llama 3.1 70B)
    OpenAIProvider(
        name="NVIDIA",
        model=os.getenv("NVIDIA_MODEL", "meta/llama-3.1-70b-instruct"),
        api_key=os.getenv("NVIDIA_API_KEY", ""),
        base_url=os.getenv("NVIDIA_BASE_URL", "https://integrate.api.nvidia.com/v1"),
        timeout=CLOUD_LLM_TIMEOUT,
        max_output_tokens=LLM_MAX_OUTPUT_TOKENS,
    ),
    # 2. Fast Primary Fallback: Gemini Flash (2.1s response time)
    OpenAIProvider(
        name="Gemini",
        model="gemini-2.5-flash",
        api_key=os.getenv("GEMINI_API_KEY", ""),
        base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
        timeout=CLOUD_LLM_TIMEOUT,
        max_output_tokens=LLM_MAX_OUTPUT_TOKENS,
    ),
    # 3. Secondary Fallback: Qwen llama-server
    QwenCustomProvider(
        name="Local-Qwen",
        model=os.getenv("QWEN_MODEL", "qwen2.5-7b-instruct"),
        api_key=os.getenv("QWEN_API_KEY", "not-needed"),
        endpoint=os.getenv(
            "QWEN_ENDPOINT",
            "http://127.0.0.1:8000/v1/chat/completions",
        ),
        timeout=LOCAL_LLM_TIMEOUT,
        max_output_tokens=LLM_MAX_OUTPUT_TOKENS,
    ),
    # 4. Final Fallback: OpenRouter
    OpenAIProvider(
        name="OpenRouter",
        model="google/gemini-2.5-flash",
        api_key=os.getenv("OPENROUTER_API_KEY", ""),
        base_url="https://openrouter.ai/api/v1",
        timeout=CLOUD_LLM_TIMEOUT,
        max_output_tokens=LLM_MAX_OUTPUT_TOKENS,
    ),
]
