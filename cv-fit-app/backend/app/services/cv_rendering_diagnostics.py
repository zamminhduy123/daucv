"""Content-neutral rendering diagnostics for typed CV documents."""

from app.models.cv_document_v2 import (
    CVDocumentV2,
    CVEducationBlock,
    CVEntryBlock,
    CVParagraphBlock,
    CVPublicationBlock,
    CVSkillGroupBlock,
    CVUnknownBlock,
)

COMPACT_ONE_PAGE_LINE_BUDGET = 62
COMPACT_OVERFLOW_WARNING = "compact_template_content_exceeds_one_page"


def compact_rendering_warnings(document: CVDocumentV2) -> list[str]:
    """Report when the compact design should paginate instead of hiding content."""
    return (
        [COMPACT_OVERFLOW_WARNING]
        if _estimated_render_lines(document) > COMPACT_ONE_PAGE_LINE_BUDGET
        else []
    )


def _estimated_render_lines(document: CVDocumentV2) -> int:
    lines = 2 + len(document.identity.contact_lines)
    if document.summary is not None:
        lines += 2 + _wrapped_lines(document.summary.text)
    for section in document.sections:
        lines += 2
        for block in section.blocks:
            if isinstance(block, CVEntryBlock):
                lines += 1 + bool(block.subtitle or block.organization)
                lines += bool(block.location or block.date)
                lines += sum(_wrapped_lines(bullet) for bullet in block.bullets)
            elif isinstance(block, CVSkillGroupBlock):
                lines += _wrapped_lines(", ".join(block.skills), width=72)
            elif isinstance(block, CVPublicationBlock):
                lines += _wrapped_lines(
                    " ".join(
                        value
                        for value in (
                            block.authors,
                            block.title,
                            block.venue,
                            block.date,
                            block.status,
                        )
                        if value
                    ),
                )
            elif isinstance(block, CVEducationBlock):
                lines += 2 + sum(_wrapped_lines(item) for item in block.details)
            elif isinstance(block, CVUnknownBlock):
                lines += sum(_wrapped_lines(item) for item in block.lines)
            elif isinstance(block, CVParagraphBlock):
                lines += _wrapped_lines(block.text)
            else:
                lines += _wrapped_lines(block.text)
    return int(lines)


def _wrapped_lines(text: str, *, width: int = 88) -> int:
    return max(1, (len(text.strip()) + width - 1) // width)
