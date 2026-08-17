"""Application configuration and LLM provider setup.
Loads environment variables and initialises the OpenAI-compatible provider list.
"""

import os
import sys
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
# Must be provisioned as a private Supabase bucket. Raw CV text must never be
# stored in the public source-PDF bucket.
RAW_EXTRACTION_BUCKET = os.getenv("RAW_EXTRACTION_BUCKET", "cv")
is_testing = "pytest" in sys.modules or (len(sys.argv) > 0 and "pytest" in sys.argv[0])
default_skip = (ENV == "development") and not is_testing
SKIP_RAW_EXTRACTION_UPLOAD = (
    os.getenv(
        "SKIP_RAW_EXTRACTION_UPLOAD",
        "true" if default_skip else "false",
    ).lower()
    == "true"
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

from app.services.llm_provider import QwenCustomProvider  # noqa: E402

# Remote Qwen runs on our own GPU host. It supports long contexts, but large
# structured CV requests can legitimately take minutes to finish. Keep this
# separate from any short local-provider timeout retained for compatibility.
LOCAL_LLM_TIMEOUT = float(os.getenv("LOCAL_LLM_TIMEOUT", "120.0"))
REMOTE_QWEN_TIMEOUT = float(os.getenv("REMOTE_QWEN_TIMEOUT", "1200.0"))
REMOTE_QWEN_MAX_CONCURRENT = int(os.getenv("REMOTE_QWEN_MAX_CONCURRENT", "1"))
REMOTE_QWEN_QUEUE_TIMEOUT = float(os.getenv("REMOTE_QWEN_QUEUE_TIMEOUT", "60.0"))
if REMOTE_QWEN_MAX_CONCURRENT < 1:
    raise ValueError("REMOTE_QWEN_MAX_CONCURRENT must be at least 1.")
if REMOTE_QWEN_QUEUE_TIMEOUT <= 0:
    raise ValueError("REMOTE_QWEN_QUEUE_TIMEOUT must be positive.")
CLOUD_LLM_TIMEOUT = float(os.getenv("CLOUD_LLM_TIMEOUT", "300.0"))
LLM_MAX_OUTPUT_TOKENS = int(os.getenv("LLM_MAX_OUTPUT_TOKENS", "8192"))
QWEN_MAX_OUTPUT_TOKENS = int(os.getenv("QWEN_MAX_OUTPUT_TOKENS", "100000"))
CV_STRUCTURING_MAX_OUTPUT_TOKENS = int(
    os.getenv("CV_STRUCTURING_MAX_OUTPUT_TOKENS", "12000")
)
# The experimental atom-plan mapper deliberately calls the model once per
# deterministic section. A cap per section prevents one long CV from ending
# in a single truncated JSON document.
CV_BLOCK_PLAN_SECTION_MAX_OUTPUT_TOKENS = int(
    os.getenv("CV_BLOCK_PLAN_SECTION_MAX_OUTPUT_TOKENS", "1800")
)
# V3 emits only compact, section-local integer ranges.  Keep it isolated until
# its shadow-comparison gates prove it is at least as faithful as V1.
CV_RANGE_PLAN_SECTION_MAX_OUTPUT_TOKENS = int(
    os.getenv("CV_RANGE_PLAN_SECTION_MAX_OUTPUT_TOKENS", "2048")
)
CV_MAPPER_MODE = os.getenv("CV_MAPPER_MODE", "semantic_v1")
if CV_MAPPER_MODE not in {"semantic_v1", "range_v3"}:
    raise ValueError("CV_MAPPER_MODE must be 'semantic_v1' or 'range_v3'.")
CV_MAPPER_V3_ROLLOUT_PERCENT = int(os.getenv("CV_MAPPER_V3_ROLLOUT_PERCENT", "0"))
if not 0 <= CV_MAPPER_V3_ROLLOUT_PERCENT <= 100:
    raise ValueError("CV_MAPPER_V3_ROLLOUT_PERCENT must be between 0 and 100.")
CV_MAPPER_V3_FALLBACK_TO_V1 = os.getenv(
    "CV_MAPPER_V3_FALLBACK_TO_V1", "true"
).strip().lower() in {"1", "true", "yes", "on"}
CV_EVALUATION_MAX_OUTPUT_TOKENS = int(
    os.getenv("CV_EVALUATION_MAX_OUTPUT_TOKENS", "1500")
)
CV_STRUCTURING_MAX_RETRIES = int(os.getenv("CV_STRUCTURING_MAX_RETRIES", "1"))
CV_ANALYSIS_REQUEST_TIMEOUT = float(
    os.getenv(
        "CV_ANALYSIS_REQUEST_TIMEOUT",
        str(max(REMOTE_QWEN_TIMEOUT + 120.0, CLOUD_LLM_TIMEOUT + 120.0, 900.0)),
    ),
)

PROVIDERS = [
    # Primary: our long-context GPU host. CV mapping can take minutes and must
    # preserve dense, multi-page source blocks, which is its strongest path.
    QwenCustomProvider(
        name="Remote-Qwen",
        model=os.getenv("QWEN_MODEL", "qwen2.5-7b-instruct"),
        api_key=os.getenv("QWEN_API_KEY", "not-needed"),
        endpoint=os.getenv(
            "QWEN_ENDPOINT",
            "http://127.0.0.1:8000/v1/chat/completions",
        ),
        timeout=REMOTE_QWEN_TIMEOUT,
        max_output_tokens=QWEN_MAX_OUTPUT_TOKENS,
    ),
    # Secondary: NVIDIA (Llama 3.1 70B)
    # OpenAIProvider(
    #     name="NVIDIA",
    #     model=os.getenv("NVIDIA_MODEL", "meta/llama-3.1-70b-instruct"),
    #     api_key=os.getenv("NVIDIA_API_KEY", ""),
    #     base_url=os.getenv("NVIDIA_BASE_URL", "https://integrate.api.nvidia.com/v1"),
    #     timeout=CLOUD_LLM_TIMEOUT,
    #     max_output_tokens=LLM_MAX_OUTPUT_TOKENS,
    # ),
    # Tertiary: Gemini Flash.
    # OpenAIProvider(
    #     name="Gemini",
    #     model=os.getenv("GEMINI_MODEL", "gemini-2.5-flash"),
    #     api_key=os.getenv("GEMINI_API_KEY", ""),
    #     base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
    #     timeout=CLOUD_LLM_TIMEOUT,
    #     max_output_tokens=LLM_MAX_OUTPUT_TOKENS,
    # ),
    # 4. Final Fallback: OpenRouter
    # OpenAIProvider(
    #     name="OpenRouter",
    #     model="google/gemini-2.5-flash",
    #     api_key=os.getenv("OPENROUTER_API_KEY", ""),
    #     base_url="https://openrouter.ai/api/v1",
    #     timeout=CLOUD_LLM_TIMEOUT,
    #     max_output_tokens=LLM_MAX_OUTPUT_TOKENS,
    # ),
]
