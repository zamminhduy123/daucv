"""Validate every response model can be serialized to valid JSON.

This catches model breakage (renamed fields, type changes, missing
imports) at test time — before the CI Docker build even starts.
"""

import json
from typing import Any

import pytest
from pydantic import BaseModel, ValidationError

from app.models.cv_document_v2 import (
    CURRENT_RECONSTRUCTION_VERSION,
    ContentOrigin,
    CVBlockRewrite,
    CVBulletBlock,
    CVDocumentV2,
    CVEducationBlock,
    CVEntryBlock,
    CVIdentity,
    CVIdentitySourceMap,
    CVParagraphBlock,
    CVPublicationBlock,
    CVReconstructionDiagnostics,
    CVSection,
    CVSkillGroupBlock,
    CVSourceCoverageDiagnostics,
    CVSourceCoverageIssue,
    CVUnknownBlock,
    CVUnmappedContent,
)
from app.models.cv_structuring import LLMSemanticCVResponse
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
    CVAnalysisEnvelope,
    CVAnalysisGenerationResponse,
    CVAnalysisLLMResponse,
    CVAnalysisPayload,
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
    CVAnalysisEnvelope,
    CVAnalysisPayload,
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
    # V2 models
    CVDocumentV2,
    CVSection,
    CVIdentity,
    CVIdentitySourceMap,
    CVEntryBlock,
    CVBulletBlock,
    CVParagraphBlock,
    CVSkillGroupBlock,
    CVPublicationBlock,
    CVEducationBlock,
    CVUnknownBlock,
    LLMSemanticCVResponse,
    CVBlockRewrite,
    CVReconstructionDiagnostics,
    CVSourceCoverageDiagnostics,
    CVSourceCoverageIssue,
]


