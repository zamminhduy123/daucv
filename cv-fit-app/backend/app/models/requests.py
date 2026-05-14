"""
Pydantic request models — inbound payloads from API clients.
"""

from pydantic import BaseModel
from typing import List, Optional

from app.models.domain import Message


# ---------------------------------------------------------------------------
# CV routes
# ---------------------------------------------------------------------------

class AnalyzeCVRequest(BaseModel):
    cv_text: str
    jd_text: Optional[str] = ""


# ---------------------------------------------------------------------------
# Interview routes
# ---------------------------------------------------------------------------

class InterviewChatRequest(BaseModel):
    cv_text: str
    chat_history: List[Message]
    current_question: int = 1      # e.g., 1
    total_questions: int = 5       # e.g., 5
    interview_type: str = "general"  # "hr", "technical", "manager", "general"
    jd_text: Optional[str] = ""


class InterviewFinishRequest(BaseModel):
    cv_text: str
    chat_history: List[Message]
    interview_type: str = "general"  # "hr", "technical", "manager", "general"
    jd_text: Optional[str] = ""


# ---------------------------------------------------------------------------
# TTS
# ---------------------------------------------------------------------------

class TTSRequest(BaseModel):
    text: str


# ---------------------------------------------------------------------------
# Writer routes
# ---------------------------------------------------------------------------

class WriterRequest(BaseModel):
    cv_text: str
    writing_type: str       # "email", "linkedin", "zalo", "custom"
    tone: str               # e.g. "Chuyên nghiệp", "Ngắn gọn", "Tự tin"
    jd_text: Optional[str] = ""
    custom_prompt: Optional[str] = None
