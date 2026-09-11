"""User-facing API routes — CV analysis, interview, TTS, and writing assistant.

Route handlers are kept thin: validate input → build prompt → call service → return.
"""

import asyncio
import json
import logging
import re
import tempfile
from collections.abc import AsyncIterator
from contextlib import suppress
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal
from uuid import UUID, uuid4

import edge_tts
from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    File,
    Form,
    HTTPException,
    UploadFile,
)
from fastapi.responses import FileResponse, Response, StreamingResponse

from app.core.config import (
    CV_ANALYSIS_REQUEST_TIMEOUT,
    PDF_MAX_SIZE,
    RAW_EXTRACTION_BUCKET,
    SKIP_RAW_EXTRACTION_UPLOAD,
)
from app.dependencies import (
    get_current_user,
    get_file_service,
    refund_credits,
    reserve_credits,
)
from app.models.cv_raw_extraction import RAW_EXTRACTION_CONTENT_TYPE
from app.models.domain import MatchResult
from app.models.requests import (
    AnalyzeCVRequest,
    InterviewChatRequest,
    InterviewFinishRequest,
    ParseProfileRequest,
    TTSRequest,
    WriterRequest,
)
from app.models.responses import (
    CandidateProfileResponse,
    CVAnalysisEnvelope,
    CVAnalysisPayload,
    CVAnalysisResponse,
    FinalInterviewReport,
    InterviewTurnResponse,
    WriterResponse,
)
from app.prompts.system_prompts import (
    INTERVIEW_FIRST_TURN_ADDENDUM,
    PERSONA_INSTRUCTIONS,
    ROUND_LABELS,
    build_interview_chat_prompt,
    build_interview_finish_prompt,
    build_job_parser_prompt,
    build_upload_and_match_prompt,
    build_writer_prompt,
)
from app.schemas.feedback import FeedbackResponse, FeedbackSubmit
from app.schemas.tailored_cv import VerifyUserEditRequest, VerifyUserEditResponse
from app.schemas.user import (
    CVListResponse,
    CVResponse,
    StructuredDocumentSaveRequest,
    UpdateCVRequest,
    UserProfileResponse,
)
from app.services import cv_analysis_service, user_cv_service
from app.services.ai_service import call_llm_with_fallback
from app.services.cv_rewrite_service import verify_and_rebind_user_edit
from app.services.files import FileService
from app.services.layout_extraction import (
    extract_cv_content_blocks,
    raw_extraction_to_layout_lines,
    raw_extraction_to_text,
)
from app.services.pdf_thumbnail import generate_pdf_thumbnail
from app.services.tailored_cv_metadata import (
    issue_tailoring_entitlement_v3,
)
from app.utils.helpers import extract_text_from_pdf

_logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["user"])


async def _refund_reserved_credit(user_id: str, tx_type: str, description: str) -> None:
    with suppress(Exception):
        await refund_credits(
            user_id=user_id,
            amount=1,
            tx_type=tx_type,
            description=description,
        )


def _build_cv_analysis_envelope(
    scored: CVAnalysisResponse,
    *,
    user_id: str,
    cv_text: str,
    jd_text: str,
) -> CVAnalysisEnvelope:
    if (
        scored.document_v2 is None
        or scored.source_document_v2 is None
        or scored.reconstruction_diagnostics is None
    ):
        raise RuntimeError("Typed CV reconstruction did not complete")
    tailoring_diag = scored.tailoring_diagnostics
    if tailoring_diag is None:
        raise RuntimeError("Phase 5 tailoring diagnostics did not complete")
    entitlement = issue_tailoring_entitlement_v3(
        to_uuid(user_id),
        cv_text,
        jd_text,
        scored.source_document_v2,
        scored.document_v2,
        tailoring_diag,
    )

    analysis = scored.model_dump(
        exclude={
            "tailored_cv",
            "document_v2",
            "source_document_v2",
            "reconstruction_diagnostics",
            "tailoring_diagnostics",
            "tailoring_entitlement",
            "block_rewrites",
        },
    )
    return CVAnalysisEnvelope(
        analysis=CVAnalysisPayload(**analysis),
        tailored_cv=scored.document_v2,
        source_document_v2=scored.source_document_v2,
        reconstruction_diagnostics=scored.reconstruction_diagnostics,
        tailoring_diagnostics=tailoring_diag,
        legacy_tailored_cv=scored.tailored_cv,
        tailoring_entitlement=entitlement,
    )


# ---------------------------------------------------------------------------
# POST /api/upload-and-match
# ---------------------------------------------------------------------------


