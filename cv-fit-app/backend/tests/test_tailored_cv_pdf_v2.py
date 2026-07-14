from app.models.cv_document_v2 import (
    CVDocumentV2,
    CVEducationBlock,
    CVEntryBlock,
    CVIdentity,
    CVPublicationBlock,
    CVSection,
)
from app.models.domain import TailoredCV
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
                    )
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
                    )
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
                    )
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
