"""Typed CV HTML/PDF rendering shared by V2 and adapted V1 documents."""

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
from app.models.domain import TailoredCV
from app.schemas.tailored_cv import CVDesign
from app.services.cv_language import CVLanguage, detect_tailored_cv_language
from app.services.cv_rendering_diagnostics import (
    COMPACT_OVERFLOW_WARNING,
    compact_rendering_warnings,
)
from app.services.cv_v1_adapter import v1_to_v2


def _block_html(block: CVBlockType) -> str:
    """Render one block using only its explicit semantic type."""
    attributes = (
        f'data-block-type="{block.type}" data-confidence="{block.confidence:.2f}"'
    )
    if block.confidence < 0.8 and not isinstance(
        block,
        (CVBulletBlock, CVParagraphBlock, CVUnknownBlock),
    ):
        return f'<div class="neutral-block" {attributes}>{_neutral_block_html(block)}</div>'

    if isinstance(block, CVEntryBlock):
        parts = [f'<p class="entry-title">{escape(block.title)}</p>']
        if block.subtitle:
            parts.append(f'<p class="entry-subtitle">{escape(block.subtitle)}</p>')
        metadata = " · ".join(
            escape(value)
            for value in (block.organization, block.location, block.date)
            if value
        )
        if metadata:
            parts.append(f'<p class="entry-meta">{metadata}</p>')
        parts.extend(
            f'<p class="bullet">{escape(bullet)}</p>' for bullet in block.bullets
        )
        return f"<div {attributes}>{''.join(parts)}</div>"

    if isinstance(block, CVBulletBlock):
        return f'<p class="bullet" {attributes}>{escape(block.text)}</p>'
    if isinstance(block, CVParagraphBlock):
        return f'<p class="item" {attributes}>{escape(block.text)}</p>'
    if isinstance(block, CVSkillGroupBlock):
        label = (
            f'<p class="entry-title">{escape(block.label)}</p>' if block.label else ""
        )
        skills = " · ".join(escape(skill) for skill in block.skills)
        return f'<div {attributes}>{label}<p class="skills">{skills}</p></div>'
    if isinstance(block, CVPublicationBlock):
        parts = [f'<p class="publication">{escape(block.title)}</p>']
        if block.authors:
            parts.append(f'<p class="item">{escape(block.authors)}</p>')
        metadata = " · ".join(
            escape(value) for value in (block.venue, block.date, block.status) if value
        )
        if metadata:
            parts.append(f'<p class="item">{metadata}</p>')
        return f"<div {attributes}>{''.join(parts)}</div>"
    if isinstance(block, CVEducationBlock):
        parts = []
        if block.institution:
            parts.append(f'<p class="entry-title">{escape(block.institution)}</p>')
        degree = " — ".join(
            escape(value) for value in (block.degree, block.field) if value
        )
        if degree:
            parts.append(f'<p class="entry-subtitle">{degree}</p>')
        metadata = " · ".join(
            escape(value) for value in (block.location, block.date) if value
        )
        if metadata:
            parts.append(f'<p class="entry-meta">{metadata}</p>')
        parts.extend(f'<p class="item">{escape(item)}</p>' for item in block.details)
        return f"<div {attributes}>{''.join(parts)}</div>"
    if isinstance(block, CVUnknownBlock):
        text = " | ".join(block.lines)
        return f'<p class="item unknown" {attributes}>{escape(text)}</p>'
    return ""


def _neutral_block_html(block: CVBlockType) -> str:
    values: list[str] = []
    for name in (
        "title",
        "subtitle",
        "organization",
        "location",
        "date",
        "text",
        "label",
        "authors",
        "venue",
        "status",
        "institution",
        "degree",
        "field",
    ):
        value = getattr(block, name, None)
        if isinstance(value, str) and value:
            values.append(value)
    for name in ("bullets", "skills", "details", "lines"):
        value = getattr(block, name, None)
        if isinstance(value, list):
            values.extend(str(item) for item in value)
    return f'<p class="item">{escape(" | ".join(values))}</p>'


def _section_html(section: CVSection) -> str:
    blocks = "".join(_block_html(block) for block in section.blocks)
    return f'<section data-section-type="{section.type}"><h2>{escape(section.title)}</h2>{blocks}</section>'