@router.post("/upload-and-match", response_model=MatchResult)
async def upload_and_match(
    background_tasks: BackgroundTasks,
    cv_file: UploadFile = File(...),
    jd_text: str = Form(""),
    user: dict = Depends(get_current_user),
):
    """Parse the uploaded CV PDF, compare with the JD, and return:
    - match_score  (0–100)
    - missing_skills  (list of strings)
    - tailored_cv  (rewritten resume JSON)
    """
    if cv_file.content_type != "application/pdf":
        raise HTTPException(status_code=400, detail="Only PDF files are accepted.")

    if cv_file.size is not None and cv_file.size > PDF_MAX_SIZE:
        raise HTTPException(
            status_code=413,
            detail=f"PDF too large. Maximum size is {PDF_MAX_SIZE // (1024 * 1024)} MB.",
        )

    file_bytes = await cv_file.read()
    try:
        cv_text = extract_text_from_pdf(file_bytes)
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"Could not parse PDF: {e}")

    if not cv_text:
        raise HTTPException(
            status_code=422,
            detail="PDF appears to be empty or image-only.",
        )

    system_prompt = build_upload_and_match_prompt()
    tx_type = "cv_analysis"
    reserve_description = f"Khớp và viết lại CV: {cv_file.filename}"
    refund_description = f"Hoàn credit do lỗi khi khớp CV: {cv_file.filename}"

    await reserve_credits(
        user_id=user["id"],
        amount=1,
        tx_type=tx_type,
        description=reserve_description,
    )

    try:
        data = await call_llm_with_fallback(
            system_prompt,
            f"CV:\n{cv_text}\n\nJob Description:\n{jd_text}",
            MatchResult,
            feature_name="upload_and_match",
            prompt_version="1.0.0",
            background_tasks=background_tasks,
        )
        return data
    except json.JSONDecodeError as e:
        await _refund_reserved_credit(user["id"], tx_type, refund_description)
        raise HTTPException(status_code=502, detail=f"AI returned invalid JSON: {e}")
    except HTTPException:
        await _refund_reserved_credit(user["id"], tx_type, refund_description)
        raise
    except Exception as e:
        await _refund_reserved_credit(user["id"], tx_type, refund_description)
        raise HTTPException(status_code=502, detail=f"LLM error: {e}")


# ---------------------------------------------------------------------------
# POST /api/extract-pdf
# ---------------------------------------------------------------------------


@router.post("/extract-pdf")
async def extract_pdf(
    file: UploadFile = File(...),
    purpose: Literal["cv", "jd"] = Form(...),
    replaces_raw_extraction_id: UUID | None = Form(default=None),
    user: dict = Depends(get_current_user),
    file_service: FileService = Depends(get_file_service),
):
    if file.content_type != "application/pdf":
        raise HTTPException(status_code=400, detail="Only PDF files are accepted.")
    if file.size is not None and file.size > PDF_MAX_SIZE:
        raise HTTPException(
            status_code=413,
            detail="PDF exceeds the maximum allowed size.",
        )
    try:
        file_bytes = await file.read(PDF_MAX_SIZE + 1)
        if len(file_bytes) > PDF_MAX_SIZE:
            raise HTTPException(
                status_code=413,
                detail="PDF exceeds the maximum allowed size.",
            )
        user_id = str(user["id"])
        raw = extract_cv_content_blocks(file_bytes)
        lines = raw_extraction_to_layout_lines(raw)
        text = raw_extraction_to_text(raw)
        raw_file_info = None
        if purpose == "cv":
            if not SKIP_RAW_EXTRACTION_UPLOAD:
                # Phase 3 will resolve this opaque reference server-side instead of
                # trusting client-supplied flattened layout_data.
                raw_file_info = await file_service.upload_file(
                    user_id=user_id,
                    filename=f"raw-extraction-{uuid4().hex}.json",
                    data=raw.model_dump_json().encode("utf-8"),
                    content_type=RAW_EXTRACTION_CONTENT_TYPE,
                    bucket=RAW_EXTRACTION_BUCKET,
                    include_url=False,
                )
                if not raw_file_info.get("id"):
                    raise RuntimeError(
                        "Raw extraction metadata could not be persisted."
                    )
            else:
                _logger.info(
                    "Skipping raw extraction Supabase upload in development mode."
                )

        # Source PDFs keep their existing public-file behavior.
        file_info = None
        raw_filename = Path(file.filename or "uploaded_cv.pdf").name
        safe_filename = (
            re.sub(r"[^\w.\-]+", "_", raw_filename).strip("._") or "uploaded_cv.pdf"
        )
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        try:
            stored_filename = f"{timestamp}_{uuid4().hex[:8]}_{safe_filename}"
            file_info = await file_service.upload_file(
                user_id=user_id,
                filename=stored_filename,
                data=file_bytes,
                content_type="application/pdf",
                bucket="cv",
                original_filename=raw_filename,
            )
        except Exception as upload_err:
            _logger.warning(
                f"File upload to bucket skipped/failed during extract-pdf: {upload_err}",
                exc_info=True,
            )

        # Pre-render first-page WebP thumbnail for fast, reliable, high-quality card previews
        thumbnail_info = None
        if purpose == "cv":
            try:
                thumb_bytes = generate_pdf_thumbnail(file_bytes)
                if thumb_bytes:
                    is_webp = (
                        thumb_bytes.startswith(b"RIFF")
                        and len(thumb_bytes) >= 12
                        and thumb_bytes[8:12] == b"WEBP"
                    )
                    ext = "webp" if is_webp else "jpg"
                    mime = "image/webp" if is_webp else "image/jpeg"
                    stored_thumb_name = f"{timestamp}_{uuid4().hex[:8]}_thumb.{ext}"
                    thumbnail_info = await file_service.upload_file(
                        user_id=user_id,
                        filename=stored_thumb_name,
                        data=thumb_bytes,
                        content_type=mime,
                        bucket="cv",
                        include_url=False,
                        original_filename=f"thumb_{raw_filename}.{ext}",
                    )
            except Exception as thumb_err:
                _logger.warning(
                    f"Thumbnail upload to bucket skipped/failed during extract-pdf: {thumb_err}",
                    exc_info=True,
                )

        pending_raw_cleanup_ids: list[str] = []
        if (
            purpose == "cv"
            and replaces_raw_extraction_id is not None
            and raw_file_info is not None
        ):
            old_raw_id = str(replaces_raw_extraction_id)
            new_raw_id = str(raw_file_info["id"])
            # Persist-new-first policy: the old artifact remains valid if
            # extraction or new persistence fails. Once the new artifact is
            # durable, failure to retire the old one is returned as explicit
            # cleanup state while the new reference remains usable.
            if old_raw_id != new_raw_id:
                try:
                    old_deleted = await file_service.delete_raw_extraction(
                        user_id,
                        old_raw_id,
                    )
                except Exception:
                    _logger.warning("Old raw extraction cleanup remains pending")
                    old_deleted = False
                if not old_deleted:
                    pending_raw_cleanup_ids.append(old_raw_id)

        res = {
            "text": text,
            "layout_data": [asdict(line) for line in lines],
        }
        if raw_file_info:
            res["raw_extraction_ref"] = {
                "id": str(raw_file_info["id"]),
                "extraction_version": raw.extraction_version,
                "method": raw.method.value,
            }
        if pending_raw_cleanup_ids:
            res["pending_raw_extraction_cleanup_ids"] = pending_raw_cleanup_ids
        if file_info:
            res["file_info"] = file_info
        if thumbnail_info:
            res["thumbnail_file_id"] = str(thumbnail_info["id"])
        return res
    except HTTPException:
        raise
    except Exception as exc:
        _logger.error("PDF extraction failed")
        raise HTTPException(
            status_code=500,
            detail="PDF extraction failed. Please try again.",
        ) from exc


