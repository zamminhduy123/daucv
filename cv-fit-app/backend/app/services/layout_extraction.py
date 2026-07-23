"""Layout-aware PDF text extraction for CV processing.

Replaces the naive ``page.extract_text()`` approach with a structured pipeline
that captures spatial metadata, normalizes extraction noise, detects reading
order for multi-column layouts, and identifies physical line continuations.

This is Phase 3 of the typed CV reconstruction pipeline.
"""

from __future__ import annotations

import io
import re
import unicodedata
from collections import Counter
from dataclasses import dataclass
from typing import Any

import pdfplumber

# ---------------------------------------------------------------------------
# 1. ExtractedLine data model (Step 3.1)
# ---------------------------------------------------------------------------

_BULLET_CHARS_RAW = "•●‣▪◦▷◉▫‐‑-"
_BULLET_RE = re.compile(
    r"^\s*([" + re.escape(_BULLET_CHARS_RAW) + r"])[\s​]*(\S.*)$",
)


@dataclass
class ExtractedLine:
    """One physical line from a PDF page with layout metadata.

    Coordinates are in pdfplumber's default user-space units (points).
    When the extraction library cannot provide reliable font information,
    ``font_size`` and ``font_weight`` remain ``None``.
    """

    text: str
    """The raw (pre-normalization) text content."""

    page: int
    """Zero-based page index."""

    x: float
    """Left coordinate in points."""

    y: float
    """Top coordinate in points."""

    width: float
    """Text width in points."""

    height: float
    """Text height (line height) in points."""

    font_size: float | None = None
    """Font size in points, if available."""

    font_weight: float | None = None
    """Font weight (100-900), if available. 400 = normal, 700 = bold."""

    bullet_marker: str | None = None
    """The detected bullet character (•, -, etc.) or ``None``."""

    # -----------------------------------------------------------------------
    # Post-processing fields (set by later pipeline stages)
    # -----------------------------------------------------------------------
    normalized_text: str = ""
    """Text after noise normalisation (Step 3.2)."""

    column_id: str | None = None
    """Assigned column identifier after reading-order detection (Step 3.3)."""

    joined_to_prev: bool = False
    """Whether this line should be joined to the previous physical line."""

    is_page_break_marker: bool = False
    """True if the line is a page-break indicator like '--- PAGE 2 ---'."""

    is_layout_artifact: bool = False
    """True for a repeated margin header/footer or standalone page number."""

    page_height: float | None = None
    """Page height in points, used to validate cross-page continuations."""

    source_line_id: str = ""
    """Stable page/line identifier assigned after reading-order sorting."""

    def __repr__(self) -> str:
        return (
            f"ExtractedLine(page={self.page}, y={self.y:.0f}, "
            f"x={self.x:.0f}, text={self.text[:60]!r}...)"
        )


# ---------------------------------------------------------------------------
# 2. Normalization helpers (Step 3.2)
# ---------------------------------------------------------------------------

# Soft hyphen (U+00AD) often inserted by PDF renderers at word-break points
_SOFT_HYPHEN = "­"

# Zero-width space artefact of some PDF extractors
_ZERO_WIDTH_SPACE = "\u200b"

# Non-breaking space variants that pdfplumber may emit
_NBSP = " "

# Patterns that look like page markers
_PAGE_MARKER_RE = re.compile(
    r"^\s*(?:(?:[-=—–]*\s*(?:PAGE|TRANG)\s*\d+"
    r"(?:\s*(?:OF|/)\s*\d+)?\s*[-=—–]*)|"
    r"(?:[-—–]\s*\d+\s*[-—–]))\s*$",
    re.IGNORECASE,
)


def _normalize_bullet(text: str) -> tuple[str, str | None]:
    """Return (text_with_normalized_bullet, detected_bullet_marker).

    Normalises unicode bullet variants to the canonical U+2022 BULLET character.
    Detects both •/● bullets AND dash/hyphen bullets (Step 3.2: no_bullet fix).
    """
    m = _BULLET_RE.match(text)
    if m:
        marker = m.group(1)
        content = m.group(2)
        return "• " + content, marker

    return text, None


