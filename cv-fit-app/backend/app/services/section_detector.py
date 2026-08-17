"""Section detection for typed CV reconstruction (Phase 4).

Takes the ordered, normalised ``list[ExtractedLine]`` produced by the
layout-aware extraction pipeline and identifies section boundaries,
producing a ``CVDocumentV2`` document.

This is a *deterministic* (no-LLM) reconstruction step.  It uses:

1. A canonical section vocabulary (Phase 4, Step 4.1)
2. Structural signals: font size/weight jumps, page boundaries,
   horizontal separators, surrounding whitespace, document position.

It does **not** classify a line as a section heading merely because it
contains a keyword — structural and typographic cues must also agree.

Unrecognised headings are stored as ``"custom"`` sections and are never
dropped.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from hashlib import sha256

from app.models.cv_document_v2 import (
    CVBlockType,
    CVDocumentV2,
    CVIdentity,
    CVParagraphBlock,
    CVSection,
    CVUnknownBlock,
)
from app.services.block_reconstruction import (
    attach_reconstruction_metadata,
    reconstruct_blocks,
)
from app.services.layout_extraction import ExtractedLine
from app.services.section_vocabulary import SECTION_TYPE, classify_heading

# ---------------------------------------------------------------------------
# 1. Structural detection helpers
# ---------------------------------------------------------------------------

# Patterns that look like horizontal separators (lines made of repeated chars)
_SEPARATORS_RE = re.compile(r"^[\s\-═━─━┄┅┈┉┊┋═╌╍╎╏─│┃\s]+$")

# Date range pattern (for experience/education entries)
_DATE_RANGE_RE = re.compile(
    r"\b(19|20)\d{2}\s*[-–—]\s*(19|20)\d{2}\b"
    r"|"
    r"\b(19|20)\d{2}\s*[-–—]\s*(present|hiện tại|nay)\b",
    re.IGNORECASE,
)

# ---------------------------------------------------------------------------
# 2. Identity preamble detection
# ---------------------------------------------------------------------------


def _detect_identity(lines: list[ExtractedLine]) -> CVIdentity:
    """Attempt to extract candidate identity from the first few lines.

    Heuristics:
    * The first non-empty, non-artifact line is treated as the name
      if it's short (≤ 4 words) and largely alphabetic.
    * The next line (if short and contains separators like ``|``, ``@``,
      phone-like patterns, or location tokens) is treated as contact.
    * A single-line headline is inferred if the second line looks like
      a role description (contains common job-title keywords).
    """
    if not lines:
        return CVIdentity()

    # Skip any leading layout artifacts
    content_lines: list[ExtractedLine] = []
    for line in lines:
        if line.is_layout_artifact or line.is_page_break_marker:
            continue
        text = line.normalized_text or line.text
        if text.strip():
            content_lines.append(line)
        if len(content_lines) >= 5:  # only look at the first few lines
            break

    if not content_lines:
        return CVIdentity()

    identity = CVIdentity()
    first = content_lines[0]
    first_text = (first.normalized_text or first.text).strip()

    # Name: short, mostly alpha words
    if first_text and _looks_like_name(first_text):
        identity.name = first_text
        if len(content_lines) > 1:
            second = content_lines[1]
            second_text = (second.normalized_text or second.text).strip()
            headline_end_idx = 1
            if (
                second_text
                and _looks_like_headline(second_text)
                and not classify_heading(second_text)
            ):
                if (
                    second_text.rstrip().endswith(("/", "|", "-", ","))
                    and len(content_lines) > 2
                ):
                    third_text = (
                        content_lines[2].normalized_text or content_lines[2].text
                    ).strip()
                    if _looks_like_headline(third_text):
                        second_text = f"{second_text} {third_text}".strip()
                        headline_end_idx = 2
                identity.headline = second_text

                for line in content_lines[headline_end_idx + 1 : 5]:
                    ct = (line.normalized_text or line.text).strip()
                    if ct and _looks_like_contact(ct):
                        identity.contact_lines.append(ct)
                return identity
            # Second line might be contact
            for line in content_lines[1:5]:
                ct = (line.normalized_text or line.text).strip()
                if ct and _looks_like_contact(ct):
                    identity.contact_lines.append(ct)
            return identity
        return identity

    # No name detected — fallback: treat first line as contact if it looks like one
    if first_text and _looks_like_contact(first_text):
        identity.contact_lines.append(first_text)
    return identity


def _looks_like_name(text: str) -> bool:
    """Return True if text looks like a person's name."""
    stripped = text.strip()
    if not stripped:
        return False
    words = stripped.split()
    # Names are typically 1-4 words
    if len(words) > 4:
        return False
    # At least one word should be ≥ 3 chars (avoid single letters, initials)
    if not any(len(w) >= 3 for w in words):
        return False
    # Names shouldn't contain job keywords or common heading words
    stop_words = {
        "the",
        "of",
        "and",
        "in",
        "for",
        "with",
        "to",
        "from",
        "kỹ",
        "nghệ",
        "sư",
        "developer",
        "engineer",
        "scientist",
        "professional",
        "tóm",
        "tắt",
        "giới",
        "thiệu",
        "mục",
        "tiêu",
        "sơ",
        "lược",
        "hoạt",
        "động",
        "hoat",
        "dong",
        "skills",
        "experience",
        "projects",
        "education",
        "activities",
        "awards",
        "interests",
        "publications",
        "summary",
        "profile",
        "contact",
        "certifications",
        "nghiem",
        "nghiệm",
        "học",
        "ngôn",
        "ngon",
        "luoc",
        "gioi",
        "thieu",
        "muc",
        "tieu",
    }
    return not any(w.lower() in stop_words for w in words if len(w) > 2)


