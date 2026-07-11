"""Validate every response model can be serialized to valid JSON.

This catches model breakage (renamed fields, type changes, missing
imports) at test time — before the CI Docker build even starts.
"""

import json
from typing import Any

import pytest
from pydantic import BaseModel

from app.models.domain import (
    AIFeedbackSummary,
    EvidenceAnalysis,
    ExperienceItem,
    LiveMetrics,
    Message,
    PrioritizedKeyword,
    SubScore,
    SuggestedEdit,
    TailoredCV,
    TailoredCVSection,
    TurnAnalysis,
)
from app.models.requests import (
    AnalyzeCVRequest,
    InterviewChatRequest,
    InterviewFinishRequest,
    JobSearchRequest,
    ParseProfileRequest,
    TTSRequest,
    WriterRequest,
)
from app.models.responses import (
    CandidateProfileResponse,
    CVAnalysisLLMResponse,
    CVAnalysisResponse,
    FinalInterviewReport,
    InterviewTurnResponse,
    JobResult,
    JobSourceStatus,
    RankedJobResult,
    ScoreBreakdown,
    WriterResponse,
)
from app.schemas.tailored_cv import (
    TailoredCVVersionCreate,
    TailoredCVVersionListResponse,
    TailoredCVVersionResponse,
    TailoredCVVersionUpdate,
)

# All Pydantic models that form the API contract.
# If a new model is added and not listed here, the test suite fails loud.
ALL_MODELS: list[type[BaseModel]] = [
    # Domain models
    Message,
    LiveMetrics,
    TurnAnalysis,
    SubScore,
    AIFeedbackSummary,
    SuggestedEdit,
    PrioritizedKeyword,
    EvidenceAnalysis,
    ExperienceItem,
    TailoredCV,
    TailoredCVSection,
    # Request models
    AnalyzeCVRequest,
    InterviewChatRequest,
    InterviewFinishRequest,
    TTSRequest,
    WriterRequest,
    ParseProfileRequest,
    JobSearchRequest,
    # Response models
    CVAnalysisLLMResponse,
    CVAnalysisResponse,
    InterviewTurnResponse,
    FinalInterviewReport,
    WriterResponse,
    CandidateProfileResponse,
    ScoreBreakdown,
    JobSourceStatus,
    JobResult,
    RankedJobResult,
    TailoredCVVersionCreate,
    TailoredCVVersionUpdate,
    TailoredCVVersionResponse,
    TailoredCVVersionListResponse,
]


