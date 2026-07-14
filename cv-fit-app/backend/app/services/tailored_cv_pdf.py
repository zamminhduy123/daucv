"""
Tailored CV PDF rendering.

Provides two rendering paths:
  1. **V2 typed‑block rendering** – consumes ``CVDocumentV2`` and renders
     explicit semantic blocks (entry, bullet, paragraph, skill_group, etc.).
  2. **V1 legacy rendering** – consumes ``TailoredCV`` with
     ``sections[].items: string[]`` and applies the original positional
     highlight logic (kept for backward compatibility).

The public entry points ``render_tailored_cv_html`` and
``generate_tailored_cv_pdf`` accept a ``TailoredCVVersionResponse``
which carries both ``tailored_cv`` (V1) and ``document_v2`` (V2).
V2 is preferred; V1 is used as a fallback.
"""

import unicodedata
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
from app.models.domain import TailoredCV, TailoredCVSection
from app.schemas.tailored_cv import CVDesign
from app.services.cv_language import CVLanguage, detect_tailored_cv_language

# ---------------------------------------------------------------------------
# V2 typed-block renderer
# ---------------------------------------------------------------------------


def _block_html(block: CVBlockType) -> str:
    """Render a single typed block to HTML."""
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
        for bullet in block.bullets or []:
            parts.append(f'<p class="bullet">{escape(bullet)}</p>')
        return "".join(parts)

    if isinstance(block, CVBulletBlock):
        return f'<p class="bullet">{escape(block.text)}</p>'

    if isinstance(block, CVParagraphBlock):
        return f'<p class="item">{escape(block.text)}</p>'

    if isinstance(block, CVSkillGroupBlock):
        if block.label:
            parts = [f'<p class="entry-title">{escape(block.label)}</p>']
        else:
            parts = []
        skills_html = " · ".join(escape(s) for s in (block.skills or []))
        parts.append(f'<p class="skills">{skills_html}</p>')
        return "".join(parts)

    if isinstance(block, CVPublicationBlock):
        parts = [f'<p class="publication">{escape(block.title)}</p>']
        if block.authors:
            parts.append(f'<p class="item">{escape(block.authors)}</p>')
        publication_meta = " · ".join(
            escape(value) for value in (block.venue, block.date, block.status) if value
        )
        if publication_meta:
            parts.append(f'<p class="item">{publication_meta}</p>')
        return "".join(parts)

    if isinstance(block, CVEducationBlock):
        parts = []
        if block.institution:
            parts.append(f'<p class="entry-title">{escape(block.institution)}</p>')
        education_title = " — ".join(
            escape(value) for value in (block.degree, block.field) if value
        )
        if education_title:
            parts.append(f'<p class="entry-subtitle">{education_title}</p>')
        education_meta = " · ".join(
            escape(value) for value in (block.location, block.date) if value
        )
        if education_meta:
            parts.append(f'<p class="entry-meta">{education_meta}</p>')
        for detail in block.details or []:
            parts.append(f'<p class="item">{escape(detail)}</p>')
        return "".join(parts)

    if isinstance(block, CVUnknownBlock):
        return f'<p class="item">{escape(" | ".join(block.lines or []))}</p>'

    return ""


def _section_blocks_html(section: CVSection) -> str:
    """Render all blocks in a CVSection."""
    blocks_html = "".join(_block_html(b) for b in section.blocks)
    return f"<section><h2>{escape(section.title)}</h2>{blocks_html}</section>"


