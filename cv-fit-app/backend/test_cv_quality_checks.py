import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import pytest
from pydantic import ValidationError

from app.models.domain import EvidenceAnalysis, PrioritizedKeyword, SuggestedEdit
from app.models.responses import CVAnalysisLLMResponse, CVAnalysisResponse
from app.services.cv_quality_checks import (
    build_scored_analysis,
    detect_unsupported_metrics,
    run_deterministic_eval,
)


def _analysis_response(**overrides):
    data = {
        "match_headline": "Strong fit",
        "match_summary": "Relevant profile with some gaps.",
        "technical_match": 80,
        "experience_relevance": 70,
        "keyword_coverage": 60,
        "impact_evidence": 50,
        "tone_quality": 90,
        "ats_readiness": 80,
        "missing_keywords": ["Kubernetes"],
        "suggested_edits": [
            SuggestedEdit(
                section="Experience",
                original_text="Worked on backend services.",
                improved_safe=(
                    "Optimized backend services to improve response time and "
                    "reliability for user-facing workflows."
                ),
                improved_with_placeholders=(
                    "Optimized backend services, reducing API latency from "
                    "[X ms] to [Y ms] for [workflow/users]."
                ),
                metric_questions=[
                    "What was the before/after latency?",
                    "Which workflow or user group was affected?",
                ],
                unsupported_assumptions=["Exact latency reduction"],
                rewrite_risk="needs_user_input",
                reason="Adds action and impact without inventing metrics.",
            ),
            SuggestedEdit(
                section="Skills",
                original_text="Python, APIs, databases.",
                improved_safe="Python, API development, database-backed services.",
                improved_with_placeholders=(
                    "Python, API development handling [N requests/day], "
                    "database-backed services for [workflow]."
                ),
                metric_questions=["What request volume did the APIs handle?"],
                unsupported_assumptions=[],
                rewrite_risk="safe",
                reason="Makes the skill list more specific.",
            )
        ],
        "cv_strengths": ["Clear backend experience", "Readable structure"],
        "prioritized_keywords": [
            PrioritizedKeyword(keyword="Kubernetes", priority="High")
        ],
        "evidence_analysis": [
            EvidenceAnalysis(
                claim="Backend optimization",
                evidence_strength="Medium",
                comment="Mentioned without metrics.",
            ),
            EvidenceAnalysis(
                claim="Kubernetes operations",
                evidence_strength="Missing",
                comment="Not found in CV.",
            ),
            EvidenceAnalysis(
                claim="API development",
                evidence_strength="Strong",
                comment="Supported by backend project details.",
            ),
        ],
    }
    data.update(overrides)
    return CVAnalysisLLMResponse(**data)


def test_build_scored_analysis_uses_weighted_subscores_and_penalties():
    response = build_scored_analysis(_analysis_response())

    assert isinstance(response, CVAnalysisResponse)
    assert response.score_breakdown is not None
    assert response.score_breakdown.raw_score == 72
    assert response.score_breakdown.critical_missing_penalty == 8
    assert response.score_breakdown.high_missing_penalty == 4
    assert response.score_breakdown.unsupported_claim_penalty == 2
    assert response.match_score == 58
    assert response.score_breakdown.final_score == 58


def test_llm_schema_does_not_include_or_accept_match_score():
    schema = CVAnalysisLLMResponse.model_json_schema()

    assert "match_score" not in schema["properties"]

    payload = _analysis_response().model_dump()
    payload["match_score"] = 99

    with pytest.raises(ValidationError):
        CVAnalysisLLMResponse(**payload)


def test_api_schema_includes_backend_score_fields():
    schema = CVAnalysisResponse.model_json_schema()

    assert "match_score" in schema["properties"]
    assert "score_breakdown" in schema["properties"]
    assert "match_score" in schema["required"]
    assert "score_breakdown" in schema["required"]


def test_metric_placeholders_do_not_count_as_fabricated_safe_metrics():
    response = _analysis_response()

    assert detect_unsupported_metrics(response, "Worked on backend services.") == []
    assert response.suggested_edits[0].upgraded_text == response.suggested_edits[0].improved_safe


def test_run_deterministic_eval_returns_scored_response():
    result = run_deterministic_eval(
        _analysis_response(),
        cv_text="Worked on backend services.",
        jd_text="We need Kubernetes and API development.",
    )

    assert result["schema_valid"] is True
    assert isinstance(result["warnings"], list)
    assert isinstance(result["scored_response"], CVAnalysisResponse)
    assert result["scored_response"].match_score == 58