def minimal_data(model: type[BaseModel]) -> dict[str, Any]:
    """Return a minimal valid payload for *model*."""
    # --- SuggestedEdit (has nested list fields) ---
    if model is SuggestedEdit:
        return {
            "section": "Experience",
            "original_text": "Did backend work.",
            "improved_safe": "Built backend services.",
            "improved_with_placeholders": "Built [N] backend services.",
            "metric_questions": ["How many services?"],
            "unsupported_assumptions": [],
            "rewrite_risk": "safe",
            "reason": "Stronger verb.",
        }

    if model is PrioritizedKeyword:
        return {"keyword": "Python", "priority": "High"}

    if model is EvidenceAnalysis:
        return {
            "claim": "Backend work",
            "evidence_strength": "Weak",
            "comment": "Needs metrics.",
        }

    if model is LiveMetrics:
        return {
            "confidence_score": 70,
            "confidence_feedback": "Good.",
            "jd_relevance_score": 60,
            "jd_relevance_feedback": "Okay.",
            "tech_vocab_rating": "KHÁ",
        }

    if model is TurnAnalysis:
        return {
            "question": "Tell me about yourself.",
            "user_answer": "I am a developer.",
            "feedback": "Good start.",
            "ideal_answer_snippet": "I am a developer with 3 years experience.",
        }

    if model is SubScore:
        return {"category": "Technical", "score": 80, "label": "Tốt"}

    if model is AIFeedbackSummary:
        return {"positive": "Good.", "warning": "Try more.", "actionable": "Practice."}

    if model is ExperienceItem:
        return {
            "company": "Acme",
            "role": "Backend Dev",
            "bullet_points": ["Built APIs."],
        }

    if model is TailoredCV:
        return {
            "name": "Duy",
            "summary": "Backend developer.",
            "experience": [
                {"company": "Acme", "role": "Dev", "bullet_points": ["Built stuff."]}
            ],
            "education": "CS Degree",
            "skills": ["Python", "FastAPI"],
        }

    if model is TailoredCVSection:
        return {"title": "Projects", "items": ["Built an API."]}

    if model is TailoredCVVersionCreate:
        return {
            "tailored_cv": minimal_data(TailoredCV),
            "source_cv_text": "Duy\nduy@example.com\nExperience\nBuilt APIs.",
            "selected_design": "classic_ats",
        }

    if model is TailoredCVVersionUpdate:
        return {"selected_design": "modern_professional"}

    if model is TailoredCVVersionResponse:
        return {
            "id": "00000000-0000-0000-0000-000000000001",
            "jd_text": "Backend Engineer",
            "tailored_cv": minimal_data(TailoredCV),
            "selected_design": "classic_ats",
            "created_at": "2026-07-11T00:00:00Z",
            "updated_at": "2026-07-11T00:00:00Z",
        }

    if model is TailoredCVVersionListResponse:
        return {"versions": [minimal_data(TailoredCVVersionResponse)]}

    if model is InterviewTurnResponse:
        return {
            "ai_feedback": "Good answer.",
            "next_question": "Tell me more.",
            "hint_for_user": "Add metrics.",
            "metrics": {
                "confidence_score": 60,
                "confidence_feedback": "Okay.",
                "jd_relevance_score": 50,
                "jd_relevance_feedback": "Low.",
                "tech_vocab_rating": "KHÁ",
            },
        }

    if model is FinalInterviewReport:
        return {
            "overall_score": 75,
            "overall_feedback": "Solid performance.",
            "sub_scores": [{"category": "Technical", "score": 80, "label": "Tốt"}],
            "key_strengths": ["Clear communication"],
            "areas_for_improvement": ["Add more metrics"],
            "top_topics_covered": ["System design"],
            "ai_feedback_summary": {
                "positive": "Good.",
                "warning": "Practice more.",
                "actionable": "Study system design.",
            },
            "turn_by_turn_analysis": [
                {
                    "question": "Q1",
                    "user_answer": "A1",
                    "feedback": "Okay.",
                    "ideal_answer_snippet": "Ideal A1.",
                }
            ],
        }

    if model is CVAnalysisLLMResponse:
        return {
            "match_headline": "Strong fit",
            "match_summary": "Relevant profile.",
            "technical_match": 80,
            "experience_relevance": 70,
            "keyword_coverage": 60,
            "impact_evidence": 50,
            "tone_quality": 90,
            "ats_readiness": 80,
            "missing_keywords": ["Kubernetes"],
            "suggested_edits": [
                {
                    "section": "Experience",
                    "original_text": "Did backend.",
                    "improved_safe": "Built backend services.",
                    "improved_with_placeholders": "Built [N] services.",
                    "metric_questions": ["How many?"],
                    "unsupported_assumptions": [],
                    "rewrite_risk": "safe",
                    "reason": "Stronger.",
                },
                {
                    "section": "Skills",
                    "original_text": "Python.",
                    "improved_safe": "Python development.",
                    "improved_with_placeholders": "Python for [use case].",
                    "metric_questions": ["What use case?"],
                    "unsupported_assumptions": [],
                    "rewrite_risk": "safe",
                    "reason": "More specific.",
                },
            ],
            "cv_strengths": ["Clear structure", "Relevant experience"],
            "prioritized_keywords": [{"keyword": "Python", "priority": "High"}],
            "evidence_analysis": [
                {
                    "claim": "Backend work",
                    "evidence_strength": "Medium",
                    "comment": "No metrics.",
                }
            ],
            "tailored_cv": {
                "name": "Duy",
                "headline": "Backend Developer",
                "contact_lines": ["duy@example.com"],
                "summary": "Backend developer.",
                "sections": [{"title": "Experience", "items": ["Built APIs."]}],
            },
        }

    if model is CVAnalysisResponse:
        data = minimal_data(CVAnalysisLLMResponse)
        data.update(
            {
                "role_fit_score": 72,
                "match_score": 62,
                "score_breakdown": scorebreak_data(),
            }
        )
        return data

    if model is WriterResponse:
        return {
            "subject_line": "Application for Backend Role",
            "content": "I am interested in the role.",
            "tips": ["Add your GitHub link."],
        }

    if model is CandidateProfileResponse:
        return {
            "target_roles": ["Backend Developer"],
            "skills": ["Python"],
            "seniority": "junior",
            "location": "Hồ Chí Minh",
            "years_of_experience": 1.0,
            "queries": ["Backend developer Hồ Chí Minh"],
        }

    if model is ScoreBreakdown:
        return scorebreak_data()

    if model is JobSourceStatus:
        return {"source": "itviec", "status": "success", "count": 5}

    if model is JobResult:
        return {
            "id": "job-1",
            "source": "itviec",
            "title": "Backend Dev",
            "company": "Acme",
            "location": "HCMC",
            "salary": "$1000-2000",
            "level": "junior",
            "skills": ["Python"],
            "url": "https://itviec.com/job-1",
        }

    if model is RankedJobResult:
        data = minimal_data(JobResult)
        data.update(
            {
                "match_score": 85,
                "match_label": "good_match",
                "match_reasons": ["Python"],
                "missing_skills": [],
            }
        )
        return data

    if model is Message:
        return {"role": "user", "content": "Hello"}

    # Request models — return empty or default values
    if model is AnalyzeCVRequest:
        return {"cv_text": "Test CV"}

    if model is InterviewChatRequest:
        return {
            "cv_text": "Test",
            "chat_history": [],
            "current_question": 1,
            "total_questions": 5,
        }

    if model is InterviewFinishRequest:
        return {"cv_text": "Test", "chat_history": [], "interview_type": "general"}

    if model is TTSRequest:
        return {"text": "Hello"}

    if model is WriterRequest:
        return {"cv_text": "Test", "writing_type": "email", "tone": "Chuyên nghiệp"}

    if model is ParseProfileRequest:
        return {"cv_text": "Test CV"}

    if model is JobSearchRequest:
        return {"cv_text": "Test CV"}

    raise ValueError(f"No minimal data fixture for {model.__name__}")


