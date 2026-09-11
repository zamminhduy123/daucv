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


# Client-supplied typography ranges mirror the review/export UI controls.
_BASE_FONT_RANGE = (8.0, 13.0)
_LINE_HEIGHT_RANGE = (1.0, 1.8)
_SECTION_SPACING_RANGE = (0.0, 10.0)
_ITEM_SPACING_RANGE = (0.0, 8.0)
_PAGE_MARGIN_RANGE = (0.0, 20.0)

_ALLOWED_FONT_FAMILIES = {
    "times new roman": '"Times New Roman", Times, "Liberation Serif", Georgia, serif',
    "inter": 'Inter, -apple-system, "Segoe UI", Roboto, sans-serif',
    "roboto": 'Roboto, -apple-system, "Segoe UI", sans-serif',
    "georgia": 'Georgia, "Times New Roman", serif',
    "merriweather": 'Merriweather, Georgia, "Times New Roman", serif',
    "arial": "Arial, Helvetica, sans-serif",
}


def _clamp(value: float | None, bounds: tuple[float, float]) -> float | None:
    if value is None:
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if number != number:  # NaN
        return None
    return min(bounds[1], max(bounds[0], number))


class CVTypographyOverride(BaseModel):
    """Optional per-export typography tuning from the export screen.

    Every field is optional; unset fields keep template defaults so a
    missing override reproduces today's output byte-for-byte. Values are
    clamped to the UI ranges and the font family is whitelist-mapped, so
    hostile query strings cannot inject CSS or break layout validation.
    """

    base_font_size: float | None = Field(default=None)
    line_height: float | None = Field(default=None)
    section_spacing: float | None = Field(default=None)
    item_spacing: float | None = Field(default=None)
    page_margin: float | None = Field(default=None)
    font_family: str | None = Field(default=None)

    def sanitized(self) -> "CVTypographyOverride":
        family: str | None = None
        if self.font_family:
            key = self.font_family.strip().strip("\"'").lower()
            family = _ALLOWED_FONT_FAMILIES.get(key)
        return CVTypographyOverride(
            base_font_size=_clamp(self.base_font_size, _BASE_FONT_RANGE),
            line_height=_clamp(self.line_height, _LINE_HEIGHT_RANGE),
            section_spacing=_clamp(self.section_spacing, _SECTION_SPACING_RANGE),
            item_spacing=_clamp(self.item_spacing, _ITEM_SPACING_RANGE),
            page_margin=_clamp(self.page_margin, _PAGE_MARGIN_RANGE),
            font_family=family,
        )

    @property
    def is_empty(self) -> bool:
        return all(
            value is None
            for value in (
                self.base_font_size,
                self.line_height,
                self.section_spacing,
                self.item_spacing,
                self.page_margin,
                self.font_family,
            )
        )

    def to_override_css(self) -> str:
        """Build an override stylesheet appended after the template CSS.

        Proportional scale factors (2.1/1.15/1.2/1.0/0.92) mirror the
        frontend preview engine, so 9.5pt reproduces template defaults.
        """
        if self.is_empty:
            return ""
        rules: list[str] = []
        if self.font_family:
            rules.append(f"body {{ font-family: {self.font_family} !important; }}")
        if self.base_font_size is not None:
            base = self.base_font_size
            rules.append(f"body {{ font-size: {base:.1f}pt !important; }}")
            rules.append(f".cv-name {{ font-size: {base * 2.1:.1f}pt !important; }}")
            rules.append(
                f".cv-headline {{ font-size: {base * 1.15:.1f}pt !important; }}"
            )
            rules.append(
                f".cv-section-title {{ font-size: {base * 1.2:.1f}pt !important; }}"
            )
            rules.append(
                f".entry-title, .entry-subtitle, .entry-meta, .entry-date, .entry-location"
                f" {{ font-size: {base:.1f}pt !important; }}"
            )
            rules.append(
                f".bullet-item, .skills-group, .pub-row, .item-paragraph, .edu-detail"
                f" {{ font-size: {base:.1f}pt !important; }}"
            )
            rules.append(
                f".cv-contacts {{ font-size: {base * 0.92:.1f}pt !important; }}"
            )
        if self.line_height is not None:
            lh = self.line_height
            rules.append(
                f"body, .bullet-item, .skills-group, .pub-row, .item-paragraph, "
                f".entry-row-1, .entry-row-2, .edu-detail"
                f" {{ line-height: {lh:.2f} !important; }}"
            )
        if self.section_spacing is not None:
            gap = self.section_spacing
            rules.append(
                f".cv-section, .cv-summary {{ margin-bottom: {gap:.1f}mm !important; }}"
            )
        if self.item_spacing is not None:
            gap = self.item_spacing
            rules.append(
                f".cv-block, .skills-group, .pub-row, .bullet-list, .education-details"
                f" {{ margin-bottom: {gap:.1f}mm !important; }}"
            )
        if self.page_margin is not None:
            margin = self.page_margin
            rules.append(f"@page {{ margin: {margin:.0f}mm !important; }}")
            rules.append(
                f".cv-container {{ padding: {margin:.0f}mm {margin:.0f}mm !important; }}"
            )
        return "<style>\n" + "\n".join(rules) + "\n</style>"