def _collapse_whitespace(text: str) -> str:
    """Collapse runs of whitespace to a single space, strip leading/trailing."""
    return re.sub(r"\s+", " ", text).strip()


def _remove_soft_hyphens(text: str) -> str:
    """Remove soft hyphens that break words incorrectly."""
    return text.replace(_SOFT_HYPHEN, "")


def _remove_zero_width_spaces(text: str) -> str:
    """Remove zero-width spaces (PDF extraction artefacts)."""
    return text.replace(_ZERO_WIDTH_SPACE, "")


def _replace_nbsp(text: str) -> str:
    """Replace non-breaking spaces with regular spaces."""
    return text.replace(_NBSP, " ")


def _detect_page_marker(text: str) -> bool:
    """Return True if the line looks like a page-break indicator."""
    return bool(_PAGE_MARKER_RE.search(text))


def normalize_line(line: ExtractedLine) -> ExtractedLine:
    """Apply all normalisation transformations to a single line in-place.

    Handles:
    - Unicode bullet variants
    - Dash/hyphen bullets (no_bullet fix)
    - Repeated whitespace
    - Soft hyphens
    - Zero-width spaces
    - Non-breaking spaces
    - Page markers
    """
    text = line.text

    # Page markers are identified on raw text
    line.is_page_break_marker = _detect_page_marker(text)

    # Apply transformations
    text = _remove_soft_hyphens(text)
    text = _remove_zero_width_spaces(text)
    text = _replace_nbsp(text)
    text = unicodedata.normalize("NFKC", text)

    # Normalize bullets (also detects dash bullets)
    text, marker = _normalize_bullet(text)
    if marker is not None:
        line.bullet_marker = marker

    # Collapse whitespace
    text = _collapse_whitespace(text)

    line.normalized_text = text
    return line


# ---------------------------------------------------------------------------
# 3. Column detection and reading order (Step 3.3)
# ---------------------------------------------------------------------------

_COLUMN_GAP_RATIO = 0.10  # Minimum gap between columns as fraction of page width
_COLUMN_CLUSTER_TOLERANCE = 15.0  # px tolerance for x-coordinate clustering


class Column:
    """A detected column spanning one or more pages."""

    __slots__ = ("column_id", "left", "pages", "right")

    def __init__(self, column_id: str, left: float, right: float, pages: set[int]):
        self.column_id = column_id
        self.left = left
        self.right = right
        self.pages = pages

    def contains(self, x: float, page: int) -> bool:
        return (
            self.left - _COLUMN_CLUSTER_TOLERANCE
            <= x
            <= self.right + _COLUMN_CLUSTER_TOLERANCE
            and page in self.pages
        )

    def __repr__(self) -> str:
        return f"Column({self.column_id}: [{self.left:.0f}, {self.right:.0f}])"


def _detect_columns(lines: list[ExtractedLine], page_width: float) -> list[Column]:
    """Detect horizontal lanes independently on each page.

    Line bounding boxes, rather than start positions alone, prevent ordinary
    indentation and centred headings from being mistaken for new columns.
    Broad lines are treated as spanning content and do not collapse a genuine
    two-column gutter.
    """
    columns: list[Column] = []
    pages = sorted({line.page for line in lines})
    for page in pages:
        page_lines = [line for line in lines if line.page == page]
        candidates = [
            (line.x, line.x + max(line.width, 1.0))
            for line in page_lines
            if line.width < page_width * 0.60
        ]
        if not candidates:
            columns.append(Column("main", 0, page_width, {page}))
            continue

        gap = max(_COLUMN_CLUSTER_TOLERANCE * 2, page_width * _COLUMN_GAP_RATIO)
        lanes = _cluster_coordinate_ranges(candidates, gap)
        if len(lanes) < 2:
            columns.append(Column("main", 0, page_width, {page}))
            continue

        for index, (left, right) in enumerate(lanes):
            columns.append(Column(f"col-{index}", left, right, {page}))

    return columns