def scorebreak_data() -> dict[str, Any]:
    """Shared ScoreBreakdown data."""
    return {
        "weights": {
            "technical": 0.25,
            "experience": 0.2,
            "keywords": 0.15,
            "evidence": 0.15,
            "tone": 0.1,
            "ats": 0.15,
        },
        "raw_score": 72,
        "critical_missing_count": 0,
        "high_missing_count": 1,
        "weighted_missing_requirement_score": 8,
        "unsupported_claim_count": 0,
        "critical_missing_penalty": 0,
        "high_missing_penalty": 8,
        "missing_requirement_penalty": 0,
        "unsupported_claim_penalty": 0,
        "total_penalty": 8,
        "final_score": 64,
    }


# --- Tests ---


@pytest.mark.parametrize("model", ALL_MODELS, ids=lambda m: m.__name__)
def test_model_serializes_to_json(model: type[BaseModel]) -> None:
    """Every API model should round-trip through JSON without error."""
    instance = model(**minimal_data(model))
    json_str = instance.model_dump_json()
    assert json_str  # not empty
    parsed = json.loads(json_str)
    assert isinstance(parsed, dict)


@pytest.mark.parametrize("model", ALL_MODELS, ids=lambda m: m.__name__)
def test_model_dump_is_dict(model: type[BaseModel]) -> None:
    """model_dump() should return a plain dict, not raise."""
    instance = model(**minimal_data(model))
    dumped = instance.model_dump()
    assert isinstance(dumped, dict)


def test_all_models_are_listed() -> None:
    """Guards against forgetting to add a new model to ALL_MODELS."""
    # If this fails, append the new model to the ALL_MODELS list above.
    names = {m.__name__ for m in ALL_MODELS}
    expected = {
        "Message",
        "LiveMetrics",
        "TurnAnalysis",
        "SubScore",
        "AIFeedbackSummary",
        "SuggestedEdit",
        "PrioritizedKeyword",
        "EvidenceAnalysis",
        "ExperienceItem",
        "TailoredCV",
        "TailoredCVSection",
        "AnalyzeCVRequest",
        "InterviewChatRequest",
        "InterviewFinishRequest",
        "TTSRequest",
        "WriterRequest",
        "ParseProfileRequest",
        "JobSearchRequest",
        "CVAnalysisLLMResponse",
        "CVAnalysisResponse",
        "InterviewTurnResponse",
        "FinalInterviewReport",
        "WriterResponse",
        "CandidateProfileResponse",
        "ScoreBreakdown",
        "JobSourceStatus",
        "JobResult",
        "RankedJobResult",
        "TailoredCVVersionCreate",
        "TailoredCVVersionUpdate",
        "TailoredCVVersionResponse",
        "TailoredCVVersionListResponse",
    }
    assert names == expected, f"Missing: {expected - names}. Extra: {names - expected}"
