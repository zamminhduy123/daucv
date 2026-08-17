"""Unit tests for LLM #2 — CV Fit Evaluator & Judge."""

from unittest.mock import AsyncMock, patch

import pytest

from app.models.cv_evaluation import (
    CategoryScores,
    LLMEvaluationReport,
    SkillRequirementMatch,
)
from app.prompts.system_prompts import build_cv_evaluator_prompt
from app.services.cv_evaluator_service import evaluate_cv_fit


def test_cv_evaluator_prompt_structure():
    """Verify system prompt for LLM #2 contains evaluation guidelines and scoring brackets."""
    prompt = build_cv_evaluator_prompt()
    assert "LLM #2" in prompt
    assert "overall_fit_score" in prompt
    assert "STRONG_FIT" in prompt
    assert "MODERATE_FIT" in prompt
    assert "WEAK_FIT" in prompt
    assert "skill_matrix" in prompt


def test_llm_evaluation_report_schema_validation():
    """Test creating and validating an LLMEvaluationReport instance."""
    report = LLMEvaluationReport(
        overall_fit_score=92,
        match_grade="STRONG_FIT",
        executive_summary="Candidate is a strong Senior AI Engineer with extensive PyTorch and LLM experience.",
        category_scores=CategoryScores(
            technical_skills=95,
            experience_level=90,
            domain_fit=90,
            education_fit=90,
        ),
        key_strengths=[
            "Proven PyTorch and LLM experience",
            "M.S. degree in AI / Engineering",
        ],
        critical_gaps=[
            "Limited explicit AWS cloud deployment experience",
        ],
        skill_matrix=[
            SkillRequirementMatch(
                requirement="PyTorch & Deep Learning",
                status="matched",
                cv_evidence="2 years graduate research in PyTorch & GNNs",
            ),
            SkillRequirementMatch(
                requirement="AWS Cloud / Kubernetes",
                status="partial",
                gap_explanation="CV highlights Docker/FastAPI, but lacks explicit AWS/k8s experience.",
            ),
        ],
        actionable_recommendations=[
            "Highlight Docker & cloud API deployment details in the experience section.",
        ],
    )

    assert report.overall_fit_score == 92
    assert report.match_grade == "STRONG_FIT"
    assert len(report.key_strengths) == 2
    assert report.skill_matrix[0].status == "matched"


@pytest.mark.asyncio
async def test_evaluate_cv_fit_service_call():
    """Test calling evaluate_cv_fit service with mocked LLM fallback router."""
    mock_report = LLMEvaluationReport(
        overall_fit_score=88,
        match_grade="STRONG_FIT",
        executive_summary="Excellent fit for AI Engineer role.",
        category_scores=CategoryScores(
            technical_skills=90,
            experience_level=85,
            domain_fit=90,
            education_fit=85,
        ),
        key_strengths=["Strong PyTorch research background"],
        critical_gaps=["No Kubernetes experience listed"],
        skill_matrix=[
            SkillRequirementMatch(
                requirement="PyTorch",
                status="matched",
                cv_evidence="Published PyTorch research papers",
            )
        ],
        actionable_recommendations=["Emphasize model deployment experience"],
    )

    sample_cv = {
        "identity": {"name": "Nguyen Thanh Minh Duy", "headline": "AI Engineer"},
        "summary": "AI researcher and engineer.",
        "skills": {"AI Engineering": ["PyTorch", "FastAPI"]},
    }
    sample_jd = "Looking for Senior AI Engineer with PyTorch, FastAPI, and model optimization experience."

    with patch(
        "app.services.cv_evaluator_service.call_llm_with_fallback",
        new_callable=AsyncMock,
    ) as mock_llm_call:
        mock_llm_call.return_value = mock_report

        eval_result = await evaluate_cv_fit(sample_cv, sample_jd)

        assert eval_result.report.overall_fit_score == 88
        assert eval_result.report.match_grade == "STRONG_FIT"
        assert "Nguyen Thanh Minh Duy" in eval_result.raw_prompt
        assert "Looking for Senior AI Engineer" in eval_result.raw_prompt


@pytest.mark.asyncio
async def test_evaluate_cv_fit_enforces_general_audit_without_jd():
    """A provider omission must not turn an audit into a fictitious job fit."""
    provider_report = LLMEvaluationReport(overall_fit_score=88)

    with patch(
        "app.services.cv_evaluator_service.call_llm_with_fallback",
        new_callable=AsyncMock,
    ) as mock_llm_call:
        mock_llm_call.return_value = provider_report
        eval_result = await evaluate_cv_fit({"identity": {"name": "Lan Nguyen"}})

    assert eval_result.report.evaluation_mode == "GENERAL_AUDIT"
    assert eval_result.report.match_grade == "EXCELLENT"
    assert eval_result.report.executive_summary.startswith("General CV Audit")
