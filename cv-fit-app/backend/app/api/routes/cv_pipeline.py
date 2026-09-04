"""Decoupled LLM #1/#2/#3 CV pipeline endpoints.

These endpoints intentionally expose each stage separately so the frontend can
retain the canonical mapper output and show evaluation/tailoring provenance
without invoking the legacy monolithic ``/api/analyze-cv`` route.
"""

from __future__ import annotations

import logging
from contextlib import suppress
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, ConfigDict, Field

from app.dependencies import (
    get_current_user,
    get_file_service,
    refund_credits,
    reserve_credits,
)
from app.models.cv_document_v2 import CVDocumentV2
from app.models.cv_evaluation import LLMEvaluationReport
from app.models.cv_tailoring import TailoredCVResponse
from app.schemas.tailored_cv import CVDesign, TailoredCVVersionResponse
from app.services.client_request_service import (
    ClientDisconnectedError,
    await_while_client_connected,
)
from app.services.cv_evaluator_service import evaluate_cv_fit
from app.services.cv_pipeline_persistence_service import persist_pipeline_tailoring
from app.services.cv_structuring_service import (
    build_manual_text_extraction,
    structure_cv,
)
from app.services.cv_tailor_service import tailor_cv
from app.services.files import FileService
from app.services.layout_extraction import (
    raw_extraction_to_text,
    validate_raw_extraction,
)
from app.services.tailored_cv_metadata import (
    issue_pipeline_source_ticket,
    verify_pipeline_source_ticket,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/cv", tags=["cv-pipeline"])


async def _refund_reserved_credit(user_id: str, description: str) -> None:
    with suppress(Exception):
        await refund_credits(
            user_id=user_id,
            amount=1,
            tx_type="cv_analysis",
            description=description,
        )


class CVParseRequest(BaseModel):
    """Text plus an optional server-owned raw-extraction reference for LLM #1."""

    model_config = ConfigDict(extra="forbid")

    cv_text: str = Field(min_length=1)
    raw_extraction_ref_id: UUID | None = None


class CVEvaluateRequest(BaseModel):
    """Canonical mapper output and optional JD for LLM #2."""

    model_config = ConfigDict(extra="forbid")

    canonical_cv: dict[str, Any]
    job_description: str | None = None


class CVTailorRequest(BaseModel):
    """Canonical CV, optional JD, and optional LLM #2 report for LLM #3."""

    model_config = ConfigDict(extra="forbid")

    canonical_cv: dict[str, Any]
    job_description: str | None = None
    evaluation: LLMEvaluationReport | None = None


class CVTailorAndSaveRequest(BaseModel):
    """Persist a previously shown LLM #3 result as an exportable CV version."""

    model_config = ConfigDict(extra="forbid")

    cv_text: str = Field(min_length=1)
    raw_extraction_ref_id: UUID | None = None
    job_description: str | None = None
    source_document_v2: CVDocumentV2
    source_ticket: str = Field(min_length=1)
    tailoring: TailoredCVResponse
    selected_design: CVDesign = "classic_ats"


class CanonicalCVResponse(BaseModel):
    canonical_cv: dict[str, Any]
    source_document_v2: CVDocumentV2
    source_ticket: str


class CVEvaluationResponse(BaseModel):
    evaluation: LLMEvaluationReport


class CVTailoringResponse(BaseModel):
    tailoring: TailoredCVResponse


@router.post("/parse", response_model=CanonicalCVResponse)
async def parse_cv(
    payload: CVParseRequest,
    request: Request,
    user: dict = Depends(get_current_user),
    file_service: FileService = Depends(get_file_service),
) -> CanonicalCVResponse:
    """Run LLM #1 and return canonical CV JSON from authoritative source text."""
    if not payload.cv_text.strip():
        raise HTTPException(status_code=422, detail="Cần cung cấp nội dung CV.")

    await reserve_credits(
        user_id=user["id"],
        amount=1,
        tx_type="cv_analysis",
        description="Phân tích CV chi tiết",
    )

    try:
        result = await await_while_client_connected(
            request,
            structure_cv(
                cv_text=payload.cv_text,
                raw_extraction_ref_id=(
                    str(payload.raw_extraction_ref_id)
                    if payload.raw_extraction_ref_id
                    else None
                ),
                user_id=str(user["id"]),
                file_service=file_service,
            ),
        )
    except ClientDisconnectedError as exc:
        await _refund_reserved_credit(
            str(user["id"]),
            "Hoàn credit do client ngắt kết nối khi lập bản đồ CV",
        )
        raise HTTPException(status_code=499, detail=str(exc)) from exc
    except Exception as exc:
        logger.error("CV pipeline parse failed: error_type=%s", type(exc).__name__)
        await _refund_reserved_credit(
            str(user["id"]),
            "Hoàn credit do lỗi khi lập bản đồ CV",
        )
        raise
    # A deterministic fallback exists only to preserve source text for an
    # operator retry. It is not a semantic mapper result and must never flow
    # into evaluation, tailoring, or PDF export as though it were one.
    if result.used_fallback:
        await _refund_reserved_credit(
            str(user["id"]),
            "Hoàn credit do lập bản đồ CV dùng fallback tạm thời",
        )
        raise HTTPException(
            status_code=503,
            detail=(
                "Không thể lập bản đồ CV an toàn từ nguồn gốc. "
                "Hãy thử phân tích lại sau ít phút."
            ),
        )
    raw_ref_id = (
        str(payload.raw_extraction_ref_id) if payload.raw_extraction_ref_id else None
    )
    return CanonicalCVResponse(
        canonical_cv=result.document.to_canonical_dict(),
        source_document_v2=result.document,
        source_ticket=issue_pipeline_source_ticket(
            UUID(str(user["id"])),
            result.source_text,
            result.document,
            raw_ref_id,
        ),
    )


@router.post("/evaluate", response_model=CVEvaluationResponse)
async def evaluate_cv(
    payload: CVEvaluateRequest,
    request: Request,
    user: dict = Depends(get_current_user),
) -> CVEvaluationResponse:
    """Run LLM #2 in JOB_FIT or GENERAL_AUDIT mode."""
    del user  # Authentication is required because the payload contains CV PII.
    if not payload.canonical_cv:
        raise HTTPException(status_code=422, detail="canonical_cv is required.")
    try:
        result = await await_while_client_connected(
            request,
            evaluate_cv_fit(payload.canonical_cv, payload.job_description),
        )
    except ClientDisconnectedError as exc:
        raise HTTPException(status_code=499, detail=str(exc)) from exc
    return CVEvaluationResponse(evaluation=result.report)


@router.post("/tailor", response_model=CVTailoringResponse)
async def tailor_cv_endpoint(
    payload: CVTailorRequest,
    request: Request,
    user: dict = Depends(get_current_user),
) -> CVTailoringResponse:
    """Run LLM #3 and return the tailored canonical CV plus an auditable log."""
    del user  # Authentication is required because the payload contains CV PII.
    if not payload.canonical_cv:
        raise HTTPException(status_code=422, detail="canonical_cv is required.")
    try:
        result = await await_while_client_connected(
            request,
            tailor_cv(
                payload.canonical_cv,
                payload.job_description,
                payload.evaluation,
            ),
        )
    except ClientDisconnectedError as exc:
        raise HTTPException(status_code=499, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return CVTailoringResponse(tailoring=result.response)


@router.post("/tailor-and-save", response_model=TailoredCVVersionResponse)
async def tailor_and_save_cv(
    payload: CVTailorAndSaveRequest,
    user: dict = Depends(get_current_user),
    file_service: FileService = Depends(get_file_service),
) -> TailoredCVVersionResponse:
    """Validate LLM #3 changes against source blocks, then create an exportable version."""
    try:
        raw_ref_id = (
            str(payload.raw_extraction_ref_id)
            if payload.raw_extraction_ref_id
            else None
        )
        if raw_ref_id:
            raw_extraction = await file_service.load_raw_extraction(
                str(user["id"]), raw_ref_id
            )
            if raw_extraction is None:
                raise HTTPException(
                    status_code=404, detail="Raw extraction reference was not found."
                )
            validate_raw_extraction(raw_extraction)
            source_text = raw_extraction_to_text(raw_extraction)
        else:
            source_text = payload.cv_text.strip()
            raw_extraction = build_manual_text_extraction(source_text)
        analysis_key = verify_pipeline_source_ticket(
            payload.source_ticket,
            UUID(str(user["id"])),
            source_text,
            payload.source_document_v2,
            raw_ref_id,
        )
        return await persist_pipeline_tailoring(
            user_id=UUID(str(user["id"])),
            source_text=source_text,
            raw_extraction=raw_extraction,
            source_document=payload.source_document_v2,
            job_description=payload.job_description,
            tailoring=payload.tailoring,
            selected_design=payload.selected_design,
            analysis_key=analysis_key,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