def _render_v2_html(
    doc: CVDocumentV2,
    design: CVDesign,
    language: CVLanguage | None = None,
) -> str:
    """Render a ``CVDocumentV2`` document to HTML."""
    contacts = " · ".join(escape(line) for line in (doc.identity.contact_lines or []))
    vietnamese = (
        language == "vi"
        if language
        else detect_tailored_cv_language(
            TailoredCV(
                name=doc.identity.name,
                headline=doc.identity.headline,
                contact_lines=doc.identity.contact_lines,
                summary=doc.summary.text if doc.summary else "",
                sections=[],
                experience=[],
                skills=[],
                education="",
            )
        )
        == "vi"
    )
    profile_label = "Tóm tắt" if vietnamese else "Profile"
    contact_label = "Liên hệ" if vietnamese else "Contact"

    # Summary
    summary_html = ""
    if doc.summary:
        summary_html = (
            f"<section><h2>{profile_label}</h2>{_block_html(doc.summary)}</section>"
        )

    # Sections (skip summary section type)
    sections_html = "".join(
        _section_blocks_html(s) for s in doc.sections if s.type != "summary"
    )

    # Header
    header = (
        f"<header><h1>{escape(doc.identity.name or 'CV')}</h1>"
        f"<h3>{escape(doc.identity.headline or '')}</h3><p class=contacts>{contacts}</p></header>"
    )
    body = f"{summary_html}{sections_html}"

    # Modern Professional: sidebar layout
    if design == "modern_professional":
        sidebar_sections = [
            s
            for s in doc.sections
            if s.type in ("skills", "education") and s.type != "summary"
        ]
        main_sections = [
            s
            for s in doc.sections
            if s.type not in ("skills", "education") and s.type != "summary"
        ]
        body = (
            f'<aside>{header}<section><h2>{contact_label}</h2><p class="item">{contacts}</p></section>'
            f"{''.join(_section_blocks_html(s) for s in sidebar_sections)}</aside>"
            f"<main>{summary_html}{''.join(_section_blocks_html(s) for s in main_sections)}</main>"
        )
        header = ""

    css = """
      @page { size: A4; margin: 0; } * { box-sizing: border-box; }
      body { margin: 0; color: #263b3b; font-family: Arial, sans-serif; }
      article { width: 210mm; min-height: 297mm; background: white; padding: 16mm; }
      header { border-bottom: 1px solid #9ca3af; padding-bottom: 5mm; }
      h1 { margin: 0 0 1mm; font-size: 24pt; } h3 { margin: 0 0 3mm; font-size: 11pt; }
      .contacts { color: #596565; font-size: 8.5pt; } section { margin-top: 6mm; break-inside: avoid; }
      h2 { margin: 0 0 2.5mm; border-bottom: 1px solid #9ca3af; padding-bottom: 1mm; font-size: 10pt; text-transform: uppercase; letter-spacing: 1.2px; }
      .item, .bullet { margin: 0 0 1.5mm; font-size: 9pt; line-height: 1.45; white-space: pre-wrap; }
      .entry-title { margin: 0 0 1.5mm; font-size: 9pt; line-height: 1.45; font-weight: 700; white-space: pre-wrap; }
      .entry-subtitle, .entry-meta { margin: 0 0 1.5mm; font-size: 9pt; line-height: 1.45; font-weight: 400; color: #555; white-space: pre-wrap; }
      .bullet { padding-left: 4mm; } .bullet::before { content: '\\2022'; margin-left: -3mm; margin-right: 2mm; }
      .skills { font-size: 8.5pt; color: #333; }
      .publication { font-size: 9pt; font-style: italic; }
      .classic_ats { font-family: Georgia, 'Times New Roman', serif; }
      .compact_one_page { border-top: 1.5mm solid #4A90A4; padding: 10mm 13mm; }
      .compact_one_page section { margin-top: 3.5mm; } .compact_one_page h2 { border: 0; border-left: 1mm solid #4A90A4; padding-left: 2mm; }
      .compact_one_page .item, .compact_one_page .bullet { font-size: 8pt; line-height: 1.3; margin-bottom: 1mm; }
      .modern_professional { display: flex; padding: 0; } .modern_professional > aside { width: 32%; min-height: 297mm; padding: 14mm 8mm; background: #6A9B5E; color: white; }
      .modern_professional > main { width: 68%; padding: 14mm 10mm; } .modern_professional aside header { border-color: rgba(255,255,255,.5); }
      .modern_professional aside h1 { font-size: 19pt; } .modern_professional aside h2 { border-color: rgba(255,255,255,.5); }
      .modern_professional main h2 { color: #6A9B5E; border: 0; border-left: 1mm solid #6A9B5E; padding-left: 2mm; }
    """
    return (
        f'<!doctype html><html><head><meta charset="utf-8"><style>{css}</style></head>'
        f'<body><article class="{design}">{header}{body}</article></body></html>'
    )


