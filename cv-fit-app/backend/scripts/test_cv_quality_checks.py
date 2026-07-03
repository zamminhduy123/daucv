import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest
from pydantic import ValidationError

from app.models.domain import EvidenceAnalysis, PrioritizedKeyword, SuggestedEdit
from app.models.responses import CVAnalysisLLMResponse, CVAnalysisResponse
from app.services.cv_quality_checks import (
    EvalResult,
    build_scored_analysis,
    classify_keyword_grounding,
    classify_rewrite_grounding,
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
    # Aggressive penalties: High=8, unsupported_claim=2, total=10
    assert response.score_breakdown.weighted_missing_requirement_score == 8
    assert response.score_breakdown.critical_missing_penalty == 0
    assert response.score_breakdown.high_missing_penalty == 8
    assert response.score_breakdown.missing_requirement_penalty == 8
    assert response.score_breakdown.unsupported_claim_penalty == 2
    assert response.score_breakdown.total_penalty == 10
    # role_fit_score = raw_score (no penalty)
    assert response.role_fit_score == 72
    # CV Match = raw_score - aggressive_penalty
    assert response.match_score == 62
    assert response.score_breakdown.final_score == 62
    assert response.match_headline == "Có tiềm năng, nhưng CV cần tối ưu thêm theo JD."


def test_llm_schema_does_not_include_or_accept_match_score():
    schema = CVAnalysisLLMResponse.model_json_schema()

    assert "match_score" not in schema["properties"]

    payload = _analysis_response().model_dump()
    payload["match_score"] = 99

    with pytest.raises(ValidationError):
        CVAnalysisLLMResponse(**payload)


def test_api_schema_includes_backend_score_fields():
    schema = CVAnalysisResponse.model_json_schema()

    assert "role_fit_score" in schema["properties"]
    assert "match_score" in schema["properties"]
    assert "score_breakdown" in schema["properties"]
    assert "role_fit_score" in schema["required"]
    assert "match_score" in schema["required"]
    assert "score_breakdown" in schema["required"]


def test_llm_schema_trims_oversized_keyword_lists():
    payload = _analysis_response().model_dump()
    payload["missing_keywords"] = [f"keyword-{index}" for index in range(12)]
    payload["prioritized_keywords"] = [
        {"keyword": f"keyword-{index}", "priority": "Low"}
        for index in range(9)
    ]

    response = CVAnalysisLLMResponse(**payload)

    assert len(response.missing_keywords) == 6
    assert response.missing_keywords == [f"keyword-{index}" for index in range(6)]
    assert len(response.prioritized_keywords) == 6
    assert [item.keyword for item in response.prioritized_keywords] == [
        f"keyword-{index}" for index in range(6)
    ]


def test_llm_schema_accepts_short_evidence_analysis():
    payload = _analysis_response().model_dump()
    payload["evidence_analysis"] = [
        {
            "claim": "Relevant backend work",
            "evidence_strength": "Medium",
            "comment": "Some backend evidence is visible.",
        },
        {
            "claim": "Role alignment",
            "evidence_strength": "Weak",
            "comment": "Needs stronger JD-specific evidence.",
        },
    ]

    response = CVAnalysisLLMResponse(**payload)

    assert len(response.evidence_analysis) == 2


def test_llm_schema_pads_missing_minimum_lists_with_safe_fallbacks():
    payload = _analysis_response().model_dump()
    payload["suggested_edits"] = []
    payload["cv_strengths"] = []
    payload["evidence_analysis"] = []

    response = CVAnalysisLLMResponse(**payload)

    assert len(response.suggested_edits) == 2
    assert len(response.cv_strengths) == 2
    assert len(response.evidence_analysis) == 1
    assert response.suggested_edits[0].rewrite_risk == "needs_user_input"


def test_metric_placeholders_do_not_count_as_fabricated_safe_metrics():
    response = _analysis_response()

    assert detect_unsupported_metrics(response, "Worked on backend services.") == []
    assert response.suggested_edits[0].upgraded_text == response.suggested_edits[0].improved_safe


def test_keyword_grounding_allows_soft_inference_and_adjacent_recommendations():
    response = _analysis_response(
        missing_keywords=["Backend scalability", "RAG evaluation", "Quantum ledger"],
        prioritized_keywords=[
            PrioritizedKeyword(keyword="Backend scalability", priority="High"),
            PrioritizedKeyword(keyword="RAG evaluation", priority="Low"),
            PrioritizedKeyword(keyword="Quantum ledger", priority="Critical"),
        ],
    )

    result = classify_keyword_grounding(
        response,
        jd_text="Build backend APIs and scalable system architecture for LLM application quality.",
    )

    assert any("Backend scalability" in item for item in result["soft_inferences"])
    assert any("RAG evaluation" in item for item in result["useful_adjacent_recommendations"])
    assert any("Quantum ledger" in item for item in result["hard_hallucinations"])


def test_rewrite_grounding_separates_placeholders_from_unsupported_facts():
    response = _analysis_response(
        suggested_edits=[
            SuggestedEdit(
                section="Experience",
                original_text="Optimized backend services.",
                improved_safe="Optimized backend services, reducing latency by 35%.",
                improved_with_placeholders="Optimized backend services, reducing latency by [X%].",
                metric_questions=["What was the measured latency reduction?"],
                unsupported_assumptions=["Exact latency reduction"],
                rewrite_risk="needs_user_input",
                reason="Needs a real metric before using the quantified version.",
            ),
            SuggestedEdit(
                section="Skills",
                original_text="Python, APIs, databases.",
                improved_safe="Python, API development, database-backed services.",
                improved_with_placeholders="Python, API development for [workflow].",
                metric_questions=["Which workflow did this support?"],
                unsupported_assumptions=[],
                rewrite_risk="safe",
                reason="Makes the skill list more specific.",
            ),
        ]
    )

    result = classify_rewrite_grounding(response, cv_text="Optimized backend services.")

    assert any("35" in item for item in result["unsupported_factual_claims"])
    assert any("[X%]" in item for item in result["placeholder_metrics"])
    assert any("Exact latency reduction" in item for item in result["needs_user_confirmation"])


def test_run_deterministic_eval_returns_scored_response():
    result = run_deterministic_eval(
        _analysis_response(),
        cv_text="Worked on backend services.",
        jd_text="We need Kubernetes and API development.",
    )

    assert isinstance(result, EvalResult)
    assert result.schema_valid is True
    assert isinstance(result.warnings, list)
    assert isinstance(result.scored_response, CVAnalysisResponse)
    assert result.scored_response.role_fit_score == 72
    assert result.scored_response.match_score == 62
    assert result.placeholder_metrics