@router.delete("/raw-extractions/{file_id}", status_code=204)
async def delete_raw_extraction(
    file_id: UUID,
    user: dict = Depends(get_current_user),
    file_service: FileService = Depends(get_file_service),
) -> None:
    deleted = await file_service.delete_raw_extraction(str(user["id"]), str(file_id))
    if not deleted:
        raise HTTPException(status_code=404, detail="Raw extraction was not found.")


# ---------------------------------------------------------------------------
# POST /api/analyze-cv
# ---------------------------------------------------------------------------


@router.post("/analyze-cv", response_model=CVAnalysisEnvelope)
async def analyze_cv(
    req: AnalyzeCVRequest,
    background_tasks: BackgroundTasks,
    user: dict = Depends(get_current_user),
    file_service: FileService = Depends(get_file_service),
):
    """Accept raw CV text and a Job Description.
    Return a structured analysis.
    """
    extracted_text = req.cv_text.strip()
    jd_text = req.jd_text or ""

    if not extracted_text:
        raise HTTPException(
            status_code=422,
            detail="Cần cung cấp nội dung CV.",
        )

    tx_type = "cv_analysis"
    refund_description = "Hoàn credit do lỗi khi phân tích CV"

    await reserve_credits(
        user_id=user["id"],
        amount=1,
        tx_type=tx_type,
        description="Phân tích CV chi tiết",
    )

    try:
        async with asyncio.timeout(CV_ANALYSIS_REQUEST_TIMEOUT):
            scored = await cv_analysis_service.analyze_cv(
                cv_text=extracted_text,
                jd_text=jd_text,
                background_tasks=background_tasks,
                layout_data=req.layout_data,
                raw_extraction_ref_id=(
                    str(req.raw_extraction_ref_id)
                    if req.raw_extraction_ref_id
                    else None
                ),
                user_id=str(user["id"]),
                file_service=file_service,
            )
        return _build_cv_analysis_envelope(
            scored,
            user_id=user["id"],
            cv_text=extracted_text,
            jd_text=jd_text,
        )
    except TimeoutError:
        await _refund_reserved_credit(user["id"], tx_type, refund_description)
        raise HTTPException(
            status_code=504,
            detail="CV analysis timed out. Please try again.",
        ) from None
    except HTTPException:
        await _refund_reserved_credit(user["id"], tx_type, refund_description)
        raise
    except ValueError as exc:
        _logger.warning(
            "CV reconstruction quality gate rejected document: error_type=%s",
            type(exc).__name__,
        )
        await _refund_reserved_credit(user["id"], tx_type, refund_description)
        raise HTTPException(
            status_code=422,
            detail="Cấu trúc CV không đủ tiêu chuẩn (tiêu đề mục dính liền hoặc thiếu thông tin). Vui lòng tải lên file PDF gốc.",
        ) from exc
    except Exception as e:
        _logger.error("CV analysis failed: error_type=%s", type(e).__name__)
        await _refund_reserved_credit(user["id"], tx_type, refund_description)
        raise HTTPException(
            status_code=500,
            detail="Phân tích CV thất bại. Vui lòng thử lại sau.",
        )