# ---------------------------------------------------------------------------
# V1 legacy renderer (unchanged logic, kept for backward compat)
# ---------------------------------------------------------------------------


def _section_kind(title: str) -> str:
    decomposed = unicodedata.normalize("NFKD", title.lower())
    normalized = "".join(
        character for character in decomposed if not unicodedata.combining(character)
    )
    if "skill" in normalized or "ky nang" in normalized:
        return "skills"
    if "education" in normalized or "hoc van" in normalized:
        return "education"
    return "main"


def _sections(cv: TailoredCV) -> list[TailoredCVSection]:
    """Derive sections from a V1 ``TailoredCV``."""
    if cv.sections:
        return cv.sections
    sections: list[TailoredCVSection] = []
    if cv.experience:
        sections.append(
            TailoredCVSection(
                title="Experience",
                items=[
                    value
                    for experience in cv.experience
                    for value in [
                        f"{experience.role} — {experience.company}",
                        *experience.bullet_points,
                    ]
                ],
            )
        )
    if cv.skills:
        sections.append(TailoredCVSection(title="Skills", items=cv.skills))
    if cv.education:
        sections.append(TailoredCVSection(title="Education", items=[cv.education]))
    return sections


def _section_html(section: TailoredCVSection) -> str:
    normalized_items: list[str] = []
    for item in section.items:
        stripped = item.strip()
        if (
            normalized_items
            and normalized_items[-1][:1] in "•●▪◦"
            and stripped
            and stripped[0].islower()
        ):
            normalized_items[-1] = f"{normalized_items[-1].rstrip()} {stripped}"
        else:
            normalized_items.append(item)

    items = []
    for index, item in enumerate(normalized_items):
        cleaned = item.lstrip("•●▪◦ ")
        is_bullet = item[:1] in "•●▪◦"
        follows_bullet = index > 0 and normalized_items[index - 1][:1] in "•●▪◦"
        class_name = (
            "bullet"
            if is_bullet
            else "headline"
            if index == 0 or follows_bullet
            else "item"
        )
        items.append(f'<p class="{class_name}">{escape(cleaned)}</p>')
    return f"<section><h2>{escape(section.title)}</h2>{''.join(items)}</section>"


