"""Unit tests for RawExtraction, ExtractionDecision, provenance finalization, and semantic omission audit."""

import pytest

from app.models.cv_document_v2 import (
    CVDocumentV2,
    CVIdentity,
    CVParagraphBlock,
    LLMUnmappedReference,
)
from app.models.cv_raw_extraction import (
    ExtractionMethod,
    ExtractionReason,
    InvalidRawExtractionError,
    RawBlock,
    RawExtraction,
    RawPage,
)
from app.services.cv_reconstruction_service import (
    InvalidSourceReferenceError,
    audit_semantic_omissions,
    finalize_document_provenance,
)
from app.services.layout_extraction import (
    evaluate_extraction,
    validate_raw_extraction,
)


def test_raw_extraction_models() -> None:
    raw = RawExtraction(
        method=ExtractionMethod.NATIVE_BLOCKS,
        pages=[
            RawPage(
                page=1,
                width=612.0,
                height=792.0,
                blocks=[
                    RawBlock(
                        block_id="p1-b1",
                        page=1,
                        text="Duy Nguyen\nSoftware Engineer",
                        bbox=(36.0, 36.0, 300.0, 80.0),
                        extraction_method=ExtractionMethod.NATIVE_BLOCKS,
                        confidence=1.0,
                    ),
                    RawBlock(
                        block_id="p1-b2",
                        page=1,
                        text="EXPERIENCE\nBackend Developer at Bé Đậu",
                        bbox=(36.0, 100.0, 300.0, 300.0),
                        extraction_method=ExtractionMethod.NATIVE_BLOCKS,
                        confidence=1.0,
                    ),
                ],
            )
        ],
    )

    validate_raw_extraction(raw)
    assert raw.method == ExtractionMethod.NATIVE_BLOCKS
    assert len(raw.pages[0].blocks) == 2


def test_column_aware_spatial_block_sorting() -> None:
    from app.services.layout_extraction import sort_raw_page_blocks

    blocks = [
        RawBlock(
            block_id="b1",
            page=1,
            text="NGUYEN THANH MINH DUY",
            bbox=(36, 40, 500, 80),
            extraction_method=ExtractionMethod.NATIVE_BLOCKS,
        ),
        RawBlock(
            block_id="b2",
            page=1,
            text="SUMMARY: AI researcher...",
            bbox=(36, 110, 320, 180),
            extraction_method=ExtractionMethod.NATIVE_BLOCKS,
        ),
        RawBlock(
            block_id="b3",
            page=1,
            text="EXPERIENCE: Independent Builder...",
            bbox=(36, 200, 320, 500),
            extraction_method=ExtractionMethod.NATIVE_BLOCKS,
        ),
        RawBlock(
            block_id="b4",
            page=1,
            text="STRENGTHS: Problem Solving...",
            bbox=(360, 110, 550, 200),
            extraction_method=ExtractionMethod.NATIVE_BLOCKS,
        ),
        RawBlock(
            block_id="b5",
            page=1,
            text="MOST PROUD OF: Your Achievement...",
            bbox=(360, 220, 550, 320),
            extraction_method=ExtractionMethod.NATIVE_BLOCKS,
        ),
        RawBlock(
            block_id="b6",
            page=1,
            text="SKILLS: LLM Applications...",
            bbox=(360, 340, 550, 450),
            extraction_method=ExtractionMethod.NATIVE_BLOCKS,
        ),
        RawBlock(
            block_id="b7",
            page=1,
            text="www.enhancv.com Powered by Enhancv",
            bbox=(36, 750, 550, 770),
            extraction_method=ExtractionMethod.NATIVE_BLOCKS,
        ),
    ]

    sorted_b = sort_raw_page_blocks(blocks, page_width=612.0, page_height=792.0)
    sorted_texts = [b.text for b in sorted_b]

    assert sorted_texts[0] == "NGUYEN THANH MINH DUY"
    assert "SUMMARY" in sorted_texts[1]
    assert "EXPERIENCE" in sorted_texts[2]
    assert "STRENGTHS" in sorted_texts[3]
    assert "MOST PROUD OF" in sorted_texts[4]
    assert "SKILLS" in sorted_texts[5]
    assert "enhancv.com" in sorted_texts[6]


def test_validate_raw_extraction_duplicate_ids() -> None:
    raw = RawExtraction(
        method=ExtractionMethod.NATIVE_BLOCKS,
        pages=[
            RawPage(
                page=1,
                blocks=[
                    RawBlock(
                        block_id="p1-b1",
                        page=1,
                        text="Text 1",
                        extraction_method=ExtractionMethod.NATIVE_BLOCKS,
                    ),
                    RawBlock(
                        block_id="p1-b1",
                        page=1,
                        text="Text 2",
                        extraction_method=ExtractionMethod.NATIVE_BLOCKS,
                    ),
                ],
            )
        ],
    )
    with pytest.raises(InvalidRawExtractionError):
        validate_raw_extraction(raw)