@router.post("/analyze-cv/stream")
async def analyze_cv_stream(
    req: AnalyzeCVRequest,
    background_tasks: BackgroundTasks,
    user: dict = Depends(get_current_user),
    file_service: FileService = Depends(get_file_service),
) -> StreamingResponse:
    """Stream real CV-analysis progress and the final envelope as NDJSON."""
    extracted_text = req.cv_text.strip()
    jd_text = req.jd_text or ""
    if not extracted_text:
        raise HTTPException(status_code=422, detail="Cần cung cấp nội dung CV.")

    tx_type = "cv_analysis"
    refund_description = "Hoàn credit do lỗi khi phân tích CV"
    await reserve_credits(
        user_id=user["id"],
        amount=1,
        tx_type=tx_type,
        description="Phân tích CV chi tiết",
    )

    events: asyncio.Queue[dict[str, Any]] = asyncio.Queue()

    async def report_progress(
        stage: str,
        message: str,
        details: dict[str, Any] | None,
    ) -> None:
        event: dict[str, Any] = {
            "type": "progress",
            "stage": stage,
            "message": message,
        }
        if details:
            event["details"] = details
        await events.put(event)

    async def run_analysis() -> None:
        await events.put(
            {
                "type": "progress",
                "stage": "queued",
                "message": "Đã nhận CV, bắt đầu phân tích...",
            },
        )
        try:
            async with asyncio.timeout(CV_ANALYSIS_REQUEST_TIMEOUT):
                scored = await cv_analysis_service.analyze_cv(
                    cv_text=extracted_text,
                    jd_text=jd_text,
                    background_tasks=background_tasks,
                    layout_data=req.layout_data,
                    raw_extraction_ref_id=(
                        str(req.raw_extraction_ref_id)
                        if req.raw_extraction_ref_id
                        else None
                    ),
                    user_id=str(user["id"]),
                    file_service=file_service,
                    progress=report_progress,
                )
            envelope = _build_cv_analysis_envelope(
                scored,
                user_id=user["id"],
                cv_text=extracted_text,
                jd_text=jd_text,
            )
            await events.put(
                {
                    "type": "complete",
                    "data": envelope.model_dump(mode="json"),
                },
            )
        except asyncio.CancelledError:
            await _refund_reserved_credit(user["id"], tx_type, refund_description)
            raise
        except TimeoutError:
            await _refund_reserved_credit(user["id"], tx_type, refund_description)
            await events.put(
                {
                    "type": "error",
                    "status": 504,
                    "message": "Phân tích CV quá thời gian. Vui lòng thử lại.",
                },
            )
        except HTTPException as exc:
            await _refund_reserved_credit(user["id"], tx_type, refund_description)
            await events.put(
                {
                    "type": "error",
                    "status": exc.status_code,
                    "message": str(exc.detail),
                },
            )
        except ValueError as exc:
            _logger.warning(
                "CV reconstruction quality gate rejected document: error_type=%s",
                type(exc).__name__,
            )
            await _refund_reserved_credit(user["id"], tx_type, refund_description)
            await events.put(
                {
                    "type": "error",
                    "status": 422,
                    "message": "Cấu trúc CV không đủ tiêu chuẩn (tiêu đề mục dính liền hoặc thiếu thông tin). Vui lòng tải lên file PDF gốc.",
                },
            )
        except Exception as exc:
            _logger.error(
                "CV analysis streaming task failed: error_type=%s", type(exc).__name__
            )
            await _refund_reserved_credit(user["id"], tx_type, refund_description)
            await events.put(
                {
                    "type": "error",
                    "status": 500,
                    "message": "Phân tích CV thất bại. Vui lòng thử lại sau.",
                },
            )

    async def stream_events() -> AsyncIterator[str]:
        task = asyncio.create_task(run_analysis())
        try:
            while True:
                event = await events.get()
                yield json.dumps(event, ensure_ascii=False) + "\n"
                if event["type"] in {"complete", "error"}:
                    break
        finally:
            if not task.done():
                task.cancel()
            with suppress(asyncio.CancelledError):
                await task

    return StreamingResponse(
        stream_events(),
        media_type="application/x-ndjson",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


# ---------------------------------------------------------------------------
# POST /api/jobs/parse-profile
# ---------------------------------------------------------------------------


@router.post("/jobs/parse-profile", response_model=CandidateProfileResponse)
async def parse_profile(
    req: ParseProfileRequest,
    background_tasks: BackgroundTasks,
    user: dict = Depends(get_current_user),
):
    """Parse candidate CV to get structured profile + search queries using LLM."""
    cv_text = req.cv_text.strip()
    if not cv_text:
        raise HTTPException(
            status_code=422,
            detail="Nội dung CV không được để trống.",
        )

    system_prompt = build_job_parser_prompt()
    user_content = f"Nội dung CV:\n{cv_text}"
    tx_type = "job_search"
    refund_description = "Hoàn credit do lỗi khi trích xuất hồ sơ tìm việc"

    await reserve_credits(
        user_id=user["id"],
        amount=1,
        tx_type=tx_type,
        description="Trích xuất hồ sơ ứng viên tìm việc",
    )

    try:
        parsed = await call_llm_with_fallback(
            system_prompt,
            user_content,
            CandidateProfileResponse,
            feature_name="job_parser",
            prompt_version="1.0.0",
            background_tasks=background_tasks,
        )
        return parsed
    except HTTPException:
        await _refund_reserved_credit(user["id"], tx_type, refund_description)
        raise
    except Exception as e:
        await _refund_reserved_credit(user["id"], tx_type, refund_description)
        raise HTTPException(
            status_code=500,
            detail=f"Profile parsing failed: {e}",
        )


# ---------------------------------------------------------------------------
# POST /api/interview/chat
# ---------------------------------------------------------------------------


@router.post("/interview/chat", response_model=InterviewTurnResponse)
async def interview_chat(
    req: InterviewChatRequest,
    background_tasks: BackgroundTasks,
    user: dict = Depends(get_current_user),
):
    """Stateless mock interview turn processor mapping an InterviewChatRequest to an InterviewTurnResponse.
    Supports bounded interviews with question progress tracking.
    """
    active_persona = PERSONA_INSTRUCTIONS.get(
        req.interview_type,
        PERSONA_INSTRUCTIONS["general"],
    )

    # --- Dynamic question strategy based on progress ---
    if req.current_question == 1:
        question_strategy = "Ask an introductory/ice-breaker question to warm up the candidate. Keep it light but professional."
    elif req.current_question == req.total_questions:
        question_strategy = "This is the FINAL question. Ask a wrap-up or high-level culture-fit question (e.g., career goals, team values, why this company)."
    elif req.interview_type == "hr":
        question_strategy = (
            "Ask a behavioral question to explore the candidate's responsibilities in past projects, "
            "teamwork, conflict resolution, or soft skills. Keep it relevant to their role but do not ask "
            "for low-level technical/coding implementation details or specific code techniques."
        )
    elif req.interview_type == "manager":
        question_strategy = (
            "Deep dive into project ownership, handling pressure/conflicts, business impact, "
            "and leadership/collaboration."
        )
    elif req.interview_type == "technical":
        question_strategy = (
            "Deep dive into a specific technical or situational requirement from the JD. "
            "Challenge the candidate on tools, frameworks, and system design."
        )
    else:
        # general or fallback
        question_strategy = (
            "Ask a balanced question covering a mix of professional experience, high-level technical alignment, "
            "or situational soft skills."
        )

    if req.jd_text.strip():
        jd_context = (
            f"You are interviewing the candidate for this specific JD:\n{req.jd_text}"
        )
    else:
        jd_context = "The candidate did not provide a specific JD. Conduct a general interview based purely on their CV to assess their past experiences, strengths, and general career readiness."

    system_prompt = build_interview_chat_prompt(
        active_persona=active_persona,
        jd_context=jd_context,
        cv_text=req.cv_text,
        current_question=req.current_question,
        total_questions=req.total_questions,
        question_strategy=question_strategy,
    )

    contents = []
    for msg in req.chat_history:
        contents.append(
            {
                "role": "assistant" if msg.role == "assistant" else "user",
                "content": msg.content,
            },
        )

    if not contents:
        # First turn logic setup since chat history is empty
        system_prompt += INTERVIEW_FIRST_TURN_ADDENDUM
        # Push default startup cue for the LLMs since content is blank
        contents = [
            {
                "role": "user",
                "content": "Xin chào, tôi đã sẵn sàng tham gia buổi phỏng vấn.",
            },
        ]

    if req.current_question == 1:
        await reserve_credits(
            user_id=user["id"],
            amount=1,
            tx_type="mock_interview",
            description="Bắt đầu buổi phỏng vấn giả định",
        )

    try:
        parsed = await call_llm_with_fallback(
            system_prompt,
            contents,
            InterviewTurnResponse,
            feature_name="mock_interview",
            prompt_version="1.0.0",
            background_tasks=background_tasks,
        )
        return parsed
    except HTTPException:
        if req.current_question == 1:
            await _refund_reserved_credit(
                user["id"],
                "mock_interview",
                "Hoàn credit do lỗi khi bắt đầu phỏng vấn giả định",
            )
        raise
    except Exception as e:
        if req.current_question == 1:
            await _refund_reserved_credit(
                user["id"],
                "mock_interview",
                "Hoàn credit do lỗi khi bắt đầu phỏng vấn giả định",
            )
        raise HTTPException(status_code=502, detail=f"AI Provider error: {e}")


# ---------------------------------------------------------------------------
# POST /api/interview/finish — Final Assessment Report
# ---------------------------------------------------------------------------


@router.post("/interview/finish", response_model=FinalInterviewReport)
async def interview_finish(
    req: InterviewFinishRequest,
    background_tasks: BackgroundTasks,
):
    """Takes the completed chat history and generates a comprehensive
    Final Assessment report with per-turn analysis.
    """
    if not req.chat_history:
        raise HTTPException(
            status_code=422,
            detail="Chat history is empty. Cannot generate report.",
        )

    round_label = ROUND_LABELS.get(req.interview_type, ROUND_LABELS["general"])

    if req.jd_text.strip():
        jd_context = f"Job Description (JD):\n{req.jd_text}\n"
    else:
        jd_context = "The candidate did not provide a specific JD. Evaluate their performance purely based on their CV claims, general career readiness, and industry standards.\n"

    system_prompt = build_interview_finish_prompt(
        jd_context=jd_context,
        cv_text=req.cv_text,
        round_label=round_label,
    )

    contents = []
    for msg in req.chat_history:
        contents.append(
            {
                "role": "assistant" if msg.role == "assistant" else "user",
                "content": msg.content,
            },
        )

    try:
        parsed = await call_llm_with_fallback(
            system_prompt,
            contents,
            FinalInterviewReport,
            feature_name="interview_finish",
            prompt_version="1.0.0",
            background_tasks=background_tasks,
        )
        return parsed
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=502,
            detail=f"Final assessment generation failed: {e}",
        )


