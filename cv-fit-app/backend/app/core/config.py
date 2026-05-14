"""
Application configuration and LLM provider setup.
Loads environment variables and initialises the OpenAI-compatible provider list.
"""

import os
from pathlib import Path

from dotenv import load_dotenv
from openai import AsyncOpenAI

load_dotenv()

# ---------------------------------------------------------------------------
# Project paths
# ---------------------------------------------------------------------------

BASE_DIR = Path(__file__).resolve().parent.parent.parent  # …/backend
LOGS_DIR = BASE_DIR / "logs"
LOGS_DIR.mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------------------------------
# LLM Waterfall Provider Configuration
# ---------------------------------------------------------------------------

PROVIDERS: list[dict] = [
    {
        "name": "Gemini",
        "client": AsyncOpenAI(
            api_key=os.getenv("GEMINI_API_KEY", "dummy"),
            base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
        ),
        "model": "gemini-2.5-flash",
    },
    {
        "name": "Groq",
        "client": AsyncOpenAI(
            api_key=os.getenv("GROQ_API_KEY", "dummy"),
            base_url="https://api.groq.com/openai/v1",
        ),
        "model": "llama-3.3-70b-versatile",
    },
    {
        "name": "OpenRouter",
        "client": AsyncOpenAI(
            api_key=os.getenv("OPENROUTER_API_KEY", "dummy"),
            base_url="https://openrouter.ai/api/v1",
        ),
        "model": "google/gemini-2.5-flash",
    },
]
