"""Lossless server-owned layout artifact for the next CV mapper generation."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class _LayoutModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class LayoutWordV1(_LayoutModel):
    word_id: str
    text: str = Field(min_length=1)
    bbox: tuple[float, float, float, float]
    span_ids: list[str] = Field(min_length=1)


class SourceSpanV1(_LayoutModel):
    """Exact PyMuPDF span, including whitespace and styling metadata."""

    span_id: str
    line_id: str
    text: str = Field(min_length=1)
    bbox: tuple[float, float, float, float]
    font: str | None = None
    font_size: float | None = Field(default=None, ge=0.0)
    flags: int | None = None


class LayoutLineV1(_LayoutModel):
    line_id: str
    page: int = Field(ge=1)
    bbox: tuple[float, float, float, float]
    text: str = Field(min_length=1)
    span_ids: list[str] = Field(min_length=1)
    word_ids: list[str] = Field(default_factory=list)
    is_bullet: bool = False


class LayoutPageV1(_LayoutModel):
    page: int = Field(ge=1)
    width: float = Field(gt=0)
    height: float = Field(gt=0)
    lines: list[LayoutLineV1] = Field(default_factory=list)


class LayoutDocumentV1(_LayoutModel):
    version: str = "layout-document-1.0"
    pages: list[LayoutPageV1] = Field(default_factory=list)
    spans: list[SourceSpanV1] = Field(default_factory=list)
    words: list[LayoutWordV1] = Field(default_factory=list)


class VisualRowV1(_LayoutModel):
    row_id: str
    page: int = Field(ge=1)
    bbox: tuple[float, float, float, float]
    line_ids: list[str] = Field(min_length=1)


class VisualBulletGroupV1(_LayoutModel):
    line_ids: list[str] = Field(min_length=1)
    span_ids: list[str] = Field(min_length=1)


class VisualRecordV1(_LayoutModel):
    record_id: str
    section_type: str
    header_row_ids: list[str] = Field(min_length=1)
    header_line_ids: list[str] = Field(min_length=1)
    header_span_ids: list[str] = Field(min_length=1)
    bullet_groups: list[VisualBulletGroupV1] = Field(default_factory=list)


class VisualSectionV1(_LayoutModel):
    section_id: str
    type: str
    heading_line_id: str
    heading_span_ids: list[str] = Field(min_length=1)
    records: list[VisualRecordV1] = Field(default_factory=list)
    residual_line_ids: list[str] = Field(default_factory=list)
    residual_span_ids: list[str] = Field(default_factory=list)


class VisualDocumentV1(_LayoutModel):
    rows: list[VisualRowV1] = Field(default_factory=list)
    sections: list[VisualSectionV1] = Field(default_factory=list)
    preamble_line_ids: list[str] = Field(default_factory=list)
    preamble_span_ids: list[str] = Field(default_factory=list)


class LayoutConservationAudit(_LayoutModel):
    source_span_count: int
    assigned_span_count: int
    missing_span_ids: list[str] = Field(default_factory=list)
    duplicate_span_ids: list[str] = Field(default_factory=list)

    @property
    def passes(self) -> bool:
        return not self.missing_span_ids and not self.duplicate_span_ids
