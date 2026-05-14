"""
Shared / domain-level Pydantic models used across multiple features.
"""

from pydantic import BaseModel
from typing import List, Optional, Literal


# ---------------------------------------------------------------------------
# CV / Match models
# ---------------------------------------------------------------------------

class ExperienceItem(BaseModel):
    company: str
    role: str
    bullet_points: List[str]


class TailoredCV(BaseModel):
    name: str
    summary: str
    experience: List[ExperienceItem]
    education: str
    skills: List[str]


class MatchResult(BaseModel):
    match_score: int
    missing_skills: List[str]
    tailored_cv: TailoredCV


# ---------------------------------------------------------------------------
# Chat / Interview models
# ---------------------------------------------------------------------------

class Message(BaseModel):
    role: str   # "user" | "assistant"
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
    feedback: str                   # What they did well and what they missed
    ideal_answer_snippet: str       # "Ví dụ cách trả lời ghi điểm: ..."


class SubScore(BaseModel):
    category: str  # "Kỹ năng chuyên môn", "Giải quyết vấn đề", "Kiến thức ngành", "Giao tiếp", "Thái độ & Hành vi"
    score: int     # 0-100
    label: str     # "Xuất sắc", "Tốt", "Khá", "Cần cố gắng"


class AIFeedbackSummary(BaseModel):
    positive: str   # "Great logical thinking..."
    warning: str    # "Try to communicate your thought process more clearly."
    actionable: str # "Practice more system design concepts."


# ---------------------------------------------------------------------------
# CV Analysis sub-models
# ---------------------------------------------------------------------------

class SuggestedEdit(BaseModel):
    section: str          # e.g. "Kinh nghiệm làm việc", "Kỹ năng"
    original_text: str    # Exact text from the original CV that needs changing
    upgraded_text: str    # Rewritten, metric-driven replacement
    reason: str           # Short explanation in Vietnamese


class PrioritizedKeyword(BaseModel):
    keyword: str
    priority: Literal["High", "Medium", "Low"]


class EvidenceAnalysis(BaseModel):
    claim: str              # e.g. "Scalable system delivery", "MLOps experience"
    evidence_strength: Literal["Strong", "Medium", "Weak", "Missing"]
    comment: str            # e.g. "Supported by 8M+ MAU", "Not visible in current CV"