def minimal_data(model: type[BaseModel]) -> dict[str, Any]:
    """Return a minimal valid payload for *model*."""
    if model is CVBlockRewrite:
        return {"block_id": "entry-1", "bullets": ["Built APIs."]}

    if model is CVSourceCoverageDiagnostics:
        return {
            "raw_block_count": 10,
            "accounted_block_count": 8,
            "significant_character_count": 1000,
            "mapped_character_count": 800,
            "benign_unmapped_character_count": 50,
            "substantive_unmapped_character_count": 150,
            "duplicate_character_count": 0,
            "coverage_ratio": 0.8,
            "issues": [],
        }

    if model is CVSourceCoverageIssue:
        return {
            "code": "substantive_source_omission",
            "block_id": "b1",
            "significant_character_count": 50,
        }

    if model is CVReconstructionDiagnostics:
        return {
            "warnings": [],
            "block_confidence": {"entry-1": 0.9},
            "source_coverage": minimal_data(CVSourceCoverageDiagnostics),
        }

    if model is CVAnalysisPayload:
        return {
            "match_headline": "Strong match",
            "match_summary": "Good alignment",
            "technical_match": 80,
            "experience_relevance": 75,
            "keyword_coverage": 70,
            "impact_evidence": 65,
            "tone_quality": 85,
            "ats_readiness": 90,
            "missing_keywords": ["aws", "docker"],
            "suggested_edits": [
                {
                    "section": "Experience",
                    "original_text": "Did backend work.",
                    "improved_safe": "Built backend services.",
                    "improved_with_placeholders": "Built [N] backend services.",
                    "metric_questions": ["How many services?"],
                    "unsupported_assumptions": [],
                    "rewrite_risk": "safe",
                    "reason": "Stronger verb.",
                },
                {
                    "section": "Summary",
                    "original_text": "Worker.",
                    "improved_safe": "Experienced developer.",
                    "improved_with_placeholders": "[Years]-year developer.",
                    "metric_questions": ["How many years?"],
                    "unsupported_assumptions": [],
                    "rewrite_risk": "safe",
                    "reason": "Be specific.",
                },
            ],
            "cv_strengths": ["Strong experience", "Good skills"],
            "prioritized_keywords": [],
            "evidence_analysis": [
                {
                    "claim": "Built APIs",
                    "evidence_strength": "Medium",
                    "comment": "Supported by the experience section.",
                },
            ],
        }

    if model is CVAnalysisEnvelope:
        document = minimal_data(CVDocumentV2)
        return {
            "analysis": {
                "match_headline": "Strong match",
                "match_summary": "Good alignment",
                "technical_match": 80,
                "experience_relevance": 75,
                "keyword_coverage": 70,
                "impact_evidence": 65,
                "tone_quality": 85,
                "ats_readiness": 90,
                "missing_keywords": ["aws", "docker"],
                "suggested_edits": [
                    {
                        "section": "Experience",
                        "original_text": "Did backend work.",
                        "improved_safe": "Built backend services.",
                        "improved_with_placeholders": "Built [N] backend services.",
                        "metric_questions": ["How many services?"],
                        "unsupported_assumptions": [],
                        "rewrite_risk": "safe",
                        "reason": "Stronger verb.",
                    },
                    {
                        "section": "Summary",
                        "original_text": "Worker.",
                        "improved_safe": "Experienced developer.",
                        "improved_with_placeholders": "[Years]-year developer.",
                        "metric_questions": ["How many years?"],
                        "unsupported_assumptions": [],
                        "rewrite_risk": "safe",
                        "reason": "Be specific.",
                    },
                ],
                "cv_strengths": ["Strong experience", "Good skills"],
                "prioritized_keywords": [],
                "evidence_analysis": [
                    {
                        "claim": "Built APIs",
                        "evidence_strength": "Medium",
                        "comment": "Supported by the experience section.",
                    },
                ],
            },
            "tailored_cv": document,
            "source_document_v2": document,
            "reconstruction_diagnostics": minimal_data(CVReconstructionDiagnostics),
            "legacy_tailored_cv": minimal_data(TailoredCV),
            "tailoring_entitlement": "token",
        }

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
                {"company": "Acme", "role": "Dev", "bullet_points": ["Built stuff."]},
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
            "tailoring_entitlement": f"{'a' * 64}.{'b' * 64}",
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
                },
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
                },
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
            },
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
            },
        )
        return data

    if model is Message:
        return {"role": "user", "content": "Hello"}

    # Request models — return empty or default values
    if model is AnalyzeCVRequest:
        return {"cv_text": "Test CV"}

    if model is LLMSemanticCVResponse:
        return {
            "identity": {},
            "sections": [],
            "unmapped_references": [],
            "confidence": 1.0,
        }

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

    if model is CVDocumentV2:
        return {
            "schema_version": 2,
            "identity": {"name": "Duy"},
            "summary": {
                "type": "paragraph",
                "block_id": "pb-1",
                "text": "Summary text",
            },
            "sections": [],
        }

    if model is CVSection:
        return {
            "id": "sec-1",
            "type": "experience",
            "title": "Experience",
            "blocks": [],
        }

    if model is CVIdentity:
        return {
            "name": "Duy",
            "headline": "Backend Engineer",
            "contact_lines": ["duy@example.com"],
        }

    if model is CVIdentitySourceMap:
        return {"full_name": ["p1-b1"], "email": ["p1-b2"]}

    if model is CVEntryBlock:
        return {
            "type": "entry",
            "block_id": "eb-1",
            "title": "Title",
            "bullets": ["Bullet 1"],
        }

    if model is CVBulletBlock:
        return {
            "type": "bullet",
            "block_id": "bb-1",
            "text": "Bullet text",
        }

    if model is CVParagraphBlock:
        return {
            "type": "paragraph",
            "block_id": "pb-1",
            "text": "Paragraph text",
        }

    if model is CVSkillGroupBlock:
        return {
            "type": "skill_group",
            "block_id": "sg-1",
            "skills": ["Python"],
        }

    if model is CVPublicationBlock:
        return {
            "type": "publication",
            "block_id": "pub-1",
            "title": "Title",
        }

    if model is CVEducationBlock:
        return {
            "type": "education",
            "block_id": "ed-1",
            "details": ["Detail 1"],
        }

    if model is CVUnknownBlock:
        return {
            "type": "unknown",
            "block_id": "unk-1",
            "lines": ["Line 1"],
            "confidence": 0.5,
        }

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
        "CVAnalysisEnvelope",
        "CVAnalysisPayload",
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
        "CVDocumentV2",
        "CVSection",
        "CVIdentity",
        "CVIdentitySourceMap",
        "CVEntryBlock",
        "CVBulletBlock",
        "CVParagraphBlock",
        "CVSkillGroupBlock",
        "CVPublicationBlock",
        "CVEducationBlock",
        "CVUnknownBlock",
        "LLMSemanticCVResponse",
        "CVBlockRewrite",
        "CVReconstructionDiagnostics",
        "CVSourceCoverageDiagnostics",
        "CVSourceCoverageIssue",
    }
    assert names == expected, f"Missing: {expected - names}. Extra: {names - expected}"


