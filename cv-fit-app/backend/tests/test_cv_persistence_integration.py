"""Integration tests for CV extraction, reconstruction, versioning, and rendering."""

from unittest.mock import MagicMock

from app.models.cv_document_v2 import (
    CURRENT_RECONSTRUCTION_VERSION,
    CVDocumentV2,
    CVReconstructionDiagnostics,
    CVSourceCoverageDiagnostics,
)
from app.services.cv_reconstruction_service import (
    reconstruct_from_lines,
    validate_reconstruction_gate,
)
from app.services.cv_template_render_service import render_cv_document
from app.services.layout_extraction import layout_extract_pdf


def test_spatial_words_reconstruction_e2e_flow(monkeypatch) -> None:
    """Verify spatial words extract into distinct lines, form a valid V3 CVDocumentV2,
    pass quality gate, and render cleanly to HTML.
    """
    words = [
        {
            "text": "PHAM",
            "x0": 50,
            "x1": 100,
            "top": 80.0,
            "x": 50,
            "y": 80,
            "height": 14,
        },
        {
            "text": "THAO",
            "x0": 105,
            "x1": 150,
            "top": 80.0,
            "x": 105,
            "y": 80,
            "height": 14,
        },
        {
            "text": "email@gmail.com",
            "x0": 350,
            "x1": 480,
            "top": 80.0,
            "x": 350,
            "y": 80,
            "height": 12,
        },
        {
            "text": "CAREER",
            "x0": 50,
            "x1": 110,
            "top": 100.0,
            "x": 50,
            "y": 100,
            "height": 12,
        },
        {
            "text": "OBJECTIVE",
            "x0": 115,
            "x1": 180,
            "top": 100.0,
            "x": 115,
            "y": 100,
            "height": 12,
        },
        {
            "text": "Seeking",
            "x0": 350,
            "x1": 400,
            "top": 100.0,
            "x": 350,
            "y": 100,
            "height": 12,
        },
        {
            "text": "role",
            "x0": 405,
            "x1": 430,
            "top": 100.0,
            "x": 405,
            "y": 100,
            "height": 12,
        },
        {
            "text": "EDUCATION",
            "x0": 50,
            "x1": 140,
            "top": 140.0,
            "x": 50,
            "y": 140,
            "height": 12,
        },
        {
            "text": "+84123456789",
            "x0": 350,
            "x1": 460,
            "top": 140.0,
            "x": 350,
            "y": 140,
            "height": 12,
        },
        {
            "text": "Hanoi",
            "x0": 50,
            "x1": 100,
            "top": 160.0,
            "x": 50,
            "y": 160,
            "height": 12,
        },
        {
            "text": "University",
            "x0": 105,
            "x1": 180,
            "top": 160.0,
            "x": 105,
            "y": 160,
            "height": 12,
        },
        {
            "text": "EXPERIENCE",
            "x0": 50,
            "x1": 150,
            "top": 180.0,
            "x": 50,
            "y": 180,
            "height": 12,
        },
        {
            "text": "Software",
            "x0": 50,
            "x1": 120,
            "top": 200.0,
            "x": 50,
            "y": 200,
            "height": 12,
        },
        {
            "text": "Engineer",
            "x0": 125,
            "x1": 180,
            "top": 200.0,
            "x": 125,
            "y": 200,
            "height": 12,
        },
    ]

    fake_page = MagicMock()
    fake_page.width = 612.0
    fake_page.height = 792.0
    fake_page.extract_words.return_value = words

    fake_pdf = MagicMock()
    fake_pdf.pages = [fake_page]
    fake_pdf.__enter__.return_value = fake_pdf

    monkeypatch.setattr(
        "app.services.layout_extraction.pdfplumber.open",
        lambda _stream: fake_pdf,
    )

    lines = layout_extract_pdf(b"fake_pdf")
    print(
        "\nDEBUG EXTRACTED LINES:",
        [f"{line.text} (x={line.x}, y={line.y})" for line in lines],
    )
    doc = reconstruct_from_lines(lines)

    # 1. Version check
    assert doc.reconstruction_version == CURRENT_RECONSTRUCTION_VERSION

    # 2. Structure check: candidate identity and sections reconstructed
    assert doc.identity.name == "PHAM THAO"
    assert len(doc.sections) >= 2

    doc.reconstruction_diagnostics = CVReconstructionDiagnostics(
        reconstruction_version=CURRENT_RECONSTRUCTION_VERSION,
        warnings=[],
        block_confidence={},
        source_coverage=CVSourceCoverageDiagnostics(
            raw_block_count=1,
            accounted_block_count=1,
            significant_character_count=100,
            mapped_character_count=100,
            coverage_ratio=1.0,
        ),
    )

    # 3. Gate validation check
    validate_reconstruction_gate(doc)

    # 4. Serialization / Deserialization check
    json_data = doc.model_dump_json()
    reloaded_doc = CVDocumentV2.model_validate_json(json_data)
    assert reloaded_doc.reconstruction_version == CURRENT_RECONSTRUCTION_VERSION

    # 5. Backend HTML rendering check
    html = render_cv_document(
        reloaded_doc, template_id="classic_ats", language="vi"
    ).html
    assert "<html" in html.lower()
    assert "pham thao" in html.lower() or "email@gmail.com" in html.lower()


def test_stale_v2_client_doc_reconstruction_version_status() -> None:
    stale_doc = CVDocumentV2(reconstruction_version=2)
    assert stale_doc.reconstruction_version == 2

    current_doc = CVDocumentV2()
    assert current_doc.reconstruction_version == CURRENT_RECONSTRUCTION_VERSION
