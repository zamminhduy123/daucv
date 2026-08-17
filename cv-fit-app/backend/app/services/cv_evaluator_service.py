"""Service module for LLM #2 — CV Fit Evaluator & Judge."""

import json
import logging
from typing import Any

from pydantic import BaseModel

from app.core.config import CV_EVALUATION_MAX_OUTPUT_TOKENS
from app.models.cv_evaluation import LLMEvaluationReport
from app.prompts.system_prompts import build_cv_evaluator_prompt
from app.services.ai_service import call_llm_with_fallback

logger = logging.getLogger(__name__)


class EvaluationResult(BaseModel):
    """Result container for LLM #2 evaluation execution."""

    report: LLMEvaluationReport
    raw_prompt: str | None = None
    provider_used: str | None = None


def _enforce_evaluation_mode(
    report: LLMEvaluationReport,
    *,
    expected_mode: str,
) -> LLMEvaluationReport:
    """Make the server-owned mode agree with the presence of a target JD."""
    if report.evaluation_mode == expected_mode:
        return report

    logger.warning(
        "LLM #2 returned evaluation_mode=%s; enforcing server mode=%s",
        report.evaluation_mode,
        expected_mode,
    )
    payload = report.model_dump()
    payload["evaluation_mode"] = expected_mode

    # The schema may have derived a JOB_FIT grade solely because the provider
    # omitted evaluation_mode and its default is JOB_FIT. Recompute it under
    # the authoritative server mode instead of returning a misleading label.
    payload["match_grade"] = None
    generated_job_fit_summary = (
        "Job Fit Analysis: Candidate achieves an overall score of "
        f"{report.overall_fit_score}/100 ({report.match_grade})."
    )
    if payload["executive_summary"] == generated_job_fit_summary:
        payload["executive_summary"] = None
    return LLMEvaluationReport.model_validate(payload)


async def evaluate_cv_fit(
    canonical_cv: dict[str, Any],
    job_description: str | None = None,
) -> EvaluationResult:
    """Evaluate canonical CV JSON using LLM #2.

    If job_description is provided, performs a target JOB_FIT evaluation.
    If job_description is None/empty, performs a standalone GENERAL_AUDIT of CV quality.

    Args:
        canonical_cv: Normalized CV JSON dictionary produced by LLM #1.
        job_description: Optional target Job Description text.

    Returns:
        EvaluationResult containing LLMEvaluationReport schema.
    """
    has_jd = bool(job_description and job_description.strip())
    mode_name = "JOB_FIT" if has_jd else "GENERAL_AUDIT"
    logger.info("Running LLM #2 CV Evaluator (mode: %s)...", mode_name)

    system_prompt = build_cv_evaluator_prompt(has_jd=has_jd)
    if has_jd:
        user_prompt = (
            "=== CANONICAL CV JSON ===\n"
            f"{json.dumps(canonical_cv, ensure_ascii=False, indent=2)}\n\n"
            "=== JOB DESCRIPTION ===\n"
            f"{job_description.strip()}\n\n"
            "Evaluate the candidate's fit against the Job Description and return a structured LLMEvaluationReport JSON."
        )
    else:
        user_prompt = (
            "=== CANONICAL CV JSON ===\n"
            f"{json.dumps(canonical_cv, ensure_ascii=False, indent=2)}\n\n"
            "Perform a comprehensive standalone CV Quality Audit & Health Check on this CV. Return a structured LLMEvaluationReport JSON."
        )

    report = await call_llm_with_fallback(
        system_prompt=system_prompt,
        user_input=user_prompt,
        response_model=LLMEvaluationReport,
        feature_name=f"cv_evaluation_{mode_name.lower()}",
        max_output_tokens=CV_EVALUATION_MAX_OUTPUT_TOKENS,
    )

    return EvaluationResult(
        report=_enforce_evaluation_mode(report, expected_mode=mode_name),
        raw_prompt=user_prompt,
        provider_used="LLM_Router",
    )
