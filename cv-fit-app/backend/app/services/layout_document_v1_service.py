"""Offline lossless layout extraction and visual-record segmentation.

This is intentionally not wired into the CV pipeline.  It is the acceptance
foundation for replacing the current atom planners, which discard PDF layout
before semantic decisions are made.
"""

from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass
from typing import Any

import fitz

from app.models.layout_document_v1 import (
    LayoutConservationAudit,
    LayoutDocumentV1,
    LayoutLineV1,
    LayoutPageV1,
    LayoutWordV1,
    SourceSpanV1,
    VisualBulletGroupV1,
    VisualDocumentV1,
    VisualRecordV1,
    VisualRowV1,
    VisualSectionV1,
)
from app.services.section_vocabulary import classify_heading

_BULLET_RE = re.compile(r"^\s*(?:[-–—•▪‣])\s+")
_WORD_RE = re.compile(r"\S+")
_ROW_TOLERANCE = 3.0
_HEADER_ROW_GAP = 20.0


@dataclass(frozen=True)
class _LineDraft:
    line: LayoutLineV1
    spans: list[SourceSpanV1]
    words: list[LayoutWordV1]


def _bbox_union(
    boxes: list[tuple[float, float, float, float]],
) -> tuple[float, float, float, float]:
    return (
        min(box[0] for box in boxes),
        min(box[1] for box in boxes),
        max(box[2] for box in boxes),
        max(box[3] for box in boxes),
    )


def _raw_span_text(raw_span: dict[str, Any]) -> str:
    chars = raw_span.get("chars", [])
    if chars:
        return "".join(str(char.get("c", "")) for char in chars)
    return str(raw_span.get("text", ""))


def _word_boxes(
    raw_spans: list[dict[str, Any]],
) -> list[tuple[str, tuple[float, float, float, float], list[int]]]:
    """Build words from characters, retaining true PDF whitespace."""
    characters: list[tuple[str, tuple[float, float, float, float], int]] = []
    for span_index, raw_span in enumerate(raw_spans):
        chars = raw_span.get("chars", [])
        if chars:
            for char in chars:
                bbox = tuple(float(value) for value in char["bbox"][:4])
                characters.append((str(char.get("c", "")), bbox, span_index))
            continue
        text = _raw_span_text(raw_span)
        bbox = tuple(float(value) for value in raw_span["bbox"][:4])
        characters.extend((char, bbox, span_index) for char in text)

    result: list[tuple[str, tuple[float, float, float, float], list[int]]] = []
    current: list[tuple[str, tuple[float, float, float, float], int]] = []
    for item in characters:
        if item[0].isspace():
            if current:
                result.append(
                    (
                        "".join(char for char, _, _ in current),
                        _bbox_union([bbox for _, bbox, _ in current]),
                        list(dict.fromkeys(span_index for _, _, span_index in current)),
                    )
                )
                current = []
        else:
            current.append(item)
    if current:
        result.append(
            (
                "".join(char for char, _, _ in current),
                _bbox_union([bbox for _, bbox, _ in current]),
                list(dict.fromkeys(span_index for _, _, span_index in current)),
            )
        )
    return result


def _line_draft(
    *,
    page_number: int,
    line_sequence: int,
    raw_line: dict[str, Any],
) -> _LineDraft | None:
    raw_spans = [span for span in raw_line.get("spans", []) if _raw_span_text(span)]
    if not raw_spans:
        return None
    text = "".join(_raw_span_text(span) for span in raw_spans)
    if not text.strip():
        return None
    line_id = f"p{page_number}-l{line_sequence}"
    spans = [
        SourceSpanV1(
            span_id=f"{line_id}-s{index}",
            line_id=line_id,
            text=_raw_span_text(span),
            bbox=tuple(float(value) for value in span["bbox"][:4]),
            font=str(span.get("font")) if span.get("font") else None,
            font_size=float(span["size"]) if span.get("size") is not None else None,
            flags=int(span["flags"]) if span.get("flags") is not None else None,
        )
        for index, span in enumerate(raw_spans, start=1)
    ]
    words = [
        LayoutWordV1(
            word_id=f"{line_id}-w{index}",
            text=word_text,
            bbox=bbox,
            span_ids=[spans[span_index].span_id for span_index in span_indexes],
        )
        for index, (word_text, bbox, span_indexes) in enumerate(
            _word_boxes(raw_spans), start=1
        )
    ]
    line_bbox = tuple(float(value) for value in raw_line["bbox"][:4])
    return _LineDraft(
        line=LayoutLineV1(
            line_id=line_id,
            page=page_number,
            bbox=line_bbox,
            text=text,
            span_ids=[span.span_id for span in spans],
            word_ids=[word.word_id for word in words],
            is_bullet=bool(_BULLET_RE.match(text)),
        ),
        spans=spans,
        words=words,
    )


