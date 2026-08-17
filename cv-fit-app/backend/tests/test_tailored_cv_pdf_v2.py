from app.models.cv_document_v2 import (
    CVDocumentV2,
    CVEducationBlock,
    CVEntryBlock,
    CVIdentity,
    CVPublicationBlock,
    CVSection,
    CVUnknownBlock,
)
from app.models.domain import TailoredCV
from app.services.cv_rendering_diagnostics import COMPACT_OVERFLOW_WARNING
from app.services.tailored_cv_pdf import render_tailored_cv_html


def test_v2_renderer_preserves_all_modeled_facts() -> None:
    document = CVDocumentV2(
        identity=CVIdentity(name="Duy"),
        sections=[
            CVSection(
                type="experience",
                title="Experience",
                blocks=[
                    CVEntryBlock(
                        title="Engineer",
                        organization="Example Co",
                        location="Hanoi",
                        date="2024–Present",
                    ),
                ],
            ),
            CVSection(
                type="education",
                title="Education",
                blocks=[
                    CVEducationBlock(
                        institution="Example University",
                        degree="BSc",
                        field="Computer Science",
                        location="Da Nang",
                        date="2020–2024",
                    ),
                ],
            ),
            CVSection(
                type="publications",
                title="Publications",
                blocks=[
                    CVPublicationBlock(
                        title="Typed CVs",
                        venue="CVConf",
                        date="2025",
                        status="Accepted",
                    ),
                ],
            ),
        ],
    )

    html = render_tailored_cv_html(
        TailoredCV(name="Legacy fallback"),
        "classic_ats",
        document,
    )

    for expected in (
        "Example Co",
        "Hanoi",
        "2024–Present",
        "Example University",
        "BSc",
        "Computer Science",
        "Da Nang",
        "2020–2024",
        "CVConf",
        "2025",
        "Accepted",
    ):
        assert expected in html


def test_v2_renderer_uses_explicit_source_language() -> None:
    document = CVDocumentV2(
        identity=CVIdentity(name="Duy"),
        summary={"type": "paragraph", "text": "Backend engineer."},
    )

    html = render_tailored_cv_html(
        TailoredCV(name="Duy"),
        "classic_ats",
        document,
        language="vi",
    )

    assert "Tóm tắt" in html


def test_v2_renderer_prefers_canonical_identity_over_mutated_legacy_fields() -> None:
    identity = CVIdentity(
        full_name="Canonical Candidate",
        email="canonical@example.com",
    )
    identity.name = "Stale Legacy Name"
    identity.contact_lines = [
        "stale@example.com",
        "Portfolio available on request",
    ]
    document = CVDocumentV2(identity=identity)

    html = render_tailored_cv_html(
        TailoredCV(name="Fallback"),
        "classic_ats",
        document,
    )

    assert "Canonical Candidate" in html
    assert "canonical@example.com" in html
    assert "Portfolio available on request" in html
    assert "Stale Legacy Name" not in html
    assert "stale@example.com" not in html


def test_v2_renderer_preserves_residual_fragment_from_mixed_legacy_contact() -> None:
    document = CVDocumentV2(
        identity=CVIdentity(
            name="Nguyen Minh An",
            contact_lines=["an@example.com | +84 912 345 678 | Ha Noi, Vietnam"],
        )
    )

    html = render_tailored_cv_html(
        TailoredCV(name="Fallback"),
        "classic_ats",
        document,
    )

    assert document.identity.location is None
    assert html.count("an@example.com") == 1
    assert html.count("+84 912 345 678") == 1
    assert html.count("Ha Noi, Vietnam") == 1


def test_all_designs_use_the_same_explicit_block_semantics() -> None:
    document = CVDocumentV2(
        identity=CVIdentity(name="Duy"),
        sections=[
            CVSection(
                type="custom",
                title="Other",
                blocks=[
                    CVUnknownBlock(
                        block_id="unknown-1",
                        lines=["Uncertain text"],
                        confidence=0.2,
                    ),
                ],
            ),
        ],
    )

    for design in ("classic_ats", "modern_professional", "compact_one_page"):
        html = render_tailored_cv_html(TailoredCV(name="Duy"), design, document)
        assert 'data-block-type="unknown"' in html
        assert "Uncertain text" in html
        assert 'data-field-id="identity:headline"' not in html


def test_legacy_document_uses_v1_adapter_instead_of_position() -> None:
    legacy = TailoredCV(
        name="Duy",
        sections=[{"title": "Skills", "items": ["Python", "FastAPI"]}],
    )

    html = render_tailored_cv_html(legacy, "classic_ats")

    assert 'data-block-type="skill_group"' in html
    assert 'data-field-id="identity:headline"' not in html


def test_compact_renderer_reports_when_content_must_paginate() -> None:
    document = CVDocumentV2(
        identity=CVIdentity(name="Duy"),
        sections=[
            CVSection(
                type="experience",
                title="Experience",
                blocks=[
                    CVEntryBlock(
                        title="Engineer",
                        organization="Example Co",
                        bullets=[
                            f"Preserved source bullet {index}" for index in range(80)
                        ],
                    ),
                ],
            ),
        ],
    )

    html = render_tailored_cv_html(
        TailoredCV(name="Duy"),
        "compact_one_page",
        document,
    )

    assert f'data-render-warning="{COMPACT_OVERFLOW_WARNING}"' in html
    assert "Preserved source bullet 79" in html