def _cluster_coordinates(
    xs: list[float], tolerance: float
) -> list[tuple[float, float]]:
    """Cluster x-coordinates into ranges. Returns [(min, max), ...]."""
    if not xs:
        return []
    xs = sorted(xs)
    clusters: list[tuple[float, float]] = []
    cluster_start = xs[0]
    cluster_end = xs[0]
    for x in xs[1:]:
        if x - cluster_end <= tolerance:
            cluster_end = x
        else:
            clusters.append((cluster_start, cluster_end))
            cluster_start = x
            cluster_end = x
    clusters.append((cluster_start, cluster_end))
    return clusters


def _cluster_coordinate_ranges(
    ranges: list[tuple[float, float]],
    gap: float,
) -> list[tuple[float, float]]:
    """Merge overlapping or nearby coordinate ranges."""
    if not ranges:
        return []
    sorted_ranges = sorted(ranges, key=lambda r: r[0])
    merged: list[tuple[float, float]] = [sorted_ranges[0]]
    for left, right in sorted_ranges[1:]:
        prev_left, prev_right = merged[-1]
        if left <= prev_right + gap:
            merged[-1] = (min(prev_left, left), max(prev_right, right))
        else:
            merged.append((left, right))
    return merged


def assign_columns(
    lines: list[ExtractedLine], page_width: float
) -> list[ExtractedLine]:
    """Detect columns and assign a column_id to each line.

    For single-column documents, all lines get ``column_id="main"``.
    For two-column layouts (common in CVs), left content gets ``col-0``
    and right content gets ``col-1``.

    Returns the same list with ``column_id`` set on each line.
    """
    if not lines:
        return lines

    columns = _detect_columns(lines, page_width)

    for line in lines:
        page_columns = [column for column in columns if line.page in column.pages]
        if len(page_columns) <= 1:
            line.column_id = "main"
            continue

        line_left = line.x
        line_right = line.x + max(line.width, 1.0)
        overlaps = [
            max(0.0, min(line_right, column.right) - max(line_left, column.left))
            for column in page_columns
        ]
        matching = [index for index, overlap in enumerate(overlaps) if overlap > 0]
        if len(matching) > 1 or line.width >= page_width * 0.60:
            line.column_id = "span"
        elif matching:
            line.column_id = page_columns[matching[0]].column_id
        else:
            line.column_id = min(
                page_columns,
                key=lambda column: abs(line.x - column.left),
            ).column_id

    return lines


def sort_by_reading_order(lines: list[ExtractedLine]) -> list[ExtractedLine]:
    """Sort lines into reading order respecting column structure.

    For single-column: sort by (page, y) — top to bottom.
    For multi-column: sort by page, then within each page, process columns
    left-to-right, each column top-to-bottom.
    """
    if not lines:
        return lines

    # Check if this is a multi-column layout
    column_ids = {line.column_id for line in lines}
    is_multi_column = len(column_ids) > 1

    if is_multi_column:
        return _sort_multi_column(lines)
    return _sort_single_column(lines)


def _sort_single_column(lines: list[ExtractedLine]) -> list[ExtractedLine]:
    """Sort single-column lines by page then y-coordinate (top to bottom)."""
    return sorted(lines, key=lambda line: (line.page, line.y))


def _sort_multi_column(lines: list[ExtractedLine]) -> list[ExtractedLine]:
    """Sort columns left-to-right while preserving spanning section bands."""
    # Determine column order by left coordinate
    col_positions: dict[str, float] = {}
    for line in lines:
        cid = line.column_id or "main"
        if cid not in col_positions:
            col_positions[cid] = line.x
        else:
            col_positions[cid] = min(col_positions[cid], line.x)

    sorted_cols = sorted(col_positions.keys(), key=lambda c: col_positions[c])

    # Group by page and column
    groups: dict[tuple[int, str], list[ExtractedLine]] = {}
    for line in lines:
        cid = line.column_id or "main"
        groups.setdefault((line.page, cid), []).append(line)

    result: list[ExtractedLine] = []
    for page in sorted({page for page, _column in groups}):
        spanning = sorted(groups.get((page, "span"), []), key=lambda line: line.y)
        page_columns = [column for column in sorted_cols if column != "span"]
        lower_bound = float("-inf")
        for spanning_line in spanning:
            for column in page_columns:
                band = [
                    line
                    for line in groups.get((page, column), [])
                    if lower_bound < line.y < spanning_line.y
                ]
                result.extend(sorted(band, key=lambda line: line.y))
            result.append(spanning_line)
            lower_bound = spanning_line.y

        for column in page_columns:
            band = [
                line for line in groups.get((page, column), []) if line.y > lower_bound
            ]
            result.extend(sorted(band, key=lambda line: line.y))

    return result


