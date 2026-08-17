"""Models for Phase 6 versioned template definitions and render diagnostics."""

from typing import Literal

from pydantic import BaseModel, Field

CURRENT_RENDER_VERSION = 1


class CVTemplateDefinition(BaseModel):
    """Server-owned immutable template metadata definition."""

    template_id: str
    version: int
    label: str
    description: str
    layout: Literal["single_column", "sidebar"]
    ats_friendly: bool
    supports_multipage: bool = True


class CVRenderDiagnostics(BaseModel):
    """Response-only server-generated render diagnostics and validation audit log."""

    render_version: int = CURRENT_RENDER_VERSION
    document_hash: str
    template_id: str
    template_version: int
    render_hash: str
    page_count: int | None = None
    warnings: list[str] = Field(default_factory=list)
    missing_field_ids: list[str] = Field(default_factory=list)
    duplicate_field_ids: list[str] = Field(default_factory=list)
    mismatched_field_ids: list[str] = Field(default_factory=list)
    clipped_field_ids: list[str] = Field(default_factory=list)
    overlapping_field_ids: list[str] = Field(default_factory=list)
    is_valid: bool = True


class CVRenderResult(BaseModel):
    """Result of deterministic HTML template rendering."""

    html: str
    diagnostics: CVRenderDiagnostics
    render_hash: str
