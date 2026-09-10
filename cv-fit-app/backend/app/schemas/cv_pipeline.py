"""Pydantic request and response schemas for the decoupled CV pipeline endpoints."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.cv_document_v2 import CVDocumentV2
from app.models.cv_evaluation import LLMEvaluationReport
from app.models.cv_tailoring import TailoredCVResponse
from app.schemas.tailored_cv import CVDesign


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


class CVPrefillRequest(BaseModel):
    """Text plus optional raw reference for deterministic (LLM-free) prefill."""

    model_config = ConfigDict(extra="forbid")

    cv_text: str = Field(min_length=1)
    raw_extraction_ref_id: UUID | None = None
    cv_id: UUID | None = None


class CVPrefillResponse(BaseModel):
    prefill_document_v2: CVDocumentV2
    warnings: list[str] = Field(default_factory=list)
    auto_persisted: bool = False


class CVSourceTicketRequest(BaseModel):
    """Mint a tailor-and-save ticket for a wizard-saved document."""

    model_config = ConfigDict(extra="forbid")

    cv_text: str = Field(min_length=1)
    source_document_v2: CVDocumentV2
    raw_extraction_ref_id: UUID | None = None


class CVSourceTicketResponse(BaseModel):
    source_ticket: str
    canonical_cv: dict[str, Any]


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
    source_cv_id: UUID | None = None


class CanonicalCVResponse(BaseModel):
    canonical_cv: dict[str, Any]
    source_document_v2: CVDocumentV2
    source_ticket: str


class CVEvaluationResponse(BaseModel):
    evaluation: LLMEvaluationReport


class CVTailoringResponse(BaseModel):
    tailoring: TailoredCVResponse