# ---------------------------------------------------------------------------
# 4. Physical line continuation detection (Step 3.4)
# ---------------------------------------------------------------------------

# Known section headings (subset of cv_quality_checks for independence)
_KNOWN_HEADINGS = {
    "professional summary",
    "summary",
    "technical skills",
    "skills",
    "work experience",
    "experience",
    "projects",
    "publications",
    "education",
    "certifications",
    "languages",
    "awards",
    "volunteering",
    "activities",
    "professional experience",
    "employment history",
    "work history",
    "key skills",
    "core competencies",
    "interests",
    "about me",
    "contact",
    "tom tat",
    "gioi thieu",
    "muc tieu",
    "kinh nghiem",
    "kinh nghiem lam viec",
    "hoc van",
    "ky nang",
    "du an",
    "chung chi",
    "ngon ngu",
    "giai thuong",
    "hoat dong",
    "lien he",
    "cong nghe",
    "so luoc",
    "du an ca nhan",
    "cac du an",
}

# Date patterns
_DATE_PATTERNS = [
    r"\b(19|20)\d{2}\s*[-–—](?:\s*(19|20)\d{2}|present|hiện tại|nay)?\b",
    r"\b(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\s+(19|20)\d{2}",
    r"\b(january|february|march|april|may|june|july|august|september|october|november|december)\s+(19|20)\d{2}",
]
_DATE_RE = re.compile("|".join(_DATE_PATTERNS), re.IGNORECASE)

# Company/role boundary patterns
_ROLE_BOUNDARY_RE = re.compile(
    r"\b(engineer|developer|designer|manager|lead|analyst|consultant|"
    r"kỹ\s*sư|lập\s*trình\s*viên|chuyên\s*viên|quản\s*lý|"
    r"intern|fresher|junior|senior|specialist|director|vp|cto|cfo|"
    r"professor|lecturer|researcher)\b",
    re.IGNORECASE,
)

_COMPANY_BOUNDARY_RE = re.compile(
    r"\b(company|công\s*ty|tập\s*đoàn|corporation|corp|ltd|co\.(?:\s*inc)?|"
    r"jsc|tnhh|university|đại\s*học|trường|institute|viện)\b",
    re.IGNORECASE,
)


def _is_known_section_heading(text: str) -> bool:
    """Check if the text matches a known section heading."""
    cleaned = text.strip().rstrip(":").strip()
    if not cleaned or len(cleaned.split()) > 8:
        return False
    if re.search(r"[.!?;]$", cleaned):
        return False
    return _normalize_heading(cleaned) in _KNOWN_HEADINGS


def _normalize_heading(text: str) -> str:
    """Normalize heading text for comparison (lowercase, strip accents)."""
    decomposed = unicodedata.normalize("NFKD", text.lower().strip())
    return "".join(c for c in decomposed if not unicodedata.combining(c))


def _looks_like_date(text: str) -> bool:
    """Return True if the text looks like a date range."""
    return bool(_DATE_RE.search(text))


def _looks_like_role_boundary(text: str) -> bool:
    """Return True if the text looks like a job title or role boundary."""
    stripped = text.strip()
    if not stripped or len(stripped.split()) > 6:
        return False
    # Must NOT be a substring match (managerial != manager)
    return bool(_ROLE_BOUNDARY_RE.search(stripped))


def _looks_like_company_boundary(text: str) -> bool:
    """Return True if the text looks like a company name boundary."""
    stripped = text.strip()
    if not stripped or len(stripped.split()) > 6:
        return False
    return bool(_COMPANY_BOUNDARY_RE.search(stripped))


