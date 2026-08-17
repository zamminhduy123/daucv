"""Contract test verifying server PDF and preview rendering share identical outputs."""

import json
from pathlib import Path

import pytest

from app.models.cv_document_v2 import CVDocumentV2
from app.models.domain import TailoredCV
from app.services.cv_rendering_diagnostics import COMPACT_OVERFLOW_WARNING
from app.services.cv_template_render_service import render_cv_document
from app.services.tailored_cv_pdf import render_tailored_cv_html

FIXTURE = Path(__file__).parent / "fixtures" / "cv_render_parity.json"
DESIGNS = ("classic_ats", "modern_professional", "compact_one_page")


@pytest.mark.parametrize("design", DESIGNS)
def test_preview_and_backend_pdf_share_identical_rendering(design: str) -> None:
    fixture = json.loads(FIXTURE.read_text())
    document = CVDocumentV2.model_validate(fixture["document"])

    pdf_html = render_tailored_cv_html(
        TailoredCV(name="Legacy"),
        design,
        document,
        language="en",
    )
    preview_result = render_cv_document(
        document=document,
        template_id=design,
        language="en",
    )

    # 1. HTML string parity check
    assert pdf_html == preview_result.html

    for block_type in fixture["expected_block_types"]:
        marker = f'data-block-type="{block_type}"'
        assert marker in pdf_html
    for content in fixture["expected_content"]:
        assert content in pdf_html

    assert 'data-confidence="0.20"' in pdf_html

    # 2. Browser layout parity check (verifying matching layout/bounding boxes)
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        return

    with sync_playwright() as p:
        try:
            browser = p.chromium.launch(headless=True)
        except Exception:
            # Skip layout checks if chromium is not installed/runnable
            return

        pdf_page = browser.new_page(viewport={"width": 794, "height": 1123})
        pdf_page.set_content(pdf_html, wait_until="domcontentloaded")
        pdf_page.evaluate("document.fonts.ready")
        pdf_boxes = pdf_page.evaluate("""() => {
            return Array.from(document.querySelectorAll('[data-field-id]')).map(el => {
                const rect = el.getBoundingClientRect();
                return { id: el.getAttribute('data-field-id'), top: rect.top, left: rect.left, width: rect.width, height: rect.height };
            });
        }""")
        pdf_page.close()

        preview_page = browser.new_page(viewport={"width": 794, "height": 1123})
        preview_page.set_content(preview_result.html, wait_until="domcontentloaded")
        preview_page.evaluate("document.fonts.ready")
        preview_boxes = preview_page.evaluate("""() => {
            return Array.from(document.querySelectorAll('[data-field-id]')).map(el => {
                const rect = el.getBoundingClientRect();
                return { id: el.getAttribute('data-field-id'), top: rect.top, left: rect.left, width: rect.width, height: rect.height };
            });
        }""")
        preview_page.close()
        browser.close()

        assert len(pdf_boxes) == len(preview_boxes)
        for b1, b2 in zip(pdf_boxes, preview_boxes, strict=True):
            assert b1["id"] == b2["id"]
            assert abs(b1["top"] - b2["top"]) < 0.1
            assert abs(b1["left"] - b2["left"]) < 0.1
            assert abs(b1["width"] - b2["width"]) < 0.1
            assert abs(b1["height"] - b2["height"]) < 0.1


def test_compact_overflow_warning_is_shared_by_preview_and_pdf() -> None:
    fixture = json.loads(FIXTURE.read_text())
    source = fixture["document"]
    source["sections"][0]["blocks"][0]["bullets"] = [
        f"Preserved bullet {index}" for index in range(80)
    ]
    document = CVDocumentV2.model_validate(source)

    pdf_html = render_tailored_cv_html(
        TailoredCV(name="Legacy"),
        "compact",
        document,
        language="en",
    )
    preview_result = render_cv_document(
        document=document,
        template_id="compact",
        language="en",
    )

    warning = f'data-render-warning="{COMPACT_OVERFLOW_WARNING}"'
    assert warning in pdf_html
    assert warning in preview_result.html
    assert pdf_html == preview_result.html
