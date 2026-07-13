import unicodedata
from html import escape

from app.models.domain import TailoredCV, TailoredCVSection
from app.schemas.tailored_cv import CVDesign


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


def render_tailored_cv_html(cv: TailoredCV, design: CVDesign) -> str:
    """Render a self-contained, escaped A4 document for browser PDF output."""
    contacts = " · ".join(escape(line) for line in cv.contact_lines)
    cv_sections = _sections(cv)
    source_text = " ".join(
        [cv.name, cv.summary]
        + [
            value
            for section in cv_sections
            for value in [section.title, *section.items]
        ]
    )
    vietnamese = any(character in source_text for character in "ăâđêôơưĂÂĐÊÔƠƯ")
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

    return f"""<!doctype html><html><head><meta charset="utf-8"><style>
      @page {{ size: A4; margin: 0; }} * {{ box-sizing: border-box; }}
      body {{ margin: 0; color: #263b3b; font-family: Arial, sans-serif; }}
      article {{ width: 210mm; min-height: 297mm; background: white; padding: 16mm; }}
      header {{ border-bottom: 1px solid #9ca3af; padding-bottom: 5mm; }}
      h1 {{ margin: 0 0 1mm; font-size: 24pt; }} h3 {{ margin: 0 0 3mm; font-size: 11pt; }}
      .contacts {{ color: #596565; font-size: 8.5pt; }} section {{ margin-top: 6mm; break-inside: avoid; }}
      h2 {{ margin: 0 0 2.5mm; border-bottom: 1px solid #9ca3af; padding-bottom: 1mm; font-size: 10pt; text-transform: uppercase; letter-spacing: 1.2px; }}
      .item, .bullet {{ margin: 0 0 1.5mm; font-size: 9pt; line-height: 1.45; white-space: pre-wrap; }}
      .headline {{ margin: 0 0 1.5mm; font-size: 9pt; line-height: 1.45; font-weight: 700; white-space: pre-wrap; }}
      .bullet {{ padding-left: 4mm; }} .bullet::before {{ content: '•'; margin-left: -3mm; margin-right: 2mm; }}
      .classic_ats {{ font-family: Georgia, 'Times New Roman', serif; }}
      .compact_one_page {{ border-top: 1.5mm solid #4A90A4; padding: 10mm 13mm; }}
      .compact_one_page section {{ margin-top: 3.5mm; }} .compact_one_page h2 {{ border: 0; border-left: 1mm solid #4A90A4; padding-left: 2mm; }}
      .compact_one_page .item, .compact_one_page .bullet {{ font-size: 8pt; line-height: 1.3; margin-bottom: 1mm; }}
      .modern_professional {{ display: flex; padding: 0; }} .modern_professional > aside {{ width: 32%; min-height: 297mm; padding: 14mm 8mm; background: #6A9B5E; color: white; }}
      .modern_professional > main {{ width: 68%; padding: 14mm 10mm; }} .modern_professional aside header {{ border-color: rgba(255,255,255,.5); }}
      .modern_professional aside h1 {{ font-size: 19pt; }} .modern_professional aside h2 {{ border-color: rgba(255,255,255,.5); }}
      .modern_professional main h2 {{ color: #6A9B5E; border: 0; border-left: 1mm solid #6A9B5E; padding-left: 2mm; }}
    </style></head><body><article class="{design}">{header}{body}</article></body></html>"""


async def generate_tailored_cv_pdf(cv: TailoredCV, design: CVDesign) -> bytes:
    from playwright.async_api import async_playwright

    html = render_tailored_cv_html(cv, design)
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
