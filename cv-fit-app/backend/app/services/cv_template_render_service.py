"""Authoritative template renderer service for Phase 6.

Produces canonical HTML preview and PDF source documents from CVDocumentV2.
"""

import hashlib
from html import escape

from app.models.cv_document_v2 import (
    CVBlockType,
    CVBulletBlock,
    CVDocumentV2,
    CVEducationBlock,
    CVEntryBlock,
    CVParagraphBlock,
    CVPublicationBlock,
    CVSection,
    CVSkillGroupBlock,
    CVUnknownBlock,
)
from app.models.cv_template import CVRenderDiagnostics, CVRenderResult
from app.services.cv_language import CVLanguage
from app.services.cv_render_ledger import build_cv_render_ledger
from app.services.cv_render_validation import validate_static_html
from app.services.cv_rendering_diagnostics import (
    COMPACT_OVERFLOW_WARNING,
    compact_rendering_warnings,
)
from app.services.cv_template_placement import build_placement_manifest
from app.services.cv_template_registry import get_template_package, resolve_template_id


def render_cv_document(
    document: CVDocumentV2,
    template_id: str = "classic_ats",
    template_version: int | None = None,
    language: CVLanguage = "vi",
) -> CVRenderResult:
    """Render CVDocumentV2 into canonical HTML with strict data-field-id tags."""
    canonical_id = resolve_template_id(template_id)
    pkg = get_template_package(canonical_id, template_version)
    template_def = pkg.definition
    css_content = pkg.css_path.read_text(encoding="utf-8")

    ledger = build_cv_render_ledger(document)
    placement_manifest = build_placement_manifest(document, template_def)

    # Separate sections into layout slots
    main_sections: list[tuple[int, CVSection]] = []
    sidebar_sections: list[tuple[int, CVSection]] = []

    for idx, section in enumerate(document.sections):
        slot = placement_manifest.get_slot_for_section(section)
        if slot == "sidebar":
            sidebar_sections.append((idx, section))
        else:
            main_sections.append((idx, section))

    # Header section HTML
    header_html = _render_header_html(document)

    has_summary_section = any(
        section.type == "summary" for section in document.sections
    )
    summary_html = ""
    if not has_summary_section and document.summary and document.summary.text:
        summary_title = "Tóm tắt" if language == "vi" else "Profile"
        summary_html = (
            f'<div class="cv-section cv-summary" data-section-type="summary">'
            f'<h2 class="cv-section-title">{escape(summary_title)}</h2>'
            f'<p class="item-paragraph" data-field-id="summary:text" data-block-type="paragraph">{escape(document.summary.text)}</p>'
            f"</div>"
        )

    # Build layout HTML
    if template_def.layout == "sidebar":
        sidebar_inner = "".join(
            _render_section_html(sec_idx, section, document)
            for sec_idx, section in sidebar_sections
        )
        main_inner = summary_html + "".join(
            _render_section_html(sec_idx, section, document)
            for sec_idx, section in main_sections
        )

        body_content = (
            f"{header_html}"
            f'<div class="cv-layout-grid">'
            f'  <div class="cv-sidebar-col">{sidebar_inner}</div>'
            f'  <div class="cv-main-col">{main_inner}</div>'
            f"</div>"
        )
    else:
        sections_inner = "".join(
            _render_section_html(sec_idx, section, document)
            for sec_idx, section in main_sections
        )
        body_content = f"{header_html}{summary_html}{sections_inner}"

    compact_warnings = (
        compact_rendering_warnings(document) if canonical_id == "compact" else []
    )
    body_attr = (
        f' data-render-warning="{COMPACT_OVERFLOW_WARNING}"' if compact_warnings else ""
    )

    full_html = (
        f"<!DOCTYPE html>\n"
        f'<html lang="{escape(language)}">\n'
        f"<head>\n"
        f'  <meta charset="utf-8">\n'
        f'  <meta name="viewport" content="width=device-width, initial-scale=1.0">\n'
        f"  <title>{escape(document.identity.full_name or 'CV')}</title>\n"
        f"  <style>\n{css_content}\n</style>\n"
        f"</head>\n"
        f"<body{body_attr}>\n"
        f'  <div class="cv-container">\n'
        f"    {body_content}\n"
        f"  </div>\n"
        f"</body>\n"
        f"</html>"
    )

    render_hash = hashlib.sha256(full_html.encode("utf-8")).hexdigest()

    diagnostics = CVRenderDiagnostics(
        document_hash=ledger.document_hash,
        template_id=template_def.template_id,
        template_version=template_def.version,
        render_hash=render_hash,
        warnings=compact_warnings,
    )

    # Perform Tier 1 static HTML validation against ledger
    validate_static_html(full_html, ledger, diagnostics)

    return CVRenderResult(
        html=full_html,
        diagnostics=diagnostics,
        render_hash=render_hash,
    )