def extract_layout_document_v1(pdf_bytes: bytes) -> LayoutDocumentV1:
    """Extract a lossless layout document directly from PyMuPDF ``rawdict``."""
    pdf = fitz.open(stream=pdf_bytes, filetype="pdf")
    pages: list[LayoutPageV1] = []
    spans: list[SourceSpanV1] = []
    words: list[LayoutWordV1] = []
    try:
        for page_number, page in enumerate(pdf, start=1):
            drafts: list[_LineDraft] = []
            raw_page = page.get_text("rawdict", sort=False)
            sequence = 0
            for raw_block in raw_page.get("blocks", []):
                if raw_block.get("type") != 0:
                    continue
                for raw_line in raw_block.get("lines", []):
                    sequence += 1
                    draft = _line_draft(
                        page_number=page_number,
                        line_sequence=sequence,
                        raw_line=raw_line,
                    )
                    if draft:
                        drafts.append(draft)
            pages.append(
                LayoutPageV1(
                    page=page_number,
                    width=float(page.rect.width),
                    height=float(page.rect.height),
                    lines=[draft.line for draft in drafts],
                )
            )
            spans.extend(span for draft in drafts for span in draft.spans)
            words.extend(word for draft in drafts for word in draft.words)
    finally:
        pdf.close()
    return LayoutDocumentV1(pages=pages, spans=spans, words=words)


def _ordered_lines(document: LayoutDocumentV1) -> list[LayoutLineV1]:
    return sorted(
        (line for page in document.pages for line in page.lines),
        key=lambda line: (line.page, line.bbox[1], line.bbox[0]),
    )


def build_visual_rows(document: LayoutDocumentV1) -> list[VisualRowV1]:
    """Group same-baseline lines into visual rows, preserving left/right cells."""
    rows: list[VisualRowV1] = []
    for line in _ordered_lines(document):
        if (
            rows
            and rows[-1].page == line.page
            and abs(rows[-1].bbox[1] - line.bbox[1]) <= _ROW_TOLERANCE
        ):
            previous = rows[-1]
            rows[-1] = VisualRowV1(
                row_id=previous.row_id,
                page=previous.page,
                bbox=_bbox_union([previous.bbox, line.bbox]),
                line_ids=[*previous.line_ids, line.line_id],
            )
            continue
        rows.append(
            VisualRowV1(
                row_id=f"p{line.page}-r{len([row for row in rows if row.page == line.page]) + 1}",
                page=line.page,
                bbox=line.bbox,
                line_ids=[line.line_id],
            )
        )
    return rows


def _line_map(document: LayoutDocumentV1) -> dict[str, LayoutLineV1]:
    return {line.line_id: line for page in document.pages for line in page.lines}


def _span_ids_for_lines(lines: list[LayoutLineV1]) -> list[str]:
    return [span_id for line in lines for span_id in line.span_ids]


def _group_bullets(
    lines: list[LayoutLineV1],
) -> tuple[list[VisualBulletGroupV1], list[LayoutLineV1]]:
    groups: list[list[LayoutLineV1]] = []
    residual: list[LayoutLineV1] = []
    current: list[LayoutLineV1] | None = None
    for line in lines:
        if line.is_bullet:
            current = [line]
            groups.append(current)
        elif current and line.bbox[0] >= current[0].bbox[0] + 5.0:
            current.append(line)
        else:
            residual.append(line)
            current = None
    return (
        [
            VisualBulletGroupV1(
                line_ids=[line.line_id for line in group],
                span_ids=_span_ids_for_lines(group),
            )
            for group in groups
        ],
        residual,
    )


