"""
Pydantic response models — outbound payloads returned to API clients.
"""

from pydantic import BaseModel, ConfigDict, Field
from typing import Annotated, Dict, List

from app.models.domain import (
    LiveMetrics,
    TurnAnalysis,
    SubScore,
    AIFeedbackSummary,
    SuggestedEdit,
    PrioritizedKeyword,
    EvidenceAnalysis,
)


# ---------------------------------------------------------------------------
# Interview responses
# ---------------------------------------------------------------------------

class InterviewTurnResponse(BaseModel):
    ai_feedback: str
    next_question: str
    hint_for_user: str
    metrics: LiveMetrics


class FinalInterviewReport(BaseModel):
    overall_score: int              # 0-100
    overall_feedback: str           # 2-3 sentences summarizing performance
    sub_scores: List[SubScore]      # Exactly 5 items matching the categories above
    key_strengths: List[str]        # 2-3 bullet points
    areas_for_improvement: List[str] # 2-3 bullet points
    top_topics_covered: List[str]   # e.g., ["React", "State Management", "Behavioral"]
    ai_feedback_summary: AIFeedbackSummary
    turn_by_turn_analysis: List[TurnAnalysis]


class ScoreBreakdown(BaseModel):
    weights: Dict[str, float]
    raw_score: int = Field(ge=0, le=100)
    critical_missing_count: int = Field(ge=0)
    high_missing_count: int = Field(ge=0)
    unsupported_claim_count: int = Field(ge=0)
    critical_missing_penalty: int = Field(ge=0)
    high_missing_penalty: int = Field(ge=0)
    unsupported_claim_penalty: int = Field(ge=0)
    total_penalty: int = Field(ge=0)
    final_score: int = Field(ge=0, le=100)


# ---------------------------------------------------------------------------
# CV Analysis response
# ---------------------------------------------------------------------------

class CVAnalysisLLMResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    match_headline: str
    match_summary: str

    # 6 sub-scores — all clamped to 0-100
    technical_match: int = Field(ge=0, le=100)
    experience_relevance: int = Field(ge=0, le=100)
    keyword_coverage: int = Field(ge=0, le=100)
    impact_evidence: int = Field(ge=0, le=100)
    tone_quality: int = Field(ge=0, le=100)
    ats_readiness: int = Field(ge=0, le=100)

    missing_keywords: Annotated[List[str], Field(max_length=6)]
    suggested_edits: Annotated[List[SuggestedEdit], Field(min_length=2, max_length=5)]

    # Widgets data
    cv_strengths: Annotated[List[str], Field(min_length=2, max_length=5)]
    prioritized_keywords: Annotated[List[PrioritizedKeyword], Field(max_length=6)]
    evidence_analysis: Annotated[List[EvidenceAnalysis], Field(min_length=3, max_length=6)]


class CVAnalysisResponse(CVAnalysisLLMResponse):
    match_score: int = Field(ge=0, le=100)
    score_breakdown: ScoreBreakdown


# ---------------------------------------------------------------------------
# Writer response
# ---------------------------------------------------------------------------

class WriterResponse(BaseModel):
    subject_line: str       # Catchy subject line (empty if not applicable)
    content: str            # Main generated letter/message
    tips: List[str]         # 1-2 quick actionable tips
