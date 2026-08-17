"""CV Analysis orchestration with source-language enforcement."""

import logging
from collections.abc import Awaitable, Callable
from functools import partial
from typing import Any

from fastapi import BackgroundTasks

from app.models.requests import LayoutLine
from app.models.responses import (
    CVAnalysisGenerationResponse,
    CVAnalysisLLMResponse,
    CVAnalysisResponse,
)
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
from app.services.cv_reconstruction_service import (
    reconstruction_diagnostics,
    validate_reconstruction_gate,
)
from app.services.cv_structuring_service import structure_cv
from app.services.files import FileService

_logger = logging.getLogger(__name__)

AnalysisProgress = Callable[[str, str, dict[str, Any] | None], Awaitable[None]]


async def _report_progress(
    progress: AnalysisProgress | None,
    stage: str,
    message: str,
    details: dict[str, Any] | None = None,
) -> None:
    if progress is not None:
        await progress(stage, message, details)


async def analyze_cv(
    *,
    cv_text: str,
    jd_text: str,
    background_tasks: BackgroundTasks | None = None,
    layout_data: list[LayoutLine] | None = None,
    raw_extraction_ref_id: str | None = None,
    user_id: str | None = None,
    file_service: FileService | None = None,
    progress: AnalysisProgress | None = None,
) -> CVAnalysisResponse:
    """Generate a scored CV Analysis in the source CV's primary language.

    Client layout metadata is retained only for request compatibility. PDF
    structure is loaded from the server-owned raw extraction reference; manual
    text is converted to deterministic server-side blocks.
    """
    await _report_progress(progress, "validating", "Đang kiểm tra nội dung CV...")
    _logger.info(
        "Stage [validating]: submitted CV len=%d, JD len=%d, has_raw_ref=%s",
        len(cv_text),
        len(jd_text),
        bool(raw_extraction_ref_id),
    )
    if layout_data:
        _logger.info("Ignoring client layout_data in authoritative structuring path")

    await _report_progress(
        progress,
        "structuring",
        "Đang nhận diện cấu trúc và các mục trong CV...",
    )

    async def report_structuring_retry(attempt: int, total_attempts: int) -> None:
        _logger.warning(
            "Stage [retrying]: semantic parser busy, attempt %d/%d",
            attempt,
            total_attempts,
        )
        await _report_progress(
            progress,
            "retrying",
            "Dịch vụ nhận diện cấu trúc đang bận, Bé Đậu đang thử lại...",
            {
                "attempt": attempt,
                "total_attempts": total_attempts,
                "operation": "structuring",
            },
        )

    structured = await structure_cv(
        cv_text=cv_text,
        raw_extraction_ref_id=raw_extraction_ref_id,
        user_id=user_id,
        file_service=file_service,
        background_tasks=background_tasks,
        on_retry=report_structuring_retry,
    )
    authoritative_cv_text = structured.source_text
    source_document = structured.document

    # Phase 4: conservation gate — reject before analysis LLM if source content is not conserved
    validate_reconstruction_gate(source_document)

    source_language = detect_cv_language(authoritative_cv_text)

    _logger.info(
        "Stage [structuring]: complete sections=%d parser=%s fallback=%s language=%s",
        len(source_document.sections),
        source_document.parser_version,
        structured.used_fallback,
        source_language,
    )

    if jd_text.strip():
        context_instruction = CV_ANALYSIS_CONTEXT_WITH_JD
        user_content = f"CV của ứng viên:\n{authoritative_cv_text}\n\nMô tả Công việc (JD):\n{jd_text}"
    else:
        context_instruction = CV_ANALYSIS_CONTEXT_WITHOUT_JD
        user_content = f"CV của ứng viên:\n{authoritative_cv_text}"

    _logger.info(
        "Stage [analyzing]: Sending prompt to LLM waterfall router (language=%s)...",
        source_language,
    )
    await _report_progress(progress, "analyzing", "Đang đối chiếu CV với công việc...")

    async def report_retry(attempt: int, total_attempts: int) -> None:
        _logger.warning(
            "Stage [retrying]: AI service busy, attempt %d/%d...",
            attempt,
            total_attempts,
        )
        await _report_progress(
            progress,
            "retrying",
            "Dịch vụ AI đang bận, Bé Đậu đang tự thử lại...",
            {"attempt": attempt, "total_attempts": total_attempts},
        )

    generated = await call_llm_with_fallback(
        build_cv_analysis_prompt(context_instruction, source_language),
        user_content,
        CVAnalysisGenerationResponse,
        feature_name="cv_analyzer",
        prompt_version="1.1.0",
        background_tasks=background_tasks,
        max_retries=1,
        result_validator=partial(
            ensure_analysis_response_language,
            expected_language=source_language,
            source_cv_text=authoritative_cv_text,
            source_reference_text=f"{authoritative_cv_text}\n{jd_text}",
        ),
        on_retry=report_retry,
    )
    _logger.info(
        "Stage [finalizing]: Received scoring response. Running evidence-constrained CV rewriter..."
    )
    await _report_progress(
        progress, "finalizing", "Đang đề xuất cải thiện nội dung chuẩn ATS..."
    )
    parsed = CVAnalysisLLMResponse.model_validate(generated.model_dump())
    parsed.tailored_cv = build_source_preserving_tailored_cv(
        parsed,
        authoritative_cv_text,
    )

    # Phase 5: Evidence-constrained rewrite service
    from app.services.cv_rewrite_service import rewrite_cv

    rewrite_result = await rewrite_cv(
        source_document=source_document,
        source_raw_extraction=structured.raw_extraction,
        jd_text=jd_text,
        source_language=source_language,
        background_tasks=background_tasks,
    )

    tailored_document = rewrite_result.tailored_document
    parsed.document_v2 = tailored_document

    response = build_scored_analysis(parsed, source_language=source_language)
    response.reconstruction_diagnostics = reconstruction_diagnostics(
        source_document,
    )
    response.source_document_v2 = source_document
    response.tailoring_diagnostics = rewrite_result.diagnostics
    return response