def _should_append_to_bullet(prev_text: str, current_text: str) -> bool:
    """Determine if ``current_text`` should be appended to ``prev_text`` as a continuation.

    Heuristics (Step 3.4):
    - Previous line must start with a bullet marker.
    - Previous line must NOT end with terminal punctuation.
    - Current line must NOT start with a new bullet.
    - Current line must NOT be a job metadata line.
    """
    if not prev_text.startswith("• "):
        return False
    if re.search(r"[.!?;:]$", prev_text.strip()):
        return False
    current = current_text.strip()
    if bool(re.match(r"^[•●‣▪◦▫\-]", current)):
        return False
    return not _is_job_metadata_line(current)


def _is_job_metadata_line(text: str) -> bool:
    """Return True if the line looks like job metadata (role, company, date, location)."""
    lowered = text.lower().strip()
    if not lowered:
        return False

    # Contains a date pattern
    if _looks_like_date(text):
        return True

    # Starts with lowercase (wrapped continuation, not a new boundary)
    stripped = text.strip()
    if stripped and stripped[0].islower():
        return False

    # Contains role or company keywords
    if _looks_like_role_boundary(text) or _looks_like_company_boundary(text):
        words = text.split()
        if len(words) <= 6 and text[0].isupper():
            return True

    return False


def should_join_lines(
    prev_line: ExtractedLine,
    curr_line: ExtractedLine,
    prev_is_bullet: bool = False,
) -> bool:
    """Determine whether ``curr_line`` should be physically joined to ``prev_line``.

    Multi-signal approach (Step 3.4):
    1. Must be on the same or consecutive pages.
    2. Similar vertical proximity (small y-gap).
    3. Similar indentation (x-coordinate proximity).
    4. Similar font size/weight (when available).
    5. Previous line lacks terminal punctuation.
    6. Current line is NOT a known section heading.
    7. Current line is NOT a date/company/role boundary.
    8. If previous was a bullet, uses ``_should_append_to_bullet``.

    Capitalization alone must NOT decide continuation.
    """
    page_delta = curr_line.page - prev_line.page
    if page_delta not in {0, 1}:
        return False

    # Must be in the same column (for multi-column)
    if (
        prev_line.column_id
        and curr_line.column_id
        and prev_line.column_id != curr_line.column_id
    ):
        return False

    if page_delta == 0:
        y_gap = curr_line.y - (prev_line.y + prev_line.height)
        if y_gap < -3 or y_gap > 30:
            return False
    else:
        if prev_line.page_height is None or curr_line.page_height is None:
            return False
        prev_near_bottom = prev_line.y + prev_line.height >= prev_line.page_height - 100
        curr_near_top = curr_line.y <= 100
        if not (prev_near_bottom and curr_near_top):
            return False

    # Similar indentation: x-coordinate difference should be small
    x_diff = abs(curr_line.x - prev_line.x)
    if x_diff > 20:  # 20 points tolerance
        return False

    # Current line is a page-break marker — never join
    if curr_line.is_page_break_marker or curr_line.is_layout_artifact:
        return False

    # Current line is a section heading — never join to previous
    if _is_known_section_heading(curr_line.normalized_text):
        return False

    # Current line is a date/role/company boundary — never join
    if _looks_like_date(curr_line.normalized_text):
        return False
    if _looks_like_role_boundary(curr_line.normalized_text):
        return False
    if _looks_like_company_boundary(curr_line.normalized_text):
        return False

    if _is_known_section_heading(prev_line.normalized_text):
        return False

    # Previous line ends with terminal punctuation — start new line
    prev_norm = prev_line.normalized_text.strip()
    if re.search(r"[.!?;:]$", prev_norm):
        return False

    # Current line starts with uppercase — likely new content
    # (but NOT alone — use with other signals)
    curr_norm = curr_line.normalized_text.strip()
    if not curr_norm:
        return False

    # Font similarity check (when available)
    if (
        prev_line.font_size is not None
        and curr_line.font_size is not None
        and abs(prev_line.font_size - curr_line.font_size) > 2
    ):
        # Different font sizes likely mean different semantic blocks
        return False

    if (
        prev_line.font_weight is not None
        and curr_line.font_weight is not None
        and abs(prev_line.font_weight - curr_line.font_weight) > 100
    ):
        # Different weights (bold vs normal) likely mean different blocks
        return False

    if prev_line.bullet_marker or prev_is_bullet:
        return _should_append_to_bullet(
            prev_line.normalized_text,
            curr_line.normalized_text,
        )

    # Geometry, typography and boundary checks all agree. Lowercase text,
    # comma/hyphen endings and cross-page edge alignment strengthen the
    # grammatical-continuation signal; capitalization is never used alone.
    starts_lowercase = curr_norm[0].islower()
    open_ending = bool(re.search(r"[,/–—-]$", prev_norm))
    return starts_lowercase or open_ending or page_delta == 1