def _render_v1_html(cv: TailoredCV, design: CVDesign) -> str:
    """Render a legacy V1 ``TailoredCV`` to HTML."""
    contacts = " · ".join(escape(line) for line in cv.contact_lines)
    cv_sections = _sections(cv)
    vietnamese = detect_tailored_cv_language(cv) == "vi"
    profile_label = "Tóm tắt" if vietnamese else "Profile"
    contact_label = "Liên hệ" if vietnamese else "Contact"
    summary = (
        f'<section><h2>{profile_label}</h2><p class="item">{escape(cv.summary)}</p></section>'
        if cv.summary
        else ""
    )
    sections = "".join(_section_html(section) for section in cv_sections)
    header = (
        f"<header><h1>{escape(cv.name or 'CV')}</h1>"
        f"<h3>{escape(cv.headline)}</h3><p class=contacts>{contacts}</p></header>"
    )
    body = f"{summary}{sections}"
    if design == "modern_professional":
        sidebar = [
            section
            for section in cv_sections
            if _section_kind(section.title) in {"skills", "education"}
        ]
        main = [section for section in cv_sections if section not in sidebar]
        body = (
            f'<aside>{header}<section><h2>{contact_label}</h2><p class="item">{contacts}</p></section>'
            f"{''.join(_section_html(section) for section in sidebar)}</aside>"
            f"<main>{summary}{''.join(_section_html(section) for section in main)}</main>"
        )
        header = ""

    css = """
      @page { size: A4; margin: 0; } * { box-sizing: border-box; }
      body { margin: 0; color: #263b3b; font-family: Arial, sans-serif; }
      article { width: 210mm; min-height: 297mm; background: white; padding: 16mm; }
      header { border-bottom: 1px solid #9ca3af; padding-bottom: 5mm; }
      h1 { margin: 0 0 1mm; font-size: 24pt; } h3 { margin: 0 0 3mm; font-size: 11pt; }
      .contacts { color: #596565; font-size: 8.5pt; } section { margin-top: 6mm; break-inside: avoid; }
      h2 { margin: 0 0 2.5mm; border-bottom: 1px solid #9ca3af; padding-bottom: 1mm; font-size: 10pt; text-transform: uppercase; letter-spacing: 1.2px; }
      .item, .bullet { margin: 0 0 1.5mm; font-size: 9pt; line-height: 1.45; white-space: pre-wrap; }
      .headline { margin: 0 0 1.5mm; font-size: 9pt; line-height: 1.45; font-weight: 700; white-space: pre-wrap; }
      .bullet { padding-left: 4mm; } .bullet::before { content: '\\2022'; margin-left: -3mm; margin-right: 2mm; }
      .classic_ats { font-family: Georgia, 'Times New Roman', serif; }
      .compact_one_page { border-top: 1.5mm solid #4A90A4; padding: 10mm 13mm; }
      .compact_one_page section { margin-top: 3.5mm; } .compact_one_page h2 { border: 0; border-left: 1mm solid #4A90A4; padding-left: 2mm; }
      .compact_one_page .item, .compact_one_page .bullet { font-size: 8pt; line-height: 1.3; margin-bottom: 1mm; }
      .modern_professional { display: flex; padding: 0; } .modern_professional > aside { width: 32%; min-height: 297mm; padding: 14mm 8mm; background: #6A9B5E; color: white; }
      .modern_professional > main { width: 68%; padding: 14mm 10mm; } .modern_professional aside header { border-color: rgba(255,255,255,.5); }
      .modern_professional aside h1 { font-size: 19pt; } .modern_professional aside h2 { border-color: rgba(255,255,255,.5); }
      .modern_professional main h2 { color: #6A9B5E; border: 0; border-left: 1mm solid #6A9B5E; padding-left: 2mm; }
    """
    return (
        f'<!doctype html><html><head><meta charset="utf-8"><style>{css}</style></head>'
        f'<body><article class="{design}">{header}{body}</article></body></html>'
    )


# ---------------------------------------------------------------------------
# Public entry points
# ---------------------------------------------------------------------------


def render_tailored_cv_html(
    tailored_cv: TailoredCV,
    design: CVDesign,
    document_v2: CVDocumentV2 | None = None,
    language: CVLanguage | None = None,
) -> str:
    """Render a tailored CV to HTML.

    Prefers the V2 typed-block renderer when ``document_v2`` is present;
    falls back to the V1 renderer otherwise.
    """
    if document_v2 is not None:
        return _render_v2_html(document_v2, design, language)
    return _render_v1_html(tailored_cv, design)


async def generate_tailored_cv_pdf(
    tailored_cv: TailoredCV,
    design: CVDesign,
    document_v2: CVDocumentV2 | None = None,
    language: CVLanguage | None = None,
) -> bytes:
    """Generate a PDF for a tailored CV.

    Accepts an optional ``document_v2`` for V2 rendering.
    Falls back to V1 rendering when not provided.
    """
    html = render_tailored_cv_html(tailored_cv, design, document_v2, language)
    from playwright.async_api import async_playwright

    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(headless=True)
        page = await browser.new_page()
        await page.set_content(html, wait_until="load")
        if design == "compact_one_page":
            await page.evaluate(
                """() => {
                  const article = document.querySelector('article');
                  if (!article) return;
                  const targetHeight = 1122;
                  const scale = Math.min(1, targetHeight / article.scrollHeight);
                  article.style.transformOrigin = 'top left';
                  article.style.transform = `scale(${scale})`;
                  article.style.width = `${100 / scale}%`;
                  document.body.style.height = `${targetHeight}px`;
                  document.body.style.overflow = 'hidden';
                }"""
            )
        pdf = await page.pdf(
            format="A4",
            print_background=True,
            margin={"top": "0", "right": "0", "bottom": "0", "left": "0"},
        )
        await browser.close()
    return pdf
