"""Phase 6 Thin Playwright PDF adapter using canonical server-rendered template HTML."""

import logging

from app.models.cv_document_v2 import CVDocumentV2
from app.models.domain import TailoredCV
from app.schemas.tailored_cv import CVDesign
from app.services.cv_language import CVLanguage, detect_tailored_cv_language
from app.services.cv_render_ledger import build_cv_render_ledger
from app.services.cv_render_validation import validate_render_output
from app.services.cv_template_render_service import render_cv_document
from app.services.cv_v1_adapter import v1_to_v2

_logger = logging.getLogger(__name__)


def render_tailored_cv_html(
    tailored_cv: TailoredCV,
    design: CVDesign = "classic_ats",
    document_v2: CVDocumentV2 | None = None,
    language: CVLanguage | None = None,
    template_id: str | None = None,
    template_version: int | None = None,
) -> str:
    """Render canonical HTML using Phase 6 server-owned template renderer."""
    document = document_v2 or v1_to_v2(tailored_cv)
    target_lang = language or detect_tailored_cv_language(tailored_cv)
    target_template = template_id or design

    result = render_cv_document(
        document=document,
        template_id=target_template,
        template_version=template_version,
        language=target_lang,
    )
    return result.html


async def generate_tailored_cv_pdf(
    tailored_cv: TailoredCV,
    design: CVDesign = "classic_ats",
    document_v2: CVDocumentV2 | None = None,
    language: CVLanguage | None = None,
    template_id: str | None = None,
    template_version: int | None = None,
) -> bytes:
    """Generate PDF binary from canonical server-rendered HTML with Playwright validation."""
    document = document_v2 or v1_to_v2(tailored_cv)
    target_lang = language or detect_tailored_cv_language(tailored_cv)
    target_template = template_id or design

    render_result = render_cv_document(
        document=document,
        template_id=target_template,
        template_version=template_version,
        language=target_lang,
    )

    ledger = build_cv_render_ledger(document)

    # Single-pass validation and PDF generation
    pdf_bytes = await validate_render_output(
        document,
        render_result.html,
        ledger,
        render_result.diagnostics,
        run_playwright=True,
    )

    if not pdf_bytes:
        from playwright.async_api import async_playwright

        async with async_playwright() as playwright:
            browser = await playwright.chromium.launch(headless=True)
            page = await browser.new_page(viewport={"width": 794, "height": 1123})
            await page.set_content(render_result.html, wait_until="domcontentloaded")
            await page.evaluate("document.fonts.ready")

            pdf_bytes = await page.pdf(
                format="A4",
                print_background=True,
                margin={"top": "0", "right": "0", "bottom": "0", "left": "0"},
            )
            await browser.close()

    if not pdf_bytes or len(pdf_bytes) < 100:
        raise RuntimeError("PDF generation yielded empty or corrupted binary.")

    return pdf_bytes
