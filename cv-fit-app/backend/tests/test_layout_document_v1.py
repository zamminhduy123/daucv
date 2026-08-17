"""Tests for offline LayoutDocumentV1 extraction and visual segmentation."""

from app.models.layout_document_v1 import (
    LayoutDocumentV1,
    LayoutLineV1,
    LayoutPageV1,
    SourceSpanV1,
)
from app.services.layout_document_v1_service import (
    _line_draft,
    audit_span_conservation,
    segment_visual_document,
)


def _line(
    line_id: str,
    text: str,
    bbox: tuple[float, float, float, float],
    *,
    bullet: bool = False,
) -> tuple[LayoutLineV1, SourceSpanV1]:
    span_id = f"{line_id}-s1"
    return (
        LayoutLineV1(
            line_id=line_id,
            page=1,
            bbox=bbox,
            text=text,
            span_ids=[span_id],
            is_bullet=bullet,
        ),
        SourceSpanV1(span_id=span_id, line_id=line_id, text=text, bbox=bbox),
    )


def _zalo_layout_document() -> LayoutDocumentV1:
    pairs = [
        _line("p1-l1", "Experience", (40, 350, 160, 362)),
        _line("p1-l2", "Zalo – VNG Corporation", (40, 384, 166, 394)),
        _line("p1-l3", "Ho Chi Minh City, Vietnam", (459, 385, 572, 394)),
        _line("p1-l4", "Software Engineer, Zalo PC", (40, 397, 152, 406)),
        _line("p1-l5", "May 2022 – Mar 2024", (482, 397, 572, 406)),
        _line(
            "p1-l6", "– Shipped production features.", (51, 416, 508, 426), bullet=True
        ),
    ]
    return LayoutDocumentV1(
        pages=[
            LayoutPageV1(
                page=1, width=612, height=792, lines=[line for line, _ in pairs]
            )
        ],
        spans=[span for _, span in pairs],
    )


def test_layout_document_keeps_inter_span_whitespace_exactly() -> None:
    raw_line = {
        "bbox": (40, 100, 300, 112),
        "spans": [
            {
                "bbox": (40, 100, 100, 112),
                "font": "Test",
                "size": 10,
                "flags": 0,
                "chars": [
                    {"c": value, "bbox": (40 + index, 100, 41 + index, 112)}
                    for index, value in enumerate("Achieved ")
                ],
            },
            {
                "bbox": (101, 100, 250, 112),
                "font": "Test",
                "size": 10,
                "flags": 0,
                "chars": [
                    {"c": value, "bbox": (101 + index, 100, 102 + index, 112)}
                    for index, value in enumerate("state-of-the-art results")
                ],
            },
        ],
    }

    draft = _line_draft(page_number=1, line_sequence=1, raw_line=raw_line)

    assert draft is not None
    assert draft.line.text == "Achieved state-of-the-art results"
    assert [word.text for word in draft.words] == [
        "Achieved",
        "state-of-the-art",
        "results",
    ]


def test_visual_segmenter_builds_one_geometry_preserving_zalo_record() -> None:
    document = _zalo_layout_document()

    visual = segment_visual_document(document)
    audit = audit_span_conservation(document, visual)

    section = visual.sections[0]
    record = section.records[0]
    assert section.type == "experience"
    assert record.header_row_ids == ["p1-r2", "p1-r3"]
    assert record.header_line_ids == ["p1-l2", "p1-l3", "p1-l4", "p1-l5"]
    assert record.bullet_groups[0].line_ids == ["p1-l6"]
    assert audit.passes
    assert audit.missing_span_ids == []
    assert audit.duplicate_span_ids == []