# ---------------------------------------------------------------------------
# 5. Main extraction pipeline (Step 3.1-3.4 combined)
# ---------------------------------------------------------------------------


def _group_words_into_lines(
    words: list[dict[str, Any]],
    tolerance: float = 2.0,
) -> list[list[dict[str, Any]]]:
    """Group extracted words whose top coordinates describe one visual line."""
    groups: list[list[dict[str, Any]]] = []
    group_tops: list[float] = []
    for word in sorted(
        words, key=lambda item: (float(item.get("top", 0)), float(item.get("x0", 0)))
    ):
        top = float(word.get("top", 0))
        for index, group_top in enumerate(group_tops):
            if abs(top - group_top) <= tolerance:
                groups[index].append(word)
                group_tops[index] = sum(
                    float(w.get("top", 0)) for w in groups[index]
                ) / float(len(groups[index]))
                break
        else:
            groups.append([word])
            group_tops.append(top)
    return groups


def _mark_layout_artifacts(lines: list[ExtractedLine]) -> None:
    """Flag repeated margin text and standalone page-number noise."""
    margin_pages: dict[str, set[int]] = {}
    for line in lines:
        normalized = line.normalized_text.casefold().strip()
        if not normalized or line.page_height is None:
            continue
        in_margin = line.y <= 72 or line.y + line.height >= line.page_height - 72
        if in_margin:
            margin_pages.setdefault(normalized, set()).add(line.page)

    repeated = {text for text, pages in margin_pages.items() if len(pages) >= 2}
    for line in lines:
        normalized = line.normalized_text.casefold().strip()
        in_margin = bool(
            line.page_height is not None
            and (line.y <= 72 or line.y + line.height >= line.page_height - 72),
        )
        standalone_page_number = bool(
            re.fullmatch(r"[-–—]?\s*\d+\s*[-–—]?", normalized)
        )
        line.is_layout_artifact = (
            line.is_page_break_marker
            or normalized in repeated
            or (in_margin and standalone_page_number)
        )


def _extract_words_to_lines(
    pdf_bytes: bytes,
) -> tuple[list[ExtractedLine], dict[int, float]]:
    """Extract words from a PDF using pdfplumber's ``extract_words()``.

    Returns the lines plus the width of every source page.
    """
    lines: list[ExtractedLine] = []
    page_widths: dict[int, float] = {}

    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        for page_idx, page in enumerate(pdf.pages):
            page_widths[page_idx] = float(page.width)
            words = (
                page.extract_words(
                    x_tolerance=3.0,
                    y_tolerance=2.0,
                    keep_blank_chars=False,
                    extra_attrs=["fontname", "size"],
                )
                or []
            )

            for group in _group_words_into_lines(words):
                group_words = sorted(group, key=lambda word: word.get("x0", 0))
                text_parts = [str(word.get("text", "")) for word in group_words]
                full_text = " ".join(text_parts)

                if not full_text.strip():
                    continue

                font_sizes = [
                    word.get("size")
                    for word in group_words
                    if word.get("size") is not None
                ]
                font_names = [
                    str(word.get("fontname"))
                    for word in group_words
                    if word.get("fontname")
                ]
                font_size = (
                    Counter(font_sizes).most_common(1)[0][0] if font_sizes else None
                )
                font_name = (
                    Counter(font_names).most_common(1)[0][0] if font_names else None
                )

                # Estimate font weight from font name
                font_weight = None
                if font_name:
                    fn_lower = font_name.lower()
                    if (
                        "bold" in fn_lower
                        or "extrabold" in fn_lower
                        or "semibold" in fn_lower
                    ):
                        font_weight = 700
                    elif "light" in fn_lower:
                        font_weight = 300
                    else:
                        font_weight = 400

                x0 = min(float(word.get("x0", 0)) for word in group_words)
                x1 = max(float(word.get("x1", x0)) for word in group_words)
                top = min(float(word.get("top", 0)) for word in group_words)
                bottom = max(
                    float(word.get("bottom", top + 12)) for word in group_words
                )

                line = ExtractedLine(
                    text=full_text,
                    page=page_idx,
                    x=x0,
                    y=top,
                    width=x1 - x0,
                    height=bottom - top,
                    font_size=font_size,
                    font_weight=font_weight,
                    page_height=float(page.height),
                )
                lines.append(line)

    return lines, page_widths


