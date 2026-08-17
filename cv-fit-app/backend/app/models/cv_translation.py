"""Pydantic data models for Phase 7 Evidence-Constrained CV Translation Variants."""

from datetime import datetime
from typing import Literal
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

from app.models.cv_document_v2 import CVDocumentV2


class CVTranslationOperation(BaseModel):
    """Proposed translation for a single semantic field."""

    field_id: str
    source_value_hash: str
    translated_value: str
    target_language: Literal["vi", "en"]


class CVTranslationDecision(BaseModel):
    """Per-field translation outcome record."""

    field_id: str
    status: Literal["translated", "preserved", "rejected"]
    reason_codes: list[str] = Field(default_factory=list)
    source_value_hash: str
    translated_value_hash: str


class CVTranslationDiagnostics(BaseModel):
    """Validation diagnostics for a full document translation variant."""

    translation_version: int = 1
    source_document_hash: str
    translated_document_hash: str
    source_language: str
    target_language: Literal["vi", "en"]
    translated_count: int = 0
    preserved_count: int = 0
    rejected_count: int = 0
    decisions: list[CVTranslationDecision] = Field(default_factory=list)
    is_valid: bool = False


class CVTranslationVariant(BaseModel):
    """Persisted translation variant linked to a tailored CV version."""

    id: UUID = Field(default_factory=uuid4)
    user_id: UUID
    tailored_cv_version_id: UUID
    source_document_hash: str
    translated_document_hash: str
    source_language: str
    target_language: Literal["vi", "en"]
    translation_version: int = 1
    translator_version: str = "v1_llm_constrained"
    status: Literal["pending", "running", "completed", "failed", "cancelled"] = (
        "completed"
    )
    operation_id: str
    translated_document: CVDocumentV2
    diagnostics: CVTranslationDiagnostics
    created_at: datetime | None = None
    updated_at: datetime | None = None