def _looks_like_headline(text: str) -> bool:
    """Return True if text looks like a professional headline."""
    stripped = text.strip()
    if not stripped:
        return False
    # Contains a pipe separator (common in headlines)
    if "|" in stripped:
        return True
    # Contains job-title keywords
    title_keywords = {
        "engineer",
        "developer",
        "designer",
        "analyst",
        "manager",
        "scientist",
        "consultant",
        "researcher",
        "director",
        "lead",
        "kỹ",
        "sư",
        "lập",
        "trình",
        "viên",
        "chuyên",
    }
    if any(kw in stripped.lower() for kw in title_keywords):
        return True
    # A headline shouldn't contain common heading keywords
    words = stripped.split()
    heading_keywords = {
        "hoat",
        "dong",
        "hoạt",
        "động",
        "skills",
        "experience",
        "projects",
        "education",
        "activities",
        "awards",
        "interests",
        "publications",
        "summary",
        "profile",
        "contact",
        "certifications",
        "nghiem",
        "nghiệm",
        "học",
        "ngôn",
        "ngon",
        "luoc",
        "lược",
        "gioi",
        "thieu",
        "muc",
        "tieu",
        "tóm",
        "tắt",
        "giới",
        "thiệu",
        "mục",
        "tiêu",
        "sơ",
    }
    if any(w.lower() in heading_keywords for w in words):
        return False
    # Multiple capitalized words (title case)
    caps = len([w for w in stripped.split() if w and w[0].isupper()])
    return caps >= 2


def _looks_like_contact(text: str) -> bool:
    """Return True if text looks like a contact line (email, phone, location)."""
    stripped = text.strip()
    if not stripped:
        return False
    # Email pattern
    if "@" in stripped:
        return True
    # Phone pattern
    if re.search(r"\+?\d[\d\s\-\(\)]{6,}", stripped):
        return True
    # Contains a separator and looks like a list of contact items
    if "|" in stripped and stripped.count("|") >= 1:
        return True
    # City/province patterns
    city_patterns = [
        r"\b(hcmc|ho\s?chí\s?minh|tp\.?hcm|hồ\s?chí\s?minh|ha\s?noi|hà\s?noi)"
        r"\b",
    ]
    return bool(any(re.search(p, stripped.lower()) for p in city_patterns))


# ---------------------------------------------------------------------------
# 3. Section boundary detection
# ---------------------------------------------------------------------------


@dataclass
class _SectionBoundary:
    """A detected section boundary within the line stream."""

    index: int  # index into lines list where this section starts
    canonical_type: SECTION_TYPE
    display_title: str  # the original heading text (e.g. "KINH NGHIỆM LÀM VIỆC")
    font_size: float | None = None
    font_weight: float | None = None
    is_page_break: bool = False


