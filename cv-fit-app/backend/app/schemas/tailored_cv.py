from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.cv_document_v2 import CVDocumentV2
from app.models.domain import SuggestedEdit, TailoredCV
from app.services.cv_language import CVLanguage

CVDesign = Literal["classic_ats", "modern_professional", "compact_one_page"]


class TailoredCVVersionCreate(BaseModel):
    tailored_cv: TailoredCV
    source_cv_text: str = Field(..., min_length=1)
    suggested_edits: list[SuggestedEdit] = Field(default_factory=list)
    jd_text: str = ""
    target_role: str | None = None
    company_name: str | None = None
    selected_design: CVDesign = "classic_ats"
    tailoring_entitlement: str = Field(..., min_length=65)
    # V2 fields (optional — backward compatible)
    document_v2: CVDocumentV2 | None = None
    source_document_v2: CVDocumentV2 | None = None


class TailoredCVVersionUpdate(BaseModel):
    selected_design: CVDesign


class TailoredCVVersionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    source_cv_id: UUID | None = None
    target_role: str | None = None
    company_name: str | None = None
    jd_text: str
    # Legacy V1 document (still required for backward compatibility)
    tailored_cv: TailoredCV
    source_language: CVLanguage = "vi"
    # V2 typed document (nullable for legacy records)
    document_v2: CVDocumentV2 | None = None
    source_document_v2: CVDocumentV2 | None = None
    source_pdf_reference: str | None = None
    selected_design: CVDesign
    # Schema versioning metadata
    document_schema_version: int = 1
    reconstruction_version: int = 1
    source_hash: str | None = None
    jd_hash: str | None = None
    reconstruction_warnings: list[str] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime


class TailoredCVVersionListResponse(BaseModel):
    versions: list[TailoredCVVersionResponse]
