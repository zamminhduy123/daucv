"""
Pydantic response models — outbound payloads returned to API clients.
"""

from pydantic import BaseModel, ConfigDict, Field, model_validator
from typing import Annotated, Any, Dict, List, Literal, Optional

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
    weighted_missing_requirement_score: int = Field(ge=0)
    unsupported_claim_count: int = Field(ge=0)
    critical_missing_penalty: int = Field(ge=0)
    high_missing_penalty: int = Field(ge=0)
    missing_requirement_penalty: int = Field(ge=0)
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
    evidence_analysis: Annotated[List[EvidenceAnalysis], Field(min_length=1, max_length=6)]

    @model_validator(mode="before")
    @classmethod
    def normalize_llm_lists(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return data

        normalized = dict(data)

        for field_name, max_items in (
            ("missing_keywords", 6),
            ("suggested_edits", 5),
            ("cv_strengths", 5),
            ("prioritized_keywords", 6),
            ("evidence_analysis", 6),
        ):
            value = normalized.get(field_name)
            if isinstance(value, list):
                normalized[field_name] = value[:max_items]

        if not normalized.get("suggested_edits"):
            normalized["suggested_edits"] = [
                {
                    "section": "General",
                    "original_text": "",
                    "improved_safe": "Clarify this section with role-relevant, truthful details from your experience.",
                    "improved_with_placeholders": "Clarify this section with [specific responsibility], [tool], and [measurable outcome if true].",
                    "metric_questions": ["What measurable result can you truthfully add?"],
                    "unsupported_assumptions": [],
                    "rewrite_risk": "needs_user_input",
                    "reason": "The model did not return enough rewrite suggestions, so this fallback asks for user-confirmed details.",
                },
                {
                    "section": "General",
                    "original_text": "",
                    "improved_safe": "Use stronger action verbs while keeping every claim grounded in the original CV.",
                    "improved_with_placeholders": "Used [action verb] to deliver [scope] for [team/user/workflow], improving [metric if true].",
                    "metric_questions": ["Which scope, audience, or metric can you confirm?"],
                    "unsupported_assumptions": [],
                    "rewrite_risk": "needs_user_input",
                    "reason": "The fallback preserves safety by using placeholders instead of invented facts.",
                },
            ]
        elif isinstance(normalized["suggested_edits"], list) and len(normalized["suggested_edits"]) == 1:
            normalized["suggested_edits"].append(
                {
                    "section": "General",
                    "original_text": "",
                    "improved_safe": "Add one more concise, JD-relevant bullet using only confirmed experience.",
                    "improved_with_placeholders": "Added [JD-relevant skill] in [project/context], achieving [outcome if true].",
                    "metric_questions": ["What confirmed outcome can support this bullet?"],
                    "unsupported_assumptions": [],
                    "rewrite_risk": "needs_user_input",
                    "reason": "The model returned only one edit, so this fallback keeps the response usable.",
                }
            )

        if not normalized.get("cv_strengths"):
            normalized["cv_strengths"] = [
                "Readable baseline CV content.",
                "Contains experience that can be refined for the target role.",
            ]
        elif isinstance(normalized["cv_strengths"], list) and len(normalized["cv_strengths"]) == 1:
            normalized["cv_strengths"].append("Additional strengths require recruiter review.")

        if not normalized.get("evidence_analysis"):
            normalized["evidence_analysis"] = [
                {
                    "claim": "Role fit evidence",
                    "evidence_strength": "Weak",
                    "comment": "The model did not return detailed evidence analysis; review the CV manually.",
                }
            ]

        return normalized


class CVAnalysisResponse(CVAnalysisLLMResponse):
    role_fit_score: int = Field(ge=0, le=100)           # Raw LLM assessment — what a human would score
    match_score: int = Field(ge=0, le=100)              # "CV Match" — penalized by missing JD keywords
    score_breakdown: ScoreBreakdown


# ---------------------------------------------------------------------------
# Writer response
# ---------------------------------------------------------------------------

class WriterResponse(BaseModel):
    subject_line: str       # Catchy subject line (empty if not applicable)
    content: str            # Main generated letter/message
    tips: List[str]         # 1-2 quick actionable tips


# ---------------------------------------------------------------------------
# Job Finder response
# ---------------------------------------------------------------------------

class CandidateProfileResponse(BaseModel):
    target_roles: List[str]
    skills: List[str]
    seniority: Literal["intern", "fresher", "junior", "middle", "senior", "unknown"]
    location: str
    years_of_experience: float
    queries: List[str]


# ---------------------------------------------------------------------------
# Job search response models
# ---------------------------------------------------------------------------

class JobSourceStatus(BaseModel):
    source: str
    status: Literal["success", "failed", "timeout"]
    count: int
    error: Optional[str] = None


class JobResult(BaseModel):
    id: str
    source: Literal["itviec", "topcv", "vietnamworks", "glints", "ybox", "jobsgo", "careerviet", "vieclam24h"]
    title: str
    company: Optional[str] = None
    location: Optional[str] = None
    salary: Optional[str] = None
    level: Optional[Literal["intern", "fresher", "junior", "middle", "senior", "unknown"]] = None
    skills: List[str] = Field(default_factory=list)
    posted_text: Optional[str] = None
    url: str
    description_snippet: Optional[str] = None


class RankedJobResult(JobResult):
    match_score: int = Field(ge=0, le=100)
    match_label: Literal["good_match", "stretch"]
    match_reasons: List[str] = Field(default_factory=list)
    missing_skills: List[str] = Field(default_factory=list)