def _record_for_section(
    section_type: str,
    section_rows: list[VisualRowV1],
    line_map: dict[str, LayoutLineV1],
    record_number: int,
) -> tuple[VisualRecordV1 | None, list[LayoutLineV1]]:
    lines = [line_map[line_id] for row in section_rows for line_id in row.line_ids]
    first_bullet = next(
        (index for index, line in enumerate(lines) if line.is_bullet), None
    )
    if first_bullet is None or first_bullet == 0:
        return None, lines
    header_lines = lines[:first_bullet]
    header_rows = [
        row
        for row in section_rows
        if any(
            line_id in {line.line_id for line in header_lines}
            for line_id in row.line_ids
        )
    ]
    if (
        len(header_rows) > 2
        or header_rows[-1].bbox[1] - header_rows[0].bbox[1] > _HEADER_ROW_GAP
    ):
        return None, lines
    bullets, residual = _group_bullets(lines[first_bullet:])
    return (
        VisualRecordV1(
            record_id=f"record-{record_number}",
            section_type=section_type,
            header_row_ids=[row.row_id for row in header_rows],
            header_line_ids=[line.line_id for line in header_lines],
            header_span_ids=_span_ids_for_lines(header_lines),
            bullet_groups=bullets,
        ),
        residual,
    )


def segment_visual_document(document: LayoutDocumentV1) -> VisualDocumentV1:
    """Build server-owned visual sections, entry headers, bullets, residuals."""
    rows = build_visual_rows(document)
    line_map = _line_map(document)
    heading_indexes = [
        index
        for index, row in enumerate(rows)
        if len(row.line_ids) == 1 and classify_heading(line_map[row.line_ids[0]].text)
    ]
    if not heading_indexes:
        return VisualDocumentV1(
            rows=rows,
            preamble_line_ids=[line.line_id for line in _ordered_lines(document)],
            preamble_span_ids=[span.span_id for span in document.spans],
        )
    preamble_rows = rows[: heading_indexes[0]]
    sections: list[VisualSectionV1] = []
    record_number = 0
    for heading_offset, heading_index in enumerate(heading_indexes):
        end = (
            heading_indexes[heading_offset + 1]
            if heading_offset + 1 < len(heading_indexes)
            else len(rows)
        )
        heading_row = rows[heading_index]
        heading_line = line_map[heading_row.line_ids[0]]
        section_type = classify_heading(heading_line.text)
        assert section_type is not None
        content_rows = rows[heading_index + 1 : end]
        record: VisualRecordV1 | None = None
        residual_lines = [
            line_map[line_id] for row in content_rows for line_id in row.line_ids
        ]
        if section_type[0] in {"experience", "projects"}:
            record_number += 1
            record, residual_lines = _record_for_section(
                section_type[0], content_rows, line_map, record_number
            )
        sections.append(
            VisualSectionV1(
                section_id=f"section-{heading_offset + 1}",
                type=section_type[0],
                heading_line_id=heading_line.line_id,
                heading_span_ids=heading_line.span_ids,
                records=[record] if record else [],
                residual_line_ids=[line.line_id for line in residual_lines],
                residual_span_ids=_span_ids_for_lines(residual_lines),
            )
        )
    preamble_lines = [
        line_map[line_id] for row in preamble_rows for line_id in row.line_ids
    ]
    return VisualDocumentV1(
        rows=rows,
        sections=sections,
        preamble_line_ids=[line.line_id for line in preamble_lines],
        preamble_span_ids=_span_ids_for_lines(preamble_lines),
    )


def audit_span_conservation(
    document: LayoutDocumentV1, visual: VisualDocumentV1
) -> LayoutConservationAudit:
    """Every meaningful source span must be assigned exactly once."""
    assigned = [*visual.preamble_span_ids]
    for section in visual.sections:
        assigned.extend(section.heading_span_ids)
        assigned.extend(section.residual_span_ids)
        for record in section.records:
            assigned.extend(record.header_span_ids)
            for bullet in record.bullet_groups:
                assigned.extend(bullet.span_ids)
    counts = Counter(assigned)
    source_ids = {span.span_id for span in document.spans}
    return LayoutConservationAudit(
        source_span_count=len(source_ids),
        assigned_span_count=len(assigned),
        missing_span_ids=sorted(source_ids - counts.keys()),
        duplicate_span_ids=sorted(
            span_id for span_id, count in counts.items() if count > 1
        ),
    )