def _render_header_html(document: CVDocumentV2) -> str:
    parts: list[str] = ['<div class="cv-header">']
    if document.identity.full_name:
        parts.append(
            f'<h1 class="cv-name" data-field-id="identity:full_name">'
            f"{escape(document.identity.full_name)}"
            f"</h1>"
        )
    if document.identity.headline:
        parts.append(
            f'<div class="cv-headline" data-field-id="identity:headline">'
            f"{escape(document.identity.headline)}"
            f"</div>"
        )

    # Single projection for contact entries
    canonical_contacts = document.identity.canonical_contact_lines()
    contact_source = (
        canonical_contacts if canonical_contacts else document.identity.contact_lines
    )

    if contact_source:
        parts.append('<div class="cv-contacts">')
        for idx, contact_line in enumerate(contact_source):
            parts.append(
                f'<span class="cv-contact-item" data-field-id="contact:line:{idx}">'
                f"{escape(contact_line)}"
                f"</span>"
            )
        parts.append("</div>")

    parts.append("</div>")
    return "".join(parts)


def _render_section_html(
    sec_idx: int,
    section: CVSection,
    document: CVDocumentV2 | None = None,
) -> str:
    if section.type == "custom" and "unclassified" in (section.title or "").lower():
        return ""
    sec_key = f"section:{section.id if section.id else sec_idx}"
    parts: list[str] = [f'<div class="cv-section" data-section-type="{section.type}">']

    if section.title:
        parts.append(
            f'<h2 class="cv-section-title" data-field-id="{sec_key}:title">'
            f"{escape(section.title)}"
            f"</h2>"
        )

    if section.type == "summary":
        if document and document.summary and document.summary.text:
            parts.append(
                f'<p class="item-paragraph" data-field-id="summary:text" data-block-type="paragraph">{escape(document.summary.text)}</p>'
            )
        parts.append("</div>")
        return "".join(parts)

    for block_idx, block in enumerate(section.blocks):
        block_key = f"{sec_key}:block:{block_idx}"
        parts.append(_render_block_html(block_key, block))

    parts.append("</div>")
    return "".join(parts)


