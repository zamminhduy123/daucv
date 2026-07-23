"""Shared / domain-level Pydantic models used across multiple features."""

from typing import Literal

from pydantic import BaseModel, Field, computed_field

# ---------------------------------------------------------------------------
# CV / Match models
# ---------------------------------------------------------------------------


class ExperienceItem(BaseModel):
    company: str
    role: str
    bullet_points: list[str]


class TailoredCVSection(BaseModel):
    title: str
    items: list[str]


class TailoredCV(BaseModel):
    name: str = ""
    headline: str = ""
    contact_lines: list[str] = Field(default_factory=list)
    summary: str = ""
    sections: list[TailoredCVSection] = Field(default_factory=list)
    experience: list[ExperienceItem] = Field(default_factory=list)
    education: str = ""
    skills: list[str] = Field(default_factory=list)


class MatchResult(BaseModel):
    match_score: int
    missing_skills: list[str]
    tailored_cv: TailoredCV


# ---------------------------------------------------------------------------
# Chat / Interview models
# ---------------------------------------------------------------------------


class Message(BaseModel):
    role: str  # "user" | "assistant"
    content: str


class LiveMetrics(BaseModel):
    confidence_score: int
    confidence_feedback: str
    jd_relevance_score: int
    jd_relevance_feedback: str
    tech_vocab_rating: Literal["YẾU", "KHÁ", "TỐT", "XUẤT SẮC"]


class TurnAnalysis(BaseModel):
    question: str
    user_answer: str
    feedback: str  # What they did well and what they missed
    ideal_answer_snippet: str  # "Ví dụ cách trả lời ghi điểm: ..."


class SubScore(BaseModel):
    category: str  # "Kỹ năng chuyên môn", "Giải quyết vấn đề", "Kiến thức ngành", "Giao tiếp", "Thái độ & Hành vi"
    score: int  # 0-100
    label: str  # "Xuất sắc", "Tốt", "Khá", "Cần cố gắng"


class AIFeedbackSummary(BaseModel):
    positive: str  # "Great logical thinking..."
    warning: str  # "Try to communicate your thought process more clearly."
    actionable: str  # "Practice more system design concepts."


# ---------------------------------------------------------------------------
# CV Analysis sub-models
# ---------------------------------------------------------------------------


class SuggestedEdit(BaseModel):
    section: str  # e.g. "Kinh nghiệm làm việc", "Kỹ năng"
    original_text: str  # Exact text from the original CV that needs changing
    improved_safe: str  # Rewrite using only supported claims, no invented metrics
    improved_with_placeholders: (
        str  # Rewrite with explicit placeholders for metrics/user facts
    )
    metric_questions: list[str]  # Questions the user should answer to quantify impact
    unsupported_assumptions: list[
        str
    ]  # Claims/metrics that must not be stated as fact yet
    rewrite_risk: Literal["safe", "needs_user_input", "risky"]
    reason: str  # Short explanation in the CV's language

    @computed_field(return_type=str)
    @property
    def upgraded_text(self) -> str:
        """Backward-compatible field for clients still rendering upgraded_text."""
        return self.improved_safe


class PrioritizedKeyword(BaseModel):
    keyword: str
    priority: Literal["Critical", "High", "Medium", "Low"]


class EvidenceAnalysis(BaseModel):
    claim: str  # e.g. "Scalable system delivery", "MLOps experience"
    evidence_strength: Literal["Strong", "Medium", "Weak", "Missing"]
    comment: str  # e.g. "Supported by 8M+ MAU", "Not visible in current CV"
