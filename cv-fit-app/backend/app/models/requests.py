"""Pydantic request models — inbound payloads from API clients."""

from uuid import UUID

from pydantic import AliasChoices, BaseModel, Field

from app.models.domain import Message

# ---------------------------------------------------------------------------
# CV routes
# ---------------------------------------------------------------------------


class LayoutLine(BaseModel):
    """Layout metadata for a single extracted line (Phase 3)."""

    text: str
    page: int
    x: float
    y: float
    width: float
    height: float
    font_size: float | None = None
    font_weight: float | None = None
    bullet_marker: str | None = None
    normalized_text: str = ""
    column_id: str | None = None
    joined_to_prev: bool = False
    is_page_break_marker: bool = False
    is_layout_artifact: bool = False
    page_height: float | None = None
    source_line_id: str | None = None


class AnalyzeCVRequest(BaseModel):
    cv_text: str
    jd_text: str | None = ""
    layout_data: list[LayoutLine] | None = None
    raw_extraction_ref_id: UUID | None = None


# ---------------------------------------------------------------------------
# Interview routes
# ---------------------------------------------------------------------------


class InterviewChatRequest(BaseModel):
    cv_text: str
    chat_history: list[Message]
    current_question: int = 1  # e.g., 1
    total_questions: int = 5  # e.g., 5
    interview_type: str = "general"  # "hr", "technical", "manager", "general"
    jd_text: str | None = ""


class InterviewFinishRequest(BaseModel):
    cv_text: str
    chat_history: list[Message]
    interview_type: str = "general"  # "hr", "technical", "manager", "general"
    jd_text: str | None = ""


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
    writing_type: str  # "email", "linkedin", "zalo", "custom"
    tone: str  # e.g. "Chuyên nghiệp", "Ngắn gọn", "Tự tin"
    jd_text: str | None = ""
    custom_prompt: str | None = None
    language: str | None = "auto"


# ---------------------------------------------------------------------------
# Job Finder routes
# ---------------------------------------------------------------------------


class ParseProfileRequest(BaseModel):
    cv_text: str


# ---------------------------------------------------------------------------
# Job search
# ---------------------------------------------------------------------------


class JobSearchRequest(BaseModel):
    model_config = {"populate_by_name": True}

    cv_text: str = Field(validation_alias=AliasChoices("cvText", "cv_text"))
    target_role: str | None = Field(
        default=None,
        validation_alias=AliasChoices("targetRole", "target_role"),
    )
    location: str | None = None
    date_range: str | None = Field(
        default=None,
        validation_alias=AliasChoices("dateRange", "date_range"),
    )
    sources: list[str] | None = None