def _render_block_html(block_key: str, block: CVBlockType) -> str:
    conf_attr = (
        f' data-confidence="{block.confidence:.2f}"'
        if getattr(block, "confidence", None) is not None
        else ""
    )
    parts: list[str] = [
        f'<div class="cv-block" data-block-type="{block.type}"{conf_attr}>'
    ]

    if isinstance(block, CVEntryBlock):
        parts.append('<div class="entry-header">')
        if block.title:
            parts.append(
                f'<span class="entry-title" data-field-id="{block_key}:title">{escape(block.title)}</span>'
            )
        if block.date:
            parts.append(
                f'<span class="entry-meta" data-field-id="{block_key}:date">{escape(block.date)}</span>'
            )
        parts.append("</div>")

        if block.subtitle:
            parts.append(
                f'<div class="entry-subtitle" data-field-id="{block_key}:subtitle">{escape(block.subtitle)}</div>'
            )

        meta_parts: list[str] = []
        if block.organization:
            meta_parts.append(
                f'<span data-field-id="{block_key}:organization">{escape(block.organization)}</span>'
            )
        if block.location:
            meta_parts.append(
                f'<span data-field-id="{block_key}:location">{escape(block.location)}</span>'
            )

        if meta_parts:
            parts.append(f'<div class="entry-meta">{" · ".join(meta_parts)}</div>')

        if block.bullets:
            parts.append('<ul class="bullet-list">')
            for bullet_idx, bullet in enumerate(block.bullets):
                parts.append(
                    f'<li class="bullet-item" data-field-id="{block_key}:bullet:{bullet_idx}">'
                    f"{escape(bullet)}"
                    f"</li>"
                )
            parts.append("</ul>")

    elif isinstance(block, CVBulletBlock):
        if block.text:
            parts.append(
                f'<p class="bullet-item" data-field-id="{block_key}:text">{escape(block.text)}</p>'
            )

    elif isinstance(block, CVParagraphBlock):
        if block.text:
            parts.append(
                f'<p class="item-paragraph" data-field-id="{block_key}:text">{escape(block.text)}</p>'
            )

    elif isinstance(block, CVSkillGroupBlock):
        parts.append('<div class="skills-group">')
        if block.label:
            parts.append(
                f'<span class="skills-label" data-field-id="{block_key}:label">{escape(block.label)}</span>'
            )
            if block.skills:
                parts.append(": ")
        if block.skills:
            skill_spans = [
                f'<span data-field-id="{block_key}:skill:{skill_idx}">{escape(skill)}</span>'
                for skill_idx, skill in enumerate(block.skills)
            ]
            parts.append(f'<div class="skills-list">{" · ".join(skill_spans)}</div>')
        parts.append("</div>")

    elif isinstance(block, CVPublicationBlock):
        if block.title:
            parts.append(
                f'<div class="entry-title" data-field-id="{block_key}:title">{escape(block.title)}</div>'
            )
        if block.authors:
            parts.append(
                f'<div class="entry-subtitle" data-field-id="{block_key}:authors">{escape(block.authors)}</div>'
            )

        pub_meta: list[str] = []
        if block.venue:
            pub_meta.append(
                f'<span data-field-id="{block_key}:venue">{escape(block.venue)}</span>'
            )
        if block.date:
            pub_meta.append(
                f'<span data-field-id="{block_key}:date">{escape(block.date)}</span>'
            )
        if block.status:
            pub_meta.append(
                f'<span data-field-id="{block_key}:status">{escape(block.status)}</span>'
            )
        if pub_meta:
            parts.append(f'<div class="entry-meta">{" · ".join(pub_meta)}</div>')

    elif isinstance(block, CVEducationBlock):
        parts.append('<div class="entry-header">')
        if block.institution:
            parts.append(
                f'<span class="entry-title" data-field-id="{block_key}:institution">{escape(block.institution)}</span>'
            )
        if block.date:
            parts.append(
                f'<span class="entry-meta" data-field-id="{block_key}:date">{escape(block.date)}</span>'
            )
        parts.append("</div>")

        deg_parts: list[str] = []
        if block.degree:
            deg_parts.append(
                f'<span data-field-id="{block_key}:degree">{escape(block.degree)}</span>'
            )
        if block.field:
            deg_parts.append(
                f'<span data-field-id="{block_key}:field">{escape(block.field)}</span>'
            )
        if deg_parts:
            parts.append(f'<div class="entry-subtitle">{" — ".join(deg_parts)}</div>')

        if block.location:
            parts.append(
                f'<div class="entry-meta"><span data-field-id="{block_key}:location">{escape(block.location)}</span></div>'
            )

        for detail_idx, detail in enumerate(block.details):
            parts.append(
                f'<p class="item-paragraph" data-field-id="{block_key}:detail:{detail_idx}">'
                f"{escape(detail)}"
                f"</p>"
            )

    elif isinstance(block, CVUnknownBlock):
        for line_idx, line in enumerate(block.lines):
            parts.append(
                f'<p class="item-paragraph" data-field-id="{block_key}:line:{line_idx}">'
                f"{escape(line)}"
                f"</p>"
            )

    parts.append("</div>")
    return "".join(parts)