# ---------------------------------------------------------------------------
# POST /api/interview/tts
# ---------------------------------------------------------------------------


@router.post("/interview/tts")
async def generate_tts(req: TTSRequest):
    if not req.text.strip():
        raise HTTPException(status_code=400, detail="Text cannot be empty.")

    try:
        # Note: vi-VN-HoaiMyNeural seems to have downtime/restrictions causing NoAudioReceived
        # using vi-VN-NamMinhNeural as it successfully generates audio
        communicate = edge_tts.Communicate(req.text, "vi-VN-NamMinhNeural")
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as tmp_file:
            tmp_path = tmp_file.name
        await communicate.save(tmp_path)
        return FileResponse(tmp_path, media_type="audio/mpeg")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ---------------------------------------------------------------------------
# POST /api/writer/generate — Writing Assistant
# ---------------------------------------------------------------------------


@router.post("/writer/generate", response_model=WriterResponse)
async def writer_generate(req: WriterRequest, background_tasks: BackgroundTasks):
    """Generate an application email, cover letter, LinkedIn message, Zalo message,
    or custom writing based on the user's CV and JD.
    """
    if not req.cv_text.strip():
        raise HTTPException(status_code=422, detail="CV is required.")

    system_prompt = build_writer_prompt(
        writing_type=req.writing_type,
        tone=req.tone,
        jd_text=req.jd_text,
        custom_prompt=req.custom_prompt,
        language=req.language,
    )

    if req.jd_text.strip():
        user_content = (
            f"CV của ứng viên:\n{req.cv_text}\n\nMô tả Công việc (JD):\n{req.jd_text}"
        )
    else:
        user_content = f"CV của ứng viên:\n{req.cv_text}"

    try:
        parsed = await call_llm_with_fallback(
            system_prompt,
            user_content,
            WriterResponse,
            feature_name="writing_assistant",
            prompt_version="1.0.0",
            background_tasks=background_tasks,
        )
        return parsed
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Writer generation failed: {e}")


