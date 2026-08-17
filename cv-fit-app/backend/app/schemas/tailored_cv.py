from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.cv_document_v2 import CVDocumentV2, CVTailoringDiagnostics
from app.models.cv_template import CVRenderDiagnostics
from app.models.domain import SuggestedEdit, TailoredCV
from app.services.cv_language import CVLanguage

CVDesign = Literal["classic_ats", "modern_professional", "compact_one_page", "compact"]


class TailoredCVVersionCreate(BaseModel):
    tailored_cv: TailoredCV
    source_cv_text: str = Field(..., min_length=1)
    suggested_edits: list[SuggestedEdit] = Field(default_factory=list)
    jd_text: str = ""
    target_role: str | None = None
    company_name: str | None = None
    selected_design: CVDesign = "classic_ats"
    template_id: str | None = None
    tailoring_entitlement: str = Field(..., min_length=65)
    # V2/V3 fields (optional — backward compatible)
    document_v2: CVDocumentV2 | None = None
    source_document_v2: CVDocumentV2 | None = None
    tailoring_diagnostics: CVTailoringDiagnostics | None = None


class TailoredCVVersionUpdate(BaseModel):
    selected_design: CVDesign | None = None
    template_id: str | None = None


class TailoredCVTemplateUpdateRequest(BaseModel):
    """Server-authoritative template selection request."""

    template_id: str = Field(..., min_length=1)


class CVPreviewResponse(BaseModel):
    """Typed server-rendered preview payload."""

    html: str
    diagnostics: CVRenderDiagnostics
    render_hash: str


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
    tailoring_diagnostics: CVTailoringDiagnostics | None = None
    source_pdf_reference: str | None = None
    selected_design: CVDesign
    template_id: str | None = None
    template_version: int | None = None
    render_version: int | None = None
    last_render_diagnostics: CVRenderDiagnostics | None = None
    # Schema versioning metadata
    document_schema_version: int = 1
    reconstruction_version: int = 1
    tailoring_pipeline_version: int = 1
    reconstruction_status: Literal["current", "outdated"] = "current"
    source_hash: str | None = None
    jd_hash: str | None = None
    reconstruction_warnings: list[str] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime


class TailoredCVVersionListResponse(BaseModel):
    versions: list[TailoredCVVersionResponse]


class VerifyUserEditRequest(BaseModel):
    source_cv_text: str = Field(..., min_length=1)
    jd_text: str = ""
    source_document_v2: CVDocumentV2
    current_tailored_document_v2: CVDocumentV2
    edited_document_v2: CVDocumentV2
    tailoring_diagnostics: CVTailoringDiagnostics
    tailoring_entitlement: str = Field(..., min_length=65)


class VerifyUserEditResponse(BaseModel):
    edited_document_v2: CVDocumentV2
    tailoring_diagnostics: CVTailoringDiagnostics
    tailoring_entitlement: str
