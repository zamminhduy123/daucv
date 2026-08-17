"""Unit tests for Phase 6 render validation gate."""

import pytest

from app.models.cv_document_v2 import CVDocumentV2, CVIdentity
from app.services.cv_render_ledger import build_cv_render_ledger
from app.services.cv_render_validation import (
    RenderValidationError,
    validate_render_output,
    validate_static_html,
)
from app.services.cv_template_render_service import render_cv_document


@pytest.mark.asyncio
async def test_validate_render_output_passes_on_valid_rendering() -> None:
    doc = CVDocumentV2(
        identity=CVIdentity(
            full_name="Valid Candidate",
            headline="Software Architect",
            email="valid@example.com",
        )
    )

    result = render_cv_document(doc, template_id="classic_ats")
    ledger = build_cv_render_ledger(doc)

    await validate_render_output(
        doc, result.html, ledger, result.diagnostics, run_playwright=False
    )
    assert result.diagnostics.is_valid is True


@pytest.mark.asyncio
async def test_validate_render_output_rejects_missing_fields() -> None:
    doc = CVDocumentV2(
        identity=CVIdentity(
            full_name="Missing Candidate",
            headline="Architect",
        )
    )

    result = render_cv_document(doc, template_id="classic_ats")
    ledger = build_cv_render_ledger(doc)

    # Tamper HTML to remove data-field-id
    tampered_html = result.html.replace(
        'data-field-id="identity:full_name"', 'class="tampered"'
    )

    with pytest.raises(RenderValidationError, match="Missing field IDs"):
        await validate_render_output(
            doc, tampered_html, ledger, result.diagnostics, run_playwright=False
        )


@pytest.mark.asyncio
async def test_validate_render_output_rejects_duplicate_fields() -> None:
    doc = CVDocumentV2(
        identity=CVIdentity(
            full_name="Duplicate Candidate",
            headline="Architect",
        )
    )

    result = render_cv_document(doc, template_id="classic_ats")
    ledger = build_cv_render_ledger(doc)

    # Duplicate identity:full_name tag
    tampered_html = (
        result.html.replace(
            'data-field-id="identity:full_name"', 'data-field-id="identity:full_name"'
        )
        + '<div data-field-id="identity:full_name">Duplicate Name</div>'
    )

    with pytest.raises(RenderValidationError, match="Duplicate field IDs"):
        await validate_render_output(
            doc, tampered_html, ledger, result.diagnostics, run_playwright=False
        )


def test_validate_static_html_checks_mismatched_and_unescaped_content() -> None:
    doc = CVDocumentV2(
        identity=CVIdentity(
            full_name="Candidate & Partner <Test>",
            headline="Architect",
        )
    )

    result = render_cv_document(doc, template_id="classic_ats")
    ledger = build_cv_render_ledger(doc)

    # Candidate & Partner <Test> must be escaped in HTML as Candidate &amp; Partner &lt;Test&gt;
    # If the unescaped literal exists in html, validation should catch and fail it.
    validate_static_html(result.html, ledger, result.diagnostics)
    assert result.diagnostics.is_valid is True

    # Tamper with unescaped text
    tampered_html = result.html.replace(
        "Candidate &amp; Partner &lt;Test&gt;", "Candidate & Partner <Test>"
    )
    validate_static_html(tampered_html, ledger, result.diagnostics)
    assert result.diagnostics.is_valid is False
    assert any("unescaped" in fid for fid in result.diagnostics.mismatched_field_ids)
