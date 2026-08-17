"""Unit tests for Phase 6 canonical render ledger."""

from app.models.cv_document_v2 import (
    CVDocumentV2,
    CVEntryBlock,
    CVIdentity,
    CVSection,
    CVUnknownBlock,
)
from app.services.cv_render_ledger import build_cv_render_ledger


def test_render_ledger_extracts_stable_field_ids():
    doc = CVDocumentV2(
        identity=CVIdentity(
            full_name="Nguyen Van A",
            headline="Senior Backend Engineer",
            email="nguyenvana@example.com",
            phone="+84 901 234 567",
        ),
        sections=[
            CVSection(
                id="sec_exp",
                title="Experience",
                type="experience",
                blocks=[
                    CVEntryBlock(
                        title="Senior Engineer",
                        organization="Tech Corp",
                        bullets=[
                            "Built scalable services",
                            "Optimized database queries",
                        ],
                    )
                ],
            ),
            CVSection(
                id="sec_custom",
                title="Custom Projects",
                type="custom",
                blocks=[
                    CVUnknownBlock(
                        lines=["Line 1 of unknown content", "Line 2 of unknown content"]
                    )
                ],
            ),
        ],
    )

    ledger = build_cv_render_ledger(doc)

    assert "identity:full_name" in ledger.items
    assert ledger.items["identity:full_name"].expected_text == "Nguyen Van A"
    assert "identity:headline" in ledger.items

    assert "contact:line:0" in ledger.items
    assert "contact:line:1" in ledger.items

    assert "section:sec_exp:title" in ledger.items
    assert ledger.items["section:sec_exp:title"].expected_text == "Experience"

    assert "section:sec_exp:block:0:title" in ledger.items
    assert "section:sec_exp:block:0:bullet:0" in ledger.items
    assert (
        ledger.items["section:sec_exp:block:0:bullet:0"].expected_text
        == "Built scalable services"
    )

    assert "section:sec_custom:block:0:line:0" in ledger.items
    assert (
        ledger.items["section:sec_custom:block:0:line:0"].expected_text
        == "Line 1 of unknown content"
    )


def test_render_ledger_prevents_double_contact_lines_counting():
    doc = CVDocumentV2(
        identity=CVIdentity(
            full_name="Test User",
            email="test@example.com",
            phone="123456",
            contact_lines=["test@example.com", "123456"],
        )
    )

    ledger = build_cv_render_ledger(doc)

    # Canonical contacts preferred: contact:line:0 and contact:line:1 exist exactly once
    contact_keys = [key for key in ledger.items if key.startswith("contact:line:")]
    assert len(contact_keys) == 2