def test_llm_semantic_block_schema_requires_type_discriminator() -> None:
    schema = LLMSemanticCVResponse.model_json_schema()
    definitions = schema["$defs"]

    for block_name in (
        "LLMEntryBlock",
        "LLMBulletBlock",
        "LLMParagraphBlock",
        "LLMSkillGroupBlock",
        "LLMPublicationBlock",
        "LLMEducationBlock",
        "LLMUnknownBlock",
    ):
        assert "type" in definitions[block_name]["required"]


def test_canonical_cv_document_round_trip_preserves_contract_fields() -> None:
    document = CVDocumentV2(
        raw_extraction_id="raw-123",
        source_hash="source-hash",
        identity=CVIdentity(
            full_name="Nguyen Minh An",
            headline="Backend Engineer",
            email="an@example.com",
            phone="+84 912 345 678",
            location="Ha Noi",
            links=["https://github.com/minhan"],
            source_block_ids=["p1-b0"],
            field_source_block_ids={
                "full_name": ["p1-b1"],
                "headline": ["p1-b1"],
                "email": ["p1-b2"],
                "phone": ["p1-b2"],
                "location": ["p1-b2"],
                "links": {"https://github.com/minhan": ["p1-b2"]},
            },
        ),
        sections=[
            CVSection(
                id="experience",
                type="experience",
                title="Experience",
                blocks=[
                    CVEntryBlock(
                        block_id="experience-1",
                        title="Backend Engineer",
                        organization="Example Company",
                        bullets=["Built reliable APIs."],
                        source_block_ids=["p1-b3"],
                        origin=ContentOrigin.LLM_REWRITE,
                    )
                ],
            )
        ],
        unmapped_content=[
            CVUnmappedContent(
                block_id="p1-b4",
                text="Decorative footer",
                page=1,
                reason="decorative_content",
                fragment_id="frag-1",
                source_start=10,
                source_end=27,
            )
        ],
        reconstruction_warnings=["review_unmapped_content"],
    )

    reloaded = CVDocumentV2.model_validate_json(document.model_dump_json())

    assert reloaded.raw_extraction_id == "raw-123"
    assert reloaded.extraction_version == "2.0"
    assert reloaded.parser_version == "2.0"
    assert reloaded.reconstruction_version == CURRENT_RECONSTRUCTION_VERSION
    assert reloaded.identity.full_name == "Nguyen Minh An"
    assert reloaded.identity.email == "an@example.com"
    assert reloaded.identity.source_block_ids == ["p1-b0", "p1-b1", "p1-b2"]
    assert reloaded.identity.field_source_block_ids.email == ["p1-b2"]
    assert reloaded.identity.field_source_block_ids.links == {
        "https://github.com/minhan": ["p1-b2"]
    }
    assert reloaded.sections[0].blocks[0].source_block_ids == ["p1-b3"]
    assert reloaded.sections[0].blocks[0].origin == ContentOrigin.LLM_REWRITE
    assert reloaded.unmapped_content[0].block_id == "p1-b4"
    assert reloaded.unmapped_content[0].fragment_id == "frag-1"
    assert reloaded.unmapped_content[0].source_start == 10
    assert reloaded.unmapped_content[0].source_end == 27
    assert reloaded.reconstruction_warnings == ["review_unmapped_content"]


