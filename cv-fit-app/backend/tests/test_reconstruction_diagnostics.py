import pytest

from app.models.cv_document_v2 import (
    ContentOrigin,
    CVDocumentV2,
    CVParagraphBlock,
    CVReconstructionDiagnostics,
    CVSection,
    CVSourceCoverageDiagnostics,
    CVUnknownBlock,
)
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


def _provenance_gap_doc(
    *,
    carrier_origin: ContentOrigin = ContentOrigin.EXTRACTED,
    with_reviewed_block: bool = False,
    keep_carrier: bool = True,
    doc_warnings: list[str] | None = None,
) -> CVDocumentV2:
    blocks: list[CVParagraphBlock] = []
    if keep_carrier:
        blocks.append(
            CVParagraphBlock(
                block_id="b-gap",
                text="Built data pipelines.",
                origin=carrier_origin,
                reconstruction_warnings=["missing_line_provenance"],
            )
        )
    blocks.append(
        CVParagraphBlock(
            block_id="b-ok",
            text="Led a team of three.",
            origin=ContentOrigin.USER_EDIT
            if with_reviewed_block
            else ContentOrigin.EXTRACTED,
        )
    )
    return CVDocumentV2(
        sections=[
            CVSection(
                id="experience",
                type="experience",
                title="EXPERIENCE",
                blocks=blocks,
            )
        ],
        reconstruction_warnings=(
            doc_warnings if doc_warnings is not None else ["missing_line_provenance"]
        ),
        reconstruction_diagnostics=CVReconstructionDiagnostics(
            source_coverage=CVSourceCoverageDiagnostics(
                raw_block_count=2,
                accounted_block_count=2,
                significant_character_count=10,
                mapped_character_count=10,
                coverage_ratio=1.0,
            )
        ),
    )


def test_gate_still_rejects_untouched_provenance_gap() -> None:
    doc = _provenance_gap_doc()
    with pytest.raises(ValueError, match="missing_line_provenance"):
        validate_reconstruction_gate(doc)


def test_gate_allows_user_edited_provenance_carrier() -> None:
    doc = _provenance_gap_doc(carrier_origin=ContentOrigin.USER_EDIT)
    validate_reconstruction_gate(doc)


def test_gate_allows_provenance_gap_with_review_evidence_elsewhere() -> None:
    doc = _provenance_gap_doc(with_reviewed_block=True)
    validate_reconstruction_gate(doc)


def test_gate_allows_stale_provenance_lift_after_block_removal() -> None:
    doc = _provenance_gap_doc(keep_carrier=False)
    validate_reconstruction_gate(doc)


def test_gate_exemption_is_scoped_to_provenance_warning() -> None:
    doc = _provenance_gap_doc(
        with_reviewed_block=True,
        doc_warnings=["missing_line_provenance", "ambiguous_entry_boundary"],
    )
    with pytest.raises(ValueError, match="ambiguous_entry_boundary"):
        validate_reconstruction_gate(doc)


def test_gate_allows_attested_doc_with_untouched_provenance_gap() -> None:
    doc = _provenance_gap_doc()
    doc.review_attested = True
    validate_reconstruction_gate(doc)


def test_gate_attestation_does_not_cover_other_critical_warnings() -> None:
    doc = _provenance_gap_doc(
        doc_warnings=["missing_line_provenance", "duplicate_line_ownership"],
    )
    doc.review_attested = True
    with pytest.raises(ValueError, match="duplicate_line_ownership"):
        validate_reconstruction_gate(doc)


def test_backfill_source_block_citations_from_line_ids() -> None:
    from app.models.cv_raw_extraction import (
        ExtractionMethod,
        RawBlock,
        RawExtraction,
        RawPage,
    )
    from app.services.cv_reconstruction_service import backfill_source_block_citations

    raw = RawExtraction(
        method=ExtractionMethod.NATIVE_BLOCKS,
        pages=[
            RawPage(
                page=1,
                blocks=[
                    RawBlock(
                        block_id="p1-b1",
                        page=1,
                        text="Built APIs.",
                        extraction_method=ExtractionMethod.NATIVE_BLOCKS,
                    ),
                    RawBlock(
                        block_id="p1-b2",
                        page=1,
                        text="Led team.",
                        extraction_method=ExtractionMethod.NATIVE_BLOCKS,
                    ),
                ],
            )
        ],
    )
    doc = CVDocumentV2(
        sections=[
            CVSection(
                id="experience",
                type="experience",
                title="EXPERIENCE",
                blocks=[
                    CVParagraphBlock(
                        block_id="b-cited",
                        text="Built APIs.",
                        source_line_ids=["p1-b1"],
                    ),
                    CVParagraphBlock(
                        block_id="b-user",
                        text="User added.",
                        origin=ContentOrigin.USER_EDIT,
                    ),
                ],
            )
        ],
    )
    filled = backfill_source_block_citations(doc, raw)
    assert filled == 1
    by_id = {b.block_id: b for s in doc.sections for b in s.blocks}
    assert by_id["b-cited"].source_block_ids == ["p1-b1"]
    assert by_id["b-user"].source_block_ids == []
    # Idempotent: second run fills nothing and never overrides.
    assert backfill_source_block_citations(doc, raw) == 0