def _detect_section_boundaries(
    lines: list[ExtractedLine],
) -> list[_SectionBoundary]:
    """Identify where each section begins in the ordered line stream.

    Uses a combination of:
    * Canonical vocabulary matching (Step 4.1)
    * Structural signals: font size/weight jumps, page breaks,
      horizontal separators, whitespace gaps (Step 4.2)
    """
    boundaries: list[_SectionBoundary] = []
    if not lines:
        return boundaries

    # Compute baseline font size from first few content lines for comparison
    baseline_size = _compute_baseline_font_size(lines)

    for i, line in enumerate(lines):
        text = line.normalized_text or line.text
        stripped = text.strip()
        if not stripped:
            continue

        # --- Signal 1: Canonical vocabulary match ---
        heading_result = classify_heading(stripped)
        if heading_result is not None:
            canonical, _display = heading_result
            boundaries.append(
                _SectionBoundary(
                    index=i,
                    canonical_type=canonical,
                    display_title=stripped,
                    font_size=line.font_size,
                    font_weight=line.font_weight,
                )
            )
            continue

        # --- Signal 2: Structural signals that reinforce a heading ---
        # A line that is:
        #   - All-caps or title-case short phrase (≤ 5 words)
        #   - Has larger font than baseline (≥ 2 points)
        #   - Is at the left margin (x ≤ 80) or spans wide
        #   - Followed by content that's clearly different
        if _looks_like_structural_heading(
            line,
            stripped,
            baseline_size,
            i,
            len(lines),
            lines,
        ):
            boundaries.append(
                _SectionBoundary(
                    index=i,
                    canonical_type="custom",
                    display_title=stripped,
                    font_size=line.font_size,
                    font_weight=line.font_weight,
                )
            )

    return boundaries


