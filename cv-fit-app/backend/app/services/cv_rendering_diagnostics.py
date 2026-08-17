"""Rendering diagnostics for Phase 6 template layouts."""

from app.models.cv_document_v2 import CVDocumentV2

COMPACT_ONE_PAGE_LINE_BUDGET = 62
COMPACT_OVERFLOW_WARNING = "compact_template_content_exceeds_one_page"


def compact_rendering_warnings(document: CVDocumentV2) -> list[str]:
    """Report when compact design will paginate across multiple pages."""
    estimated_lines = _estimated_render_lines(document)
    return (
        [COMPACT_OVERFLOW_WARNING]
        if estimated_lines > COMPACT_ONE_PAGE_LINE_BUDGET
        else []
    )


def _estimated_render_lines(document: CVDocumentV2) -> int:
    contacts = (
        document.identity.canonical_contact_lines() or document.identity.contact_lines
    )
    lines = 2 + len(contacts)
    if document.summary is not None and document.summary.text:
        lines += 2 + max(1, len(document.summary.text) // 80)
    for section in document.sections:
        lines += 2
        for block in section.blocks:
            bullets = getattr(block, "bullets", [])
            lines += sum(max(1, len(b) // 80) for b in bullets)
            details = getattr(block, "details", [])
            lines += sum(max(1, len(d) // 80) for d in details)
            text_str = str(getattr(block, "text", getattr(block, "title", "")))
            if text_str:
                lines += max(1, len(text_str) // 80)
    return lines