@router.get("/user/credits")
async def get_user_credits(user: dict = Depends(get_current_user)) -> dict:
    return {"credits": user["credits"]}


@router.get("/user/profile", response_model=UserProfileResponse)
async def get_user_profile(
    user: dict = Depends(get_current_user),
) -> UserProfileResponse:
    return await user_cv_service.get_profile_with_stats(user)


def to_uuid(val: str | UUID) -> UUID:
    if isinstance(val, UUID):
        return val
    return UUID(str(val))


def parse_cv_uuid(cv_id: str) -> UUID:
    """Parse one CV row id or raise a localized 400 (single helper)."""
    try:
        return UUID(cv_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="ID CV không hợp lệ.") from None


@router.get("/user/cvs", response_model=CVListResponse)
async def list_user_cvs(
    user: dict = Depends(get_current_user),
    file_service: FileService = Depends(get_file_service),
) -> CVListResponse:
    cvs = await user_cv_service.list_cvs(to_uuid(user["id"]))
    # Resolve fresh per-row PDF URLs for first-page thumbnails. Rows are
    # already user-scoped by the query; URL minting re-checks ownership per
    # file so a forged pdf_file_id can never leak another user's object.
    # Signed URLs expire — the client refetches the list (re-minting) and
    # falls back to text previews on failure.
    for cv in cvs:
        if not cv.pdf_file_id:
            continue
        try:
            cv.pdf_url = await file_service.get_owned_file_url(
                str(user["id"]), cv.pdf_file_id
            )
        except Exception:
            _logger.warning(
                "Could not mint thumbnail URL for CV %s.", cv.id, exc_info=True
            )
    return CVListResponse(cvs=cvs)


@router.post("/user/cv", response_model=CVResponse)
async def upload_user_cv(
    req: UpdateCVRequest,
    user: dict = Depends(get_current_user),
) -> CVResponse:
    return await user_cv_service.create_cv(
        to_uuid(user["id"]),
        req.cv_text,
        req.cv_filename,
        req.raw_extraction_ref,
        req.pdf_file_id,
        req.thumbnail_file_id,
    )