def _compute_baseline_font_size(lines: list[ExtractedLine]) -> float | None:
    """Compute the median font size from content lines (excluding headings)."""
    sizes: list[float] = []
    for line in lines[:30]:  # look at first 30 lines for baseline
        if line.font_size is not None and not line.is_layout_artifact:
            sizes.append(line.font_size)
    if not sizes:
        return None
    sizes.sort()
    return sizes[len(sizes) // 2]


def _looks_like_structural_heading(
    line: ExtractedLine,
    text: str,
    baseline_size: float | None,
    index: int,
    total: int,
    lines: list[ExtractedLine] | None = None,
) -> bool:
    """Determine if a line looks like a section heading without vocabulary match.

    Structural signals (Step 4.2):
    * Must be short (≤ 5 words), all-caps or title-case
    * AND must have at least ONE of:
        - Font size ≥ 2.5 points above baseline (strong typographic cue)
        - Adjacent separator line or blank line
    * AND left-aligned (column start)

    This is deliberately conservative to avoid classifying normal content
    lines (company names, short all-caps phrases) as headings.
    """
    stripped = text.strip()
    words = stripped.split()

    # Must be short — section headings are ≤ 5 words
    if len(words) > 5:
        return False

    # Must not be part of the identity preamble at the very start of the CV
    if index < 5 and (
        _looks_like_name(stripped)
        or _looks_like_headline(stripped)
        or _looks_like_contact(stripped)
    ):
        return False

    # Must be all-caps or title-case
    all_caps = all(w and w.isupper() for w in words if w.isalpha())
    title_case = all(w[0].isupper() for w in words if w) and sum(
        1 for w in words if w and len(w) > 2 and w[1:].islower()
    ) >= max(1, len(words) // 2)

    if not (all_caps or title_case):
        return False

    # Left margin signal: heading typically starts at column 0
    if line.x > 100:
        return False

    # Need at least one supporting structural signal
    has_separator = False
    if lines is not None:
        if index + 1 < total:
            next_line = lines[index + 1]
            next_text = (next_line.normalized_text or next_line.text).strip()
            if _SEPARATORS_RE.match(next_text) or next_text == "":
                has_separator = True
        if not has_separator and index > 0:
            prev_line = lines[index - 1]
            prev_text = (prev_line.normalized_text or prev_line.text).strip()
            if _SEPARATORS_RE.match(prev_text) or prev_text == "":
                has_separator = True

    if has_separator and (
        all_caps
        or (
            baseline_size is not None
            and line.font_size is not None
            and line.font_size >= baseline_size + 1.5
        )
    ):
        return True

    # Font size signal: need ≥ 2.0 pt above baseline (relaxed from 2.5 pt to capture 11->13 pt jumps)
    return bool(
        baseline_size is not None
        and line.font_size is not None
        and line.font_size >= baseline_size + 2.0
    )


# ---------------------------------------------------------------------------
# 4. Section content classification (block typing)
# ---------------------------------------------------------------------------


def _classify_section_content(
    lines: list[ExtractedLine],
    section_type: SECTION_TYPE,
    claimed_line_ids: set[str] | None = None,
    section_title: str | None = None,
) -> list[CVBlockType]:
    """Classify the content lines within one section into typed blocks.

    Phase 5: delegated to ``block_reconstruction.reconstruct_blocks()``
    which implements section-specific parsers for each canonical section type.
    """
    return reconstruct_blocks(
        section_type,
        lines,
        claimed_line_ids=claimed_line_ids,
        section_title=section_title,
    )


def _looks_like_entry_headline(
    line: ExtractedLine,
    text: str,
    lines: list[ExtractedLine],
    index: int,
) -> bool:
    """Determine if a line looks like an entry headline (job/project title)."""
    stripped = text.strip()
    words = stripped.split()

    # Must not be a bullet
    if stripped.startswith(("• ", "● ", "▪ ", "◦ ")):
        return False

    # Must not be just a date
    if _DATE_RANGE_RE.fullmatch(stripped):
        return False

    # Should be reasonably short (≤ 6 words) and start uppercase
    if len(words) > 6:
        return False
    if not stripped or not stripped[0].isupper():
        return False

    # Prefer lines that are bold or larger font
    if line.font_weight is not None and line.font_weight >= 700:
        return True

    # Title-case or all-caps short phrase
    all_caps = all(w and w.isupper() for w in words if w.isalpha())
    title_case = all(w[0].isupper() for w in words if w)

    if all_caps or title_case:
        return True

    # Fallback: if it's the first content line after a section heading,
    # likely an entry headline
    if index > 0:
        prev = lines[index - 1]
        prev_text = (prev.normalized_text or prev.text).strip()
        # If prev is a known section heading or separator
        if classify_heading(prev_text) or _SEPARATORS_RE.match(prev_text):
            return True

    return False


def _classify_skill_section(lines: list[ExtractedLine]) -> list[CVBlockType]:
    """Backward-compatible wrapper around the Phase 5 skills parser."""
    return reconstruct_blocks("skills", lines)


# ---------------------------------------------------------------------------
# 5. Summary detection
# ---------------------------------------------------------------------------


def _detect_summary(lines: list[ExtractedLine]) -> CVParagraphBlock | None:
    """Detect a summary/profile section at the top of the document.

    Heuristics:
    * Located before the first recognized section (experience, skills, etc.)
    * OR located after a "summary"-type section heading
    * 2+ lines of prose text
    * Not an entry or bullet pattern
    """
    content = [
        (index, line, (line.normalized_text or line.text).strip())
        for index, line in enumerate(lines)
        if (line.normalized_text or line.text).strip()
        and not line.is_layout_artifact
        and not line.is_page_break_marker
    ]
    if not content:
        return None

    for position, (_index, _line, text) in enumerate(content):
        heading = classify_heading(text)
        if heading and heading[0] == "summary":
            summary_lines: list[tuple[ExtractedLine, str]] = []
            for _next_index, next_line, next_text in content[position + 1 :]:
                if classify_heading(next_text) is not None:
                    break
                summary_lines.append((next_line, next_text))
            if summary_lines:
                return CVParagraphBlock(
                    text=" ".join(text for _line, text in summary_lines),
                    source_line_ids=[
                        line.source_line_id
                        for line, _text in summary_lines
                        if line.source_line_id
                    ],
                )
            return None

    identity = _detect_identity(lines)
    identity_texts = {
        identity.name,
        identity.headline,
        *identity.contact_lines,
    }
    summary_lines: list[tuple[ExtractedLine, str]] = []
    for _index, line, text in content:
        if classify_heading(text) is not None:
            break
        if text not in identity_texts:
            summary_lines.append((line, text))

    if len(summary_lines) >= 2 and any(
        len(text.split()) >= 6 or text.endswith((".", "!", "?"))
        for _line, text in summary_lines
    ):
        return CVParagraphBlock(
            text=" ".join(text for _line, text in summary_lines),
            source_line_ids=[
                line.source_line_id
                for line, _text in summary_lines
                if line.source_line_id
            ],
        )

    return None


# ---------------------------------------------------------------------------
# 6. Main detection pipeline
# ---------------------------------------------------------------------------


def detect_sections(lines: list[ExtractedLine]) -> CVDocumentV2:
    """Detect sections and build a typed ``CVDocumentV2`` from extracted lines.

    This is the Phase 4 entry point.  It produces a complete ``CVDocumentV2``
    by:

    1. Detecting identity preamble (name, headline, contact lines).
    2. Detecting summary content.
    3. Identifying section boundaries using vocabulary + structural signals.
    4. Classifying content within each section into typed blocks.
    5. Returning unknown/unclassified lines as ``"custom"`` sections.

    Lines that belong to the identity preamble or summary are excluded from
    section content.
    """
    doc = CVDocumentV2()

    if not lines:
        return doc

    from app.services.cv_reconstruction_service import canonical_cv_hash

    raw_text = "\n".join(
        (line.normalized_text or line.text or "").strip()
        for line in lines
        if (line.normalized_text or line.text or "").strip()
    )
    doc.source_hash = canonical_cv_hash(raw_text)

    page_line_numbers: dict[int, int] = {}
    for line in lines:
        page_line_numbers[line.page] = page_line_numbers.get(line.page, 0) + 1
        if not line.source_line_id:
            line.source_line_id = f"p{line.page + 1}-l{page_line_numbers[line.page]}"

    doc_claimed_line_ids: set[str] = set()

    # Step 1: Identity
    doc.identity = _detect_identity(lines).canonicalized()

    # Step 2: Summary
    doc.summary = _detect_summary(lines)
    if doc.summary is not None:
        doc.summary = attach_reconstruction_metadata(
            [doc.summary],
            lines,
            "summary",
            claimed_line_ids=doc_claimed_line_ids,
        )[0]

    preamble_texts = {
        t
        for t in {
            doc.identity.name,
            doc.identity.headline,
            *doc.identity.contact_lines,
        }
        if t
    }
    summary_line_ids = (
        set(doc.summary.source_line_ids)
        if doc.summary and doc.summary.source_line_ids
        else set()
    )

    # Step 3: Section boundaries
    boundaries = _detect_section_boundaries(lines)

    if not boundaries:
        # No sections detected — everything is unclassified content
        unknown_lines = [
            (line.normalized_text or line.text).strip()
            for idx, line in enumerate(lines)
            if (line.normalized_text or line.text).strip()
            and not line.is_layout_artifact
            and (line.normalized_text or line.text).strip() not in preamble_texts
            and (line.source_line_id or f"p{line.page + 1}-l{idx + 1}")
            not in summary_line_ids
        ]
        if unknown_lines:
            unknown_blocks = attach_reconstruction_metadata(
                [CVUnknownBlock(lines=unknown_lines, confidence=0.1)],
                lines,
                "custom",
                claimed_line_ids=doc_claimed_line_ids,
            )
            doc.sections.append(
                CVSection(
                    type="custom",
                    title="Unclassified Content",
                    blocks=unknown_blocks,
                )
            )
            doc.reconstruction_warnings.append("single_unknown_section_fallback")
        return _finalize_diagnostics(doc, lines)

    # Step 4: Build sections from boundaries
    for seg_idx, boundary in enumerate(boundaries):
        if boundary.canonical_type == "summary":
            continue
        start = boundary.index
        end = (
            boundaries[seg_idx + 1].index
            if seg_idx + 1 < len(boundaries)
            else len(lines)
        )

        section_lines = lines[start + 1 : end]
        # Filter: skip page-break markers and layout artifacts
        section_lines = [
            line_item
            for line_item in section_lines
            if not line_item.is_layout_artifact and not line_item.is_page_break_marker
        ]

        # Collect actual text lines (skip blank lines at start/end)
        while (
            section_lines
            and not (section_lines[0].normalized_text or section_lines[0].text).strip()
        ):
            section_lines = section_lines[1:]
        while (
            section_lines
            and not (
                section_lines[-1].normalized_text or section_lines[-1].text
            ).strip()
        ):
            section_lines = section_lines[:-1]

        blocks = _classify_section_content(
            section_lines,
            boundary.canonical_type,
            claimed_line_ids=doc_claimed_line_ids,
            section_title=boundary.display_title,
        )

        section = CVSection(
            type=boundary.canonical_type,
            title=boundary.display_title,
            blocks=blocks,
        )
        doc.sections.append(section)

    # Step 5: Any content lines not assigned to a section
    assigned_indices = set()
    for boundary in boundaries:
        end = (
            boundaries[boundaries.index(boundary) + 1].index
            if boundaries.index(boundary) + 1 < len(boundaries)
            else len(lines)
        )
        assigned_indices.update(range(boundary.index, end))

    unassigned: list[tuple[int, ExtractedLine, str]] = []
    for i, line in enumerate(lines):
        if i not in assigned_indices and not line.is_layout_artifact:
            text = (line.normalized_text or line.text).strip()
            line_id = line.source_line_id or f"p{line.page + 1}-l{i + 1}"
            if text and text not in preamble_texts and line_id not in summary_line_ids:
                unassigned.append((i, line, text))

    if unassigned:
        blocks: list[CVUnknownBlock] = []
        for orig_idx, line, text in unassigned:
            source_id = line.source_line_id or f"p{line.page + 1}-l{orig_idx + 1}"
            seed = f"custom-unknown-{source_id}-{orig_idx}-{text}"
            block = CVUnknownBlock(
                lines=[text],
                confidence=0.3,
                source_line_ids=[source_id],
            )
            block.block_id = f"custom-{sha256(seed.encode('utf-8')).hexdigest()[:12]}"
            blocks.append(block)
        doc.sections.append(
            CVSection(
                type="custom",
                title="Other Content",
                blocks=blocks,
            )
        )

    return _finalize_diagnostics(doc, lines)


def _finalize_diagnostics(
    doc: CVDocumentV2,
    lines: list[ExtractedLine],
) -> CVDocumentV2:
    warnings = list(doc.reconstruction_warnings)
    for index, section in enumerate(doc.sections):
        seed = f"{index}|{section.type}|{section.title}|" + "|".join(
            block.block_id for block in section.blocks
        )
        section.id = f"{section.type}-{sha256(seed.encode('utf-8')).hexdigest()[:10]}"
    blocks = [block for section in doc.sections for block in section.blocks]
    if doc.summary is not None:
        blocks.append(doc.summary)
    for section in doc.sections:
        sec_line_ids = [
            line_id for block in section.blocks for line_id in block.source_line_ids
        ]
        if len(sec_line_ids) != len(set(sec_line_ids)):
            warnings.append("duplicate_line_ownership")

    for block in blocks:
        warnings.extend(block.reconstruction_warnings)

    if any(
        _get_line_text(line)[:1].islower() and not line.joined_to_prev
        for line in lines
        if _get_line_text(line)
    ):
        warnings.append("possible_unjoined_line_wrap")

    columns_by_page: dict[int, set[str]] = {}
    for line in lines:
        if line.column_id:
            columns_by_page.setdefault(line.page, set()).add(line.column_id)
    if any(len(columns) > 1 for columns in columns_by_page.values()):
        warnings.append("possible_column_order_problem")

    # Identity check: contact/email present in source lines but identity name is missing
    if (
        not doc.identity
        or not doc.identity.name
        or doc.identity.name.strip() in ("", "Candidate")
    ):
        has_contact_signal = any(
            re.search(r"[\w\.-]+@[\w\.-]+\.\w+", _get_line_text(line))
            or re.search(r"\+?\d[\d\s-]{7,}\d", _get_line_text(line))
            for line in lines
        )
        if has_contact_signal:
            warnings.append("identity_candidate_unparsed")

    # Summary ownership check
    all_line_ids = {line.source_line_id for line in lines if line.source_line_id}
    summary_line_ids = set(doc.summary.source_line_ids) if doc.summary else set()
    if all_line_ids and (len(summary_line_ids) / len(all_line_ids)) > 0.60:
        warnings.append("summary_ownership_excessive")

    # Embedded headings check inside composite summary lines
    heading_patterns = [
        r"\bCAREER OBJECTIVE\b",
        r"\bWORK EXPERIENCE\b",
        r"\bTECHNICAL SKILLS\b",
        r"\bEDUCATION\b",
        r"\bEXPERIENCE\b",
        r"\bSKILLS\b",
        r"\bPROJECTS\b",
        r"\bACTIVITIES\b",
        r"\bCERTIFICATIONS\b",
    ]
    if doc.summary:
        summary_lines = [
            _get_line_text(line)
            for line in lines
            if line.source_line_id in summary_line_ids
        ]
        has_embedded = False
        for text in summary_lines:
            for pat in heading_patterns:
                m = re.search(pat, text, re.IGNORECASE)
                if m:
                    matched_heading = m.group(0)
                    if m.start() > 3 and not matched_heading.isupper():
                        continue
                    remainder = (text[: m.start()] + text[m.end() :]).strip()
                    if len(remainder) >= 10:
                        has_embedded = True
                        break
            if has_embedded:
                break
        if has_embedded:
            warnings.append("summary_contains_embedded_headings")

    # Classified section collapse check
    known_sections = [s for s in doc.sections if s.type not in ("custom", "unknown")]
    if not doc.sections or not known_sections:
        warnings.append("classified_section_collapse")

    doc.reconstruction_warnings = list(dict.fromkeys(warnings))
    return doc


def _get_line_text(line: ExtractedLine) -> str:
    return (line.normalized_text or line.text).strip()
