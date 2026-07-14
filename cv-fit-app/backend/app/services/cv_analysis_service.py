"""CV Analysis orchestration with source-language enforcement."""

from functools import partial

from fastapi import BackgroundTasks

from app.models.responses import CVAnalysisLLMResponse, CVAnalysisResponse
from app.prompts.system_prompts import (
    CV_ANALYSIS_CONTEXT_WITH_JD,
    CV_ANALYSIS_CONTEXT_WITHOUT_JD,
    build_cv_analysis_prompt,
)
from app.services.ai_service import call_llm_with_fallback
from app.services.cv_language import (
    detect_cv_language,
    ensure_analysis_response_language,
)
from app.services.cv_quality_checks import (
    build_scored_analysis,
    build_source_preserving_tailored_cv,
)


async def analyze_cv(
    *,
    cv_text: str,
    jd_text: str,
    background_tasks: BackgroundTasks | None = None,
) -> CVAnalysisResponse:
    """Generate a scored CV Analysis in the source CV's primary language."""
    source_language = detect_cv_language(cv_text)
    if jd_text.strip():
        context_instruction = CV_ANALYSIS_CONTEXT_WITH_JD
        user_content = (
            f"CV của ứng viên:\n{cv_text}\n\nMô tả Công việc (JD):\n{jd_text}"
        )
    else:
        context_instruction = CV_ANALYSIS_CONTEXT_WITHOUT_JD
        user_content = f"CV của ứng viên:\n{cv_text}"

    parsed = await call_llm_with_fallback(
        build_cv_analysis_prompt(context_instruction, source_language),
        user_content,
        CVAnalysisLLMResponse,
        feature_name="cv_analyzer",
        prompt_version="1.1.0",
        background_tasks=background_tasks,
        max_retries=2,
        result_validator=partial(
            ensure_analysis_response_language,
            expected_language=source_language,
        ),
    )
    parsed.tailored_cv = build_source_preserving_tailored_cv(parsed, cv_text)
    return build_scored_analysis(parsed, source_language=source_language)