def _render_v2_html(
    document: CVDocumentV2,
    design: CVDesign,
    language: CVLanguage,
) -> str:
    contacts = " · ".join(escape(line) for line in document.identity.contact_lines)
    profile_label = "Tóm tắt" if language == "vi" else "Profile"
    contact_label = "Liên hệ" if language == "vi" else "Contact"
    summary = (
        f"<section><h2>{profile_label}</h2>{_block_html(document.summary)}</section>"
        if document.summary
        else ""
    )
    sections = [section for section in document.sections if section.type != "summary"]
    header = (
        f"<header><h1>{escape(document.identity.name or 'CV')}</h1>"
        f"<h3>{escape(document.identity.headline)}</h3>"
        f'<p class="contacts">{contacts}</p></header>'
    )

    if design == "modern_professional":
        sidebar = [s for s in sections if s.type in {"skills", "education"}]
        main = [s for s in sections if s.type not in {"skills", "education"}]
        body = (
            f"<aside>{header}<section><h2>{contact_label}</h2>"
            f'<p class="item">{contacts}</p></section>'
            f"{''.join(_section_html(section) for section in sidebar)}</aside>"
            f"<main>{summary}{''.join(_section_html(section) for section in main)}</main>"
        )
        header = ""
    else:
        body = f"{summary}{''.join(_section_html(section) for section in sections)}"

    return (
        '<!doctype html><html><head><meta charset="utf-8">'
        f"<style>{_CSS}</style></head><body>"
        f'<article class="{design}">{header}{body}</article></body></html>'
    )


_CSS = """
@page { size: A4; margin: 0; } * { box-sizing: border-box; }
body { margin: 0; color: #263b3b; font-family: Arial, sans-serif; }
article { width: 210mm; min-height: 297mm; background: white; padding: 16mm; }
header { border-bottom: 1px solid #9ca3af; padding-bottom: 5mm; }
h1 { margin: 0 0 1mm; font-size: 24pt; } h3 { margin: 0 0 3mm; font-size: 11pt; }
.contacts { color: #596565; font-size: 8.5pt; }
section { margin-top: 6mm; break-inside: avoid; }
h2 { margin: 0 0 2.5mm; border-bottom: 1px solid #9ca3af; padding-bottom: 1mm; font-size: 10pt; text-transform: uppercase; letter-spacing: 1.2px; }
.item, .bullet, .entry-title, .entry-subtitle, .entry-meta { margin: 0 0 1.5mm; font-size: 9pt; line-height: 1.45; white-space: pre-wrap; }
.entry-title { font-weight: 700; } .entry-subtitle, .entry-meta { color: #555; }
.bullet { padding-left: 4mm; } .bullet::before { content: '\\2022'; margin-left: -3mm; margin-right: 2mm; }
.skills { font-size: 8.5pt; color: #333; } .publication { font-size: 9pt; font-style: italic; }
.unknown, .neutral-block { font-weight: 400; font-style: normal; }
.classic_ats { font-family: Georgia, 'Times New Roman', serif; }
.compact_one_page { border-top: 1.5mm solid #4A90A4; padding: 10mm 13mm; }
.compact_one_page section { margin-top: 3.5mm; }
.compact_one_page h2 { border: 0; border-left: 1mm solid #4A90A4; padding-left: 2mm; }
.compact_one_page .item, .compact_one_page .bullet, .compact_one_page .entry-title,
.compact_one_page .entry-subtitle, .compact_one_page .entry-meta { font-size: 8pt; line-height: 1.3; margin-bottom: 1mm; }
.modern_professional { display: flex; padding: 0; }
.modern_professional > aside { width: 32%; min-height: 297mm; padding: 14mm 8mm; background: #6A9B5E; color: white; }
.modern_professional > main { width: 68%; padding: 14mm 10mm; }
.modern_professional aside h1 { font-size: 19pt; }
.modern_professional aside h2 { border-color: rgba(255,255,255,.5); }
.modern_professional main h2 { color: #6A9B5E; border: 0; border-left: 1mm solid #6A9B5E; padding-left: 2mm; }
"""


def render_tailored_cv_html(
    tailored_cv: TailoredCV,
    design: CVDesign,
    document_v2: CVDocumentV2 | None = None,
    language: CVLanguage | None = None,
) -> str:
    """Render V2 directly and legacy V1 through the conservative adapter."""
    document = document_v2 or v1_to_v2(tailored_cv)
    source_language = language or detect_tailored_cv_language(tailored_cv)
    html = _render_v2_html(document, design, source_language)
    if design == "compact_one_page" and compact_rendering_warnings(document):
        html = html.replace(
            "<body>",
            f'<body data-render-warning="{COMPACT_OVERFLOW_WARNING}">',
            1,
        )
    return html


async def generate_tailored_cv_pdf(
    tailored_cv: TailoredCV,
    design: CVDesign,
    document_v2: CVDocumentV2 | None = None,
    language: CVLanguage | None = None,
) -> bytes:
    """Generate a PDF without hiding overflowing compact-template content."""
    html = render_tailored_cv_html(tailored_cv, design, document_v2, language)
    from playwright.async_api import async_playwright

    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(headless=True)
        page = await browser.new_page()
        await page.set_content(html, wait_until="load")
        pdf = await page.pdf(
            format="A4",
            print_background=True,
            margin={"top": "0", "right": "0", "bottom": "0", "left": "0"},
        )
        await browser.close()
    return pdf