def test_evaluate_extraction_quality() -> None:
    raw_usable = RawExtraction(
        method=ExtractionMethod.NATIVE_BLOCKS,
        pages=[
            RawPage(
                page=1,
                blocks=[
                    RawBlock(
                        block_id="p1-b1",
                        page=1,
                        text="NGUYEN THANH MINH DUY\nAI Engineer\nEmail: duy@example.com\nPhone: +84 123 456 789\n"
                        "Summary: Experienced machine learning engineer with over 5 years of experience building scalable AI platforms.\n"
                        "Work Experience: Senior AI Engineer at Tech Company. Developed production LLM pipelines.",
                        bbox=(36.0, 36.0, 300.0, 300.0),
                        extraction_method=ExtractionMethod.NATIVE_BLOCKS,
                    )
                ],
            )
        ],
    )
    decision = evaluate_extraction(raw_usable)
    assert decision.usable is True
    assert len(decision.reasons) == 0

    raw_short = RawExtraction(
        method=ExtractionMethod.NATIVE_BLOCKS,
        pages=[
            RawPage(
                page=1,
                blocks=[
                    RawBlock(
                        block_id="p1-b1",
                        page=1,
                        text="Short",
                        bbox=(36.0, 36.0, 100.0, 50.0),
                        extraction_method=ExtractionMethod.NATIVE_BLOCKS,
                    )
                ],
            )
        ],
    )
    decision_short = evaluate_extraction(raw_short)
    assert decision_short.usable is False
    assert ExtractionReason.TEXT_TOO_SHORT in decision_short.reasons


def test_finalize_document_provenance_and_unmapped_population() -> None:
    raw = RawExtraction(
        method=ExtractionMethod.NATIVE_BLOCKS,
        pages=[
            RawPage(
                page=1,
                blocks=[
                    RawBlock(
                        block_id="p1-b1",
                        page=1,
                        text="Nguyen Minh Duy\nAI Engineer",
                        extraction_method=ExtractionMethod.NATIVE_BLOCKS,
                    ),
                    RawBlock(
                        block_id="p1-b2",
                        page=1,
                        text="Summary: AI practitioner with 5 years experience.",
                        extraction_method=ExtractionMethod.NATIVE_BLOCKS,
                    ),
                    RawBlock(
                        block_id="p1-b3",
                        page=1,
                        text="Decorative footer line 2026",
                        extraction_method=ExtractionMethod.NATIVE_BLOCKS,
                    ),
                    RawBlock(
                        block_id="p1-b4",
                        page=1,
                        text="Omitted extra section line",
                        extraction_method=ExtractionMethod.NATIVE_BLOCKS,
                    ),
                ],
            )
        ],
    )

    doc = CVDocumentV2(
        identity=CVIdentity(
            full_name="Nguyen Minh Duy",
            headline="AI Engineer",
            source_block_ids=["p1-b1"],
        ),
        summary=CVParagraphBlock(
            text="AI practitioner with 5 years experience.",
            source_block_ids=["p1-b2"],
        ),
    )

    llm_unmapped = [
        LLMUnmappedReference(
            block_id="p1-b3", reason="decorative_content", confidence=0.9
        )
    ]

    final_doc = finalize_document_provenance(raw, doc, llm_unmapped)

    # The summary value maps, but its alphanumeric "Summary:" label remains
    # substantive. It must be retained alongside the LLM-tagged footer and
    # wholly omitted fourth block.
    assert len(final_doc.unmapped_content) == 3

    u_b2 = next(u for u in final_doc.unmapped_content if u.block_id == "p1-b2")
    assert "Summary" in u_b2.text
    assert u_b2.reason == "parser_omission"

    u_b3 = next(u for u in final_doc.unmapped_content if u.block_id == "p1-b3")
    assert u_b3.text == "Decorative footer line 2026"
    assert u_b3.reason == "decorative_content"
    assert u_b3.page == 1

    u_b4 = next(u for u in final_doc.unmapped_content if u.block_id == "p1-b4")
    assert u_b4.text == "Omitted extra section line"
    assert u_b4.reason == "parser_omission"
    assert u_b4.page == 1


def test_finalize_document_provenance_rejects_unknown_ids() -> None:
    raw = RawExtraction(
        method=ExtractionMethod.NATIVE_BLOCKS,
        pages=[
            RawPage(
                page=1,
                blocks=[
                    RawBlock(
                        block_id="p1-b1",
                        page=1,
                        text="Valid Block",
                        extraction_method=ExtractionMethod.NATIVE_BLOCKS,
                    )
                ],
            )
        ],
    )

    doc = CVDocumentV2(
        identity=CVIdentity(
            full_name="Fake Name",
            source_block_ids=["p1-b999"],
        )
    )

    with pytest.raises(InvalidSourceReferenceError):
        finalize_document_provenance(raw, doc)


def test_audit_semantic_omissions() -> None:
    raw = RawExtraction(
        method=ExtractionMethod.NATIVE_BLOCKS,
        pages=[
            RawPage(
                page=1,
                blocks=[
                    RawBlock(
                        block_id="p1-b1",
                        page=1,
                        text="Minh Duy\nEmail: minhduy@example.com\nPhone: +84 335 452 060",
                        extraction_method=ExtractionMethod.NATIVE_BLOCKS,
                    )
                ],
            )
        ],
    )

    doc_missing_info = CVDocumentV2(
        identity=CVIdentity(
            full_name="Minh Duy",
            source_block_ids=["p1-b1"],
            # email and phone omitted
        )
    )

    warnings = audit_semantic_omissions(raw, doc_missing_info)
    assert len(warnings) == 2
    assert any("minhduy@example.com" in w for w in warnings)
    assert any("+84 335 452 060" in w for w in warnings)
