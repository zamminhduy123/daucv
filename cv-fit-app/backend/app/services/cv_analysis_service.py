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
    reconstruct_cv_text,
    reconstruct_from_lines,
    reconstruction_diagnostics,
    validate_reconstruction_gate,
)
from app.services.cv_rendering_diagnostics import compact_rendering_warnings
from app.services.cv_tailoring_service import apply_block_rewrites, rewrite_payload
from app.services.layout_extraction import ExtractedLine

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
    progress: AnalysisProgress | None = None,
) -> CVAnalysisResponse:
    """Generate a scored CV Analysis in the source CV's primary language.

    When *layout_data* is provided (from Phase 3 layout extraction),
    uses real page/column/font metadata for reconstruction instead of
    fabricating synthetic layout from plain text.
    """
    await _report_progress(progress, "validating", "Đang kiểm tra nội dung CV...")
    source_language = detect_cv_language(cv_text)
    _logger.info(
        "Stage [validating]: CV len=%d, JD len=%d, source_language=%s",
        len(cv_text),
        len(jd_text),
        source_language,
    )
    await _report_progress(progress, "reconstructing", "Đang đọc cấu trúc CV...")
    _logger.info(
        "Stage [reconstructing]: Reconstructing CV structure from %s (layout_lines=%d)...",
        "layout_data" if layout_data else "plain_text",
        len(layout_data) if layout_data else 0,
    )
    if layout_data:
        lines = [
            ExtractedLine(
                text=item.text,
                page=item.page,
                x=item.x,
                y=item.y,
                width=item.width,
                height=item.height,
                font_size=item.font_size,
                font_weight=item.font_weight,
                bullet_marker=item.bullet_marker,
                normalized_text=item.normalized_text,
                column_id=item.column_id,
                joined_to_prev=item.joined_to_prev,
                is_page_break_marker=item.is_page_break_marker,
                is_layout_artifact=item.is_layout_artifact,
                page_height=item.page_height,
                source_line_id=item.source_line_id or "",
            )
            for item in layout_data
        ]
        source_document = reconstruct_from_lines(lines)
    else:
        source_document = reconstruct_cv_text(cv_text)

    _logger.info(
        "Stage [reconstructing]: Structure built. Sections: %d (%s), Summary lines: %d, Diagnostics warnings: %s",
        len(source_document.sections),
        [s.type for s in source_document.sections],
        len(source_document.summary.source_line_ids) if source_document.summary else 0,
        source_document.reconstruction_warnings,
    )

    validate_reconstruction_gate(source_document)
    _logger.info("Stage [reconstructing]: Quality gate passed successfully.")

    typed_source = rewrite_payload(source_document)
    if jd_text.strip():
        context_instruction = CV_ANALYSIS_CONTEXT_WITH_JD
        user_content = (
            f"CV của ứng viên:\n{cv_text}\n\nMô tả Công việc (JD):\n{jd_text}"
            f"\n\nTYPED SOURCE DOCUMENT (structure is authoritative):\n{typed_source}"
        )
    else:
        context_instruction = CV_ANALYSIS_CONTEXT_WITHOUT_JD
        user_content = (
            f"CV của ứng viên:\n{cv_text}"
            f"\n\nTYPED SOURCE DOCUMENT (structure is authoritative):\n{typed_source}"
        )

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
            source_cv_text=cv_text,
            source_reference_text=f"{cv_text}\n{jd_text}",
        ),
        on_retry=report_retry,
    )
    _logger.info(
        "Stage [finalizing]: Received LLM response. Building tailored CV & block rewrites..."
    )
    await _report_progress(
        progress, "finalizing", "Đang hoàn thiện kết quả phân tích..."
    )
    parsed = CVAnalysisLLMResponse.model_validate(generated.model_dump())
    parsed.tailored_cv = build_source_preserving_tailored_cv(parsed, cv_text)
    tailored_document, _warnings = apply_block_rewrites(
        source_document,
        parsed.block_rewrites,
        cv_text,
    )
    tailored_document.reconstruction_warnings = list(
        dict.fromkeys(
            [
                *tailored_document.reconstruction_warnings,
                *compact_rendering_warnings(tailored_document),
            ],
        ),
    )
    parsed.document_v2 = tailored_document
    response = build_scored_analysis(parsed, source_language=source_language)
    response.reconstruction_diagnostics = reconstruction_diagnostics(
        tailored_document,
    )
    response.source_document_v2 = source_document
    return response