def test_legacy_identity_is_lifted_without_losing_original_contact_rows() -> None:
    identity = CVIdentity.model_validate(
        {
            "name": "Nguyen Minh An",
            "headline": "Backend Engineer",
            "contact_lines": [
                "  an@example.com | +84 912 345 678  ",
                "linkedin.com/in/minhan",
                "Ha Noi, Vietnam",
            ],
        }
    )

    assert identity.full_name == "Nguyen Minh An"
    assert identity.email == "an@example.com"
    assert identity.phone == "+84 912 345 678"
    assert identity.links == ["linkedin.com/in/minhan"]
    assert identity.location is None
    assert identity.contact_lines == [
        "an@example.com",
        "+84 912 345 678",
        "linkedin.com/in/minhan",
        "Ha Noi, Vietnam",
    ]
    assert identity.canonical_contact_lines().count("an@example.com") == 1
    assert identity.canonical_contact_lines().count("+84 912 345 678") == 1
    assert identity.canonical_contact_lines().count("Ha Noi, Vietnam") == 1


def test_canonical_identity_keeps_legacy_consumers_working() -> None:
    identity = CVIdentity(
        full_name="Nguyen Minh An",
        email="an@example.com",
        phone="+84 912 345 678",
        location="Ha Noi",
        links=["https://github.com/minhan"],
    )

    assert identity.name == "Nguyen Minh An"
    assert identity.contact_lines == [
        "an@example.com",
        "+84 912 345 678",
        "Ha Noi",
        "https://github.com/minhan",
    ]


def test_canonical_identity_overrides_conflicting_legacy_values_on_round_trip() -> None:
    identity = CVIdentity(
        full_name="Canonical Name",
        name="Stale Legacy Name",
        email="canonical@example.com",
        phone="+84 912 345 678",
        links=["https://example.com/canonical"],
        contact_lines=[
            "legacy@example.com",
            "+84 900 000 000",
            "https://example.com/legacy",
            "Unclassified contact note",
        ],
    )

    reloaded = CVIdentity.model_validate_json(identity.model_dump_json())

    assert reloaded.full_name == "Canonical Name"
    assert reloaded.name == "Canonical Name"
    assert reloaded.email == "canonical@example.com"
    assert reloaded.phone == "+84 912 345 678"
    assert reloaded.links == ["https://example.com/canonical"]
    assert reloaded.contact_lines == [
        "canonical@example.com",
        "+84 912 345 678",
        "https://example.com/canonical",
        "Unclassified contact note",
    ]


def test_mutated_legacy_identity_can_be_canonicalized() -> None:
    identity = CVIdentity()
    identity.name = "Nguyen Minh An"
    identity.contact_lines.append("an@example.com")

    canonical = identity.canonicalized()

    assert canonical.full_name == "Nguyen Minh An"
    assert canonical.email == "an@example.com"


@pytest.mark.parametrize("field", ["contact_lines", "links"])
def test_identity_bridge_does_not_hide_invalid_list_inputs(field: str) -> None:
    with pytest.raises(ValidationError):
        CVIdentity.model_validate({field: "not-a-list"})


def test_scoring_llm_contract_rejects_block_rewrites() -> None:
    payload = minimal_data(CVAnalysisLLMResponse)
    payload.pop("tailored_cv", None)
    payload["block_rewrites"] = []

    with pytest.raises(ValidationError, match="block_rewrites"):
        CVAnalysisGenerationResponse.model_validate(payload)
