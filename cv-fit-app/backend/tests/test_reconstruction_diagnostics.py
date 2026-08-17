import pytest

from app.models.cv_document_v2 import CVDocumentV2, CVUnknownBlock
from app.services.cv_reconstruction_service import (
    reconstruct_cv_text,
    reconstruction_diagnostics,
    validate_reconstruction_gate,
)


def test_reconstruction_attaches_confidence_and_source_line_ids() -> None:
    document = reconstruct_cv_text(
        "NGUYEN VAN DUY\nBackend Developer\nEXPERIENCE\n"
        "Backend Engineer | TechCorp | 2023\n• Built APIs.",
    )
    entry = document.sections[0].blocks[0]

    assert entry.confidence >= 0.8
    assert entry.source_line_ids
    assert all(line_id.startswith("p1-l") for line_id in entry.source_line_ids)


def test_unknown_content_is_low_confidence_and_observable() -> None:
    document = reconstruct_cv_text(
        "NGUYEN VAN DUY\nBackend Developer\nMISCELLANEOUS\nUnclassified content",
    )
    unknown = next(
        block
        for section in document.sections
        for block in section.blocks
        if isinstance(block, CVUnknownBlock)
    )

    assert unknown.confidence < 0.5
    assert "unknown_section" in unknown.reconstruction_warnings
    assert "unknown_section" in document.reconstruction_warnings


def test_diagnostics_are_separate_from_document_content() -> None:
    document = reconstruct_cv_text(
        "NGUYEN VAN DUY\nBackend Developer\nSKILLS\nBackend: Python, FastAPI",
    )
    diagnostics = reconstruction_diagnostics(document)

    from app.models.cv_document_v2 import CURRENT_RECONSTRUCTION_VERSION

    assert diagnostics.reconstruction_version == CURRENT_RECONSTRUCTION_VERSION
    assert diagnostics.block_confidence
    assert set(diagnostics.block_confidence.values()) <= {0.9, 0.65, 0.75, 0.6}


def test_reconstruction_block_ids_are_stable_for_the_same_source() -> None:
    source = "Duy Nguyen\nBackend Developer\nSKILLS\nBackend: Python, FastAPI"

    first = reconstruct_cv_text(source)
    second = reconstruct_cv_text(source)

    assert [
        block.block_id for section in first.sections for block in section.blocks
    ] == [block.block_id for section in second.sections for block in section.blocks]
    assert [section.id for section in first.sections] == [
        section.id for section in second.sections
    ]


def test_compound_gate_rejection_for_excessive_summary_with_embedded_headings() -> None:
    doc = CVDocumentV2(
        reconstruction_warnings=[
            "summary_ownership_excessive",
            "summary_contains_embedded_headings",
        ]
    )
    with pytest.raises(
        ValueError,
        match="excessive summary ownership co-occurring with embedded section headings",
    ):
        validate_reconstruction_gate(doc)


def test_compound_gate_rejection_for_unjoined_wrap_with_section_collapse() -> None:
    doc = CVDocumentV2(
        reconstruction_warnings=[
            "possible_unjoined_line_wrap",
            "classified_section_collapse",
        ]
    )
    with pytest.raises(
        ValueError, match="line wrap issue co-occurring with section collapse"
    ):
        validate_reconstruction_gate(doc)


def test_current_deterministic_summary_without_coverage_is_rejected() -> None:
    document = reconstruct_cv_text(
        "NGUYEN VAN DUY\nemail@gmail.com\nSUMMARY\nExtremely passionate software engineer with extensive experience in Python, FastAPI, distributed systems, database optimization, cloud computing and team leadership.\nEXPERIENCE\nBackend Engineer | TechCorp | 2023\n• Built APIs.",
    )
    with pytest.raises(ValueError, match="source coverage diagnostics are missing"):
        validate_reconstruction_gate(document)


def test_current_multicol_reconstruction_without_coverage_is_rejected() -> None:
    source = (
        "PHAM TAO THAO CHI thaochi28112005@gmail.com\n"
        "0981929723\nLOGISTICS INTERN\nCAREER OBJECTIVE\n"
        "As a final-year International Economics student at Foreign Trade University...\n"
        "EDUCATION EXPERIENCE\n"
        "FOREIGN TRADE UNIVERSITY\n"
        "International Economics\n"
        "SKILLS ACTIVITIES\n"
        "MICROSOFT OFFICE & GOOGLE WORKSPACE\n"
        "TECHNICAL SKILLS\n"
        "Python, SQL\n"
    )
    doc = reconstruct_cv_text(source)
    assert len(doc.sections) >= 2
    with pytest.raises(ValueError, match="source coverage diagnostics are missing"):
        validate_reconstruction_gate(doc)
