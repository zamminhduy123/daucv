"""Pydantic schemas for CV translation endpoints."""

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field

from app.models.cv_document_v2 import CVDocumentV2
from app.models.cv_translation import CVTranslationDiagnostics


class CVTranslationRequest(BaseModel):
    """Payload for creating a CV translation variant."""

    target_language: Literal["vi", "en"] = Field(
        ...,
        description="Target language code for the translation variant (vi or en).",
    )


class CVTranslationVariantResponse(BaseModel):
    """Response model for a CV translation variant."""

    id: UUID
    user_id: UUID
    tailored_cv_version_id: UUID
    source_document_hash: str
    translated_document_hash: str
    source_language: str
    target_language: str
    translation_version: int = 1
    translator_version: str = "v1_llm_constrained"
    status: Literal["pending", "completed", "failed"]
    operation_id: str
    translated_document: CVDocumentV2
    diagnostics: CVTranslationDiagnostics
    created_at: datetime
    updated_at: datetime


class CVTranslationListResponse(BaseModel):
    """List response for translation variants."""

    translations: list[CVTranslationVariantResponse]