@router.put("/user/cv/active", response_model=CVResponse)
async def update_active_cv(
    req: UpdateCVRequest,
    user: dict = Depends(get_current_user),
) -> CVResponse:
    return await user_cv_service.update_active_cv_text(
        to_uuid(user["id"]),
        req.cv_text,
        req.cv_filename,
    )


@router.put("/user/cv/{cv_id}", response_model=CVResponse)
async def update_user_cv(
    cv_id: str,
    req: UpdateCVRequest,
    user: dict = Depends(get_current_user),
    file_service: FileService = Depends(get_file_service),
) -> CVResponse:
    """Update one source CV row by id (multi-CV switcher; ownership-checked)."""
    cv_uuid = parse_cv_uuid(cv_id)
    user_id = str(user["id"])

    # If new files are being associated (e.g. re-upload/replace), clean up the old replaced files
    if req.pdf_file_id or req.thumbnail_file_id:
        old_row = await user_cv_service.get_cv(cv_uuid, to_uuid(user["id"]))
        if old_row:
            if (
                req.pdf_file_id
                and old_row.pdf_file_id
                and req.pdf_file_id != old_row.pdf_file_id
            ):
                await file_service.delete_owned_file(user_id, old_row.pdf_file_id)
            if (
                req.thumbnail_file_id
                and old_row.thumbnail_file_id
                and req.thumbnail_file_id != old_row.thumbnail_file_id
            ):
                await file_service.delete_owned_file(user_id, old_row.thumbnail_file_id)

    return await user_cv_service.update_cv_text(
        cv_uuid,
        to_uuid(user["id"]),
        req.cv_text,
        req.cv_filename,
        req.raw_extraction_ref,
        req.pdf_file_id,
        req.thumbnail_file_id,
    )


@router.delete("/user/cv/{cv_id}")
async def deactivate_user_cv(
    cv_id: str,
    user: dict = Depends(get_current_user),
    file_service: FileService = Depends(get_file_service),
) -> dict:
    """Delete one source CV and, best-effort, its stored files.

    File ids come from the owned row itself (raw extraction + source PDF + thumbnail),
    so callers cannot address other users' objects. Storage cleanup never
    blocks the row deletion: missing or already cleaned artifacts are
    ignored so orphaned files cannot strand the row.
    """
    cv_uuid = parse_cv_uuid(cv_id)

    row = await user_cv_service.get_cv(cv_uuid, to_uuid(user["id"]))
    if row is not None:
        for file_id in (row.raw_extraction_ref, row.pdf_file_id, row.thumbnail_file_id):
            if file_id:
                await file_service.delete_owned_file(str(user["id"]), file_id)

    await user_cv_service.delete_cv(cv_uuid, to_uuid(user["id"]))
    return {"success": True}


def _detect_image_media_type(data: bytes, fallback: str = "image/webp") -> str:
    if data.startswith(b"RIFF") and len(data) >= 12 and data[8:12] == b"WEBP":
        return "image/webp"
    if data.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    return fallback


@router.get("/user/cv/{cv_id}/thumbnail")
async def get_user_cv_thumbnail(
    cv_id: str,
    v: str | None = None,
    user: dict = Depends(get_current_user),
    file_service: FileService = Depends(get_file_service),
) -> Response:
    """Stream pre-rendered first-page thumbnail (WebP/JPEG) for a source CV.

    If the thumbnail has not been pre-rendered yet (e.g. existing CVs),
    lazily backfills it on the fly and writes through to storage and DB.
    """
    cv_uuid = parse_cv_uuid(cv_id)
    user_id = str(user["id"])
    row = await user_cv_service.get_cv(cv_uuid, to_uuid(user["id"]))
    if not row:
        raise HTTPException(status_code=404, detail="Không tìm thấy CV.")

    # Pasted-text CVs have no source PDF and therefore no thumbnail
    if not row.pdf_file_id:
        raise HTTPException(status_code=404, detail="CV không có file PDF.")

    # 1. If thumbnail already exists on the row, try downloading from storage
    if row.thumbnail_file_id:
        try:
            thumb_record = await file_service.repository.get_file_by_id(
                row.thumbnail_file_id
            )
            if thumb_record and str(thumb_record.get("user_id")) == user_id:
                data = await file_service.storage.download(
                    bucket=thumb_record["bucket"],
                    path=thumb_record["object_path"],
                )
                media_type = thumb_record.get(
                    "content_type"
                ) or _detect_image_media_type(data)
                return Response(
                    content=data,
                    media_type=media_type,
                    headers={
                        "Cache-Control": "private, max-age=86400, stale-while-revalidate=604800",
                    },
                )
        except Exception:
            _logger.warning(
                "Failed to download existing thumbnail for CV %s, falling back to regeneration.",
                cv_id,
                exc_info=True,
            )

    # 2. Lazy backfill: download source PDF and generate thumbnail on the fly
    try:
        pdf_record = await file_service.repository.get_file_by_id(row.pdf_file_id)
    except Exception:
        pdf_record = None

    if not pdf_record or str(pdf_record.get("user_id")) != user_id:
        raise HTTPException(status_code=404, detail="Không tìm thấy file PDF gốc.")

    try:
        pdf_bytes = await file_service.storage.download(
            bucket=pdf_record["bucket"],
            path=pdf_record["object_path"],
        )
    except Exception as exc:
        _logger.warning("Could not download source PDF for thumbnail: %s", exc)
        raise HTTPException(status_code=404, detail="Không thể đọc file PDF gốc.")

    thumb_bytes = generate_pdf_thumbnail(pdf_bytes)
    if not thumb_bytes:
        raise HTTPException(
            status_code=404, detail="Không thể tạo thumbnail từ file PDF."
        )

    media_type = _detect_image_media_type(thumb_bytes, "image/webp")
    ext = "webp" if media_type == "image/webp" else "jpg"

    # 3. Write-through: persist thumbnail file and update user_cvs row
    try:
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        thumb_filename = f"{timestamp}_{uuid4().hex[:8]}_thumb.{ext}"
        thumb_info = await file_service.upload_file(
            user_id=user_id,
            filename=thumb_filename,
            data=thumb_bytes,
            content_type=media_type,
            bucket="cv",
            include_url=False,
            original_filename=f"thumb_{row.cv_filename}.{ext}",
        )
        await user_cv_service.update_cv_thumbnail(
            cv_uuid,
            to_uuid(user["id"]),
            str(thumb_info["id"]),
        )
    except Exception as exc:
        _logger.warning(
            "Write-through thumbnail persistence failed (serving generated bytes anyway): %s",
            exc,
        )

    return Response(
        content=thumb_bytes,
        media_type=media_type,
        headers={
            "Cache-Control": "private, max-age=86400, stale-while-revalidate=604800",
        },
    )


