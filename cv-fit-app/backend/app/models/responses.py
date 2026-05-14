"""
Pydantic response models — outbound payloads returned to API clients.
"""

from pydantic import BaseModel
from typing import List

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


# ---------------------------------------------------------------------------
# CV Analysis response
# ---------------------------------------------------------------------------

class CVAnalysisResponse(BaseModel):
    match_score: int               # 0 to 100 - overall match
    match_headline: str            # e.g. "Rất phù hợp — Khả năng lọt vào vòng phỏng vấn cao."
    match_summary: str             # 2-3 sentences explaining the score and what to focus on

    # 6 sub-scores (all 0 to 100)
    technical_match: int
    experience_relevance: int
    keyword_coverage: int
    impact_evidence: int
    tone_quality: int
    ats_readiness: int

    missing_keywords: List[str]           # Up to 5 missing keywords
    suggested_edits: List[SuggestedEdit]  # 3 to 5 high-impact bullet rewrites

    # Widgets data
    cv_strengths: List[str]                          # 3-4 bullet points of what the CV does well
    prioritized_keywords: List[PrioritizedKeyword]   # Missing keywords with priority levels
    evidence_analysis: List[EvidenceAnalysis]         # 4-5 items evaluating claims vs evidence


# ---------------------------------------------------------------------------
# Writer response
# ---------------------------------------------------------------------------

class WriterResponse(BaseModel):
    subject_line: str       # Catchy subject line (empty if not applicable)
    content: str            # Main generated letter/message
    tips: List[str]         # 1-2 quick actionable tips