def layout_extract_pdf(pdf_bytes: bytes) -> list[ExtractedLine]:
    """Full layout-aware PDF extraction pipeline.

    This is the Phase 3 replacement for ``extract_text_from_pdf()``.

    Pipeline:
    1. Extract words with spatial metadata (Step 3.1).
    2. Normalize each line (Step 3.2).
    3. Detect columns and assign column IDs (Step 3.3).
    4. Sort lines into reading order (Step 3.3).
    5. Detect physical line continuations (Step 3.4).

    Returns a list of ``ExtractedLine`` with ``normalized_text`` populated.
    """
    # Step 1: Extract words → lines
    lines, page_widths = _extract_words_to_lines(pdf_bytes)

    if not lines:
        return lines

    # Step 2: Normalize each line
    for line in lines:
        normalize_line(line)

    _mark_layout_artifacts(lines)
    lines = [line for line in lines if not line.is_layout_artifact]

    # Step 3: Column detection and reading order
    for page, page_width in page_widths.items():
        page_lines = [line for line in lines if line.page == page]
        assign_columns(page_lines, page_width)
    lines = sort_by_reading_order(lines)

    page_line_numbers: dict[int, int] = {}
    for line in lines:
        page_line_numbers[line.page] = page_line_numbers.get(line.page, 0) + 1
        line.source_line_id = f"p{line.page + 1}-l{page_line_numbers[line.page]}"

    # Step 3.3: Record page transitions (for cross-page continuation)
    # This is handled implicitly by the page field in each line.

    # Step 3.4: Detect physical line continuations
    for i in range(1, len(lines)):
        prev = lines[i - 1]
        curr = lines[i]

        # Skip page-break markers
        if curr.is_page_break_marker:
            continue

        prev_is_bullet = bool(prev.bullet_marker)
        if should_join_lines(prev, curr, prev_is_bullet):
            curr.joined_to_prev = True

    return lines


def extract_text_from_layout(lines: list[ExtractedLine]) -> str:
    """Reconstruct a plain text document from ordered, normalised ``ExtractedLine`` objects.

    Joined lines are concatenated with a space; non-joined lines get a newline.
    Page-break markers are replaced with ``--- PAGE N ---``.
    """
    if not lines:
        return ""

    output_lines: list[str] = []
    for line in lines:
        if line.is_layout_artifact or line.is_page_break_marker:
            continue
        norm = line.normalized_text or line.text
        if line.joined_to_prev and output_lines:
            if output_lines[-1].endswith("-"):
                output_lines[-1] = output_lines[-1][:-1] + norm.lstrip()
            else:
                output_lines[-1] += " " + norm.lstrip()
        else:
            output_lines.append(norm)

    return "\n".join(output_lines)


def extract_text_from_pdf(file_bytes: bytes) -> str:
    """Legacy plain-text extraction (kept for backward compatibility).

    Uses the new layout-aware pipeline internally, then returns
    a plain text string for compatibility with existing callers.
    """
    lines = layout_extract_pdf(file_bytes)
    return extract_text_from_layout(lines)