@router.put("/user/cv/{cv_id}/structured-document")
async def save_structured_document(
    cv_id: str,
    req: StructuredDocumentSaveRequest,
    user: dict = Depends(get_current_user),
) -> dict:
    """Persist the review-wizard corrected document JSON for one source CV.

    Per-brick provenance is preserved: only bricks the wizard touched carry
    ``origin == USER_EDIT`` (stamped by the frontend); untouched bricks keep
    the extractor's ``EXTRACTED`` origin.
    """
    cv_uuid = parse_cv_uuid(cv_id)
    document = req.document.model_copy(deep=True)
    document = user_cv_service.mark_user_edited(document)
    updated_at = await user_cv_service.save_structured_document(
        cv_uuid, to_uuid(user["id"]), document.model_dump_json()
    )
    return {"success": True, "updated_at": updated_at}


@router.get("/user/cv/{cv_id}/structured-document")
async def get_structured_document(
    cv_id: str,
    user: dict = Depends(get_current_user),
) -> dict:
    """Return the saved wizard JSON for one source CV, or saved:null."""
    cv_uuid = parse_cv_uuid(cv_id)
    saved = await user_cv_service.get_structured_document(cv_uuid, to_uuid(user["id"]))
    return {"saved": saved}


@router.post("/user/feedback", response_model=FeedbackResponse)
async def submit_feedback(
    req: FeedbackSubmit,
    user: dict = Depends(get_current_user),
) -> FeedbackResponse:
    credits_rewarded, new_credits = await user_cv_service.submit_user_feedback(
        user_id=to_uuid(user["id"]),
        name=user.get("name"),
        avatar=user.get("image"),
        rating=req.rating,
        content=req.content,
    )
    msg = "Cảm ơn bạn đã gửi ý kiến phản hồi!"
    if credits_rewarded > 0:
        msg = f"Đóng góp thành công! Bạn nhận được +{credits_rewarded} credits cho lượt gửi đầu tiên."

    return FeedbackResponse(
        success=True,
        message=msg,
        credits_rewarded=credits_rewarded,
        new_credits=new_credits,
    )


@router.get("/feedbacks")
async def list_feedbacks() -> list:
    from app.core.db import Database

    rows = await Database.fetch_all(
        "SELECT id, name, avatar, rating, content, created_at FROM public.feedbacks WHERE is_public = TRUE ORDER BY created_at DESC",
    )
    return [dict(r) for r in rows]


@router.post("/user/tailored-cv/verify-edit", response_model=VerifyUserEditResponse)
async def verify_user_edit(
    req: VerifyUserEditRequest,
    user: dict = Depends(get_current_user),
) -> VerifyUserEditResponse:
    """Verify an edit against the signed current tailored document."""
    try:
        result = verify_and_rebind_user_edit(
            user_id=to_uuid(user["id"]),
            source_cv_text=req.source_cv_text,
            jd_text=req.jd_text,
            source_document=req.source_document_v2,
            current_tailored_document=req.current_tailored_document_v2,
            edited_document=req.edited_document_v2,
            diagnostics=req.tailoring_diagnostics,
            tailoring_entitlement=req.tailoring_entitlement,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invalid tailored CV edit") from exc

    return VerifyUserEditResponse(
        edited_document_v2=result.tailored_document,
        tailoring_diagnostics=result.diagnostics,
        tailoring_entitlement=result.tailoring_entitlement,
    )
