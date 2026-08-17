"""Section-specific block reconstruction (Phase 5).

Takes ``list[ExtractedLine]`` for a *single* already-detected section and
produces typed ``CVBlock`` instances using a different parser strategy per
canonical section type.

This module replaces the basic ``_classify_*_section()`` helpers that lived
inside ``section_detector.py``.  Each parser is independent and deterministic
(No LLM).  The parsers use:

1. Canonical vocabulary and pattern matching.
2. Structural signals from ``ExtractedLine`` (font size/weight, bullets,
   indentation, geometry).
3. Context: preceding / following lines within the same section.

The ``reconstruct_blocks()`` entry point dispatches to the correct parser
by section type.
"""

from __future__ import annotations

import logging
import re
from collections.abc import Sequence
from hashlib import sha256

from app.models.cv_document_v2 import (
    CVBlockType,
    CVBulletBlock,
    CVEducationBlock,
    CVEntryBlock,
    CVParagraphBlock,
    CVPublicationBlock,
    CVSkillGroupBlock,
    CVUnknownBlock,
)
from app.services.layout_extraction import ExtractedLine

_logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Regex patterns shared across section parsers
# ---------------------------------------------------------------------------

# Date pattern covering years, month/year ranges, and present-day ranges.
_DATE_RANGE_RE = re.compile(
    r"\b(?:"
    r"(?:tháng\s+)?(?:\d{1,2}[/.-])?(?:19|20)\d{2}"
    r"|"
    r"(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|"
    r"Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|"
    r"Nov(?:ember)?|Dec(?:ember)?)\s*,?\s*(?:19|20)\d{2}"
    r")"
    r"(?:\s*[-–—]\s*(?:"
    r"(?:tháng\s+)?(?:\d{1,2}[/.-])?(?:19|20)\d{2}"
    r"|"
    r"(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|"
    r"Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|"
    r"Nov(?:ember)?|Dec(?:ember)?)\s*,?\s*(?:19|20)\d{2}"
    r"|present|hiện tại|nay"
    r"))?\b",
    re.IGNORECASE,
)

# Organization suffixes (English + Vietnamese)
_ORG_SUFFIXES_RE = re.compile(
    r"\b(company|corporation|inc\.?|ltd\.?|llc|grp|group|pty|gmbh|sa|jsc|tnhh|coc|co\.|"
    r"corporation|university|college|institute|center|lab|lab\.?|fund|association|"
    r"tập\s?đoàn|vnv|vng|fpt|tiki|shope|momo|viettel|vina|vinaphone|mobifone"
    r")\b",
    re.IGNORECASE,
)

# Shared metadata pattern: "Role at Company | Location | Date"
_SHARED_META_RE = re.compile(
    r"^(.+?)\s+at\s+(.+?)(?:\s*\|\s*(.+?))?(?:\s*\|\s*(.+?))?\s*$",
    re.IGNORECASE,
)

# Pipe-separated metadata: "Role | Company | Date"
_PIPE_META_RE = re.compile(
    r"^(.+?)\s*\|\s*(.+?)(?:\s*\|\s*(.+?))?\s*$",
)

# Job-title keywords (for detecting role titles)
_JOB_TITLES = {
    "engineer",
    "developer",
    "designer",
    "analyst",
    "manager",
    "director",
    "lead",
    "architect",
    "consultant",
    "researcher",
    "specialist",
    "coordinator",
    "administrator",
    "associate",
    "intern",
    "internship",
    "assistant",
    "professor",
    "lecturer",
    "principal",
    "senior",
    "junior",
    "staff",
    "chief",
    "head",
    "vice president",
    "vp",
    "cto",
    "cfo",
    "cio",
    "cmo",
    "kỹ",
    "sư",
    "lập",
    "trình",
    "viên",
    "chuyên",
    "gia",
    "nhân",
    "trưởng",
    "phó",
    "giáo",
    "giảng",
}

# Skill label pattern: "Label: item1, item2, ..."
# Relaxed to support technical skills with mixed capitalization, numbers, symbols
# Also matches simple labels like "Skills:" followed by comma-separated items on same line
_SKILL_GROUP_RE = re.compile(
    r"^[A-ZÀ-Ỹ][a-zA-Z0-9À-ỹ\s./&+#()（）-]{0,60}:\s+"
    r"([a-zA-Z0-9À-ỹ\s./&+#()（）-]+(?:\s*,\s*[a-zA-Z0-9À-ỹ\s./&+#()（）-]+)*)$",
)
# Also match: "Label: item1 item2 item3" (space-separated, no commas)
_SKILL_GROUP_SPACE_RE = re.compile(
    r"^[A-ZÀ-Ỹ][a-zA-Z0-9À-ỹ\s./&+#()（）-]{0,40}:\s+"
    r"([a-zA-Z0-9À-ỹ\s./&+#()（）-]+(?:\s+[a-zA-Z0-9À-ỹ\s./&+#()（）-]+)*)$",
)

# Bullet patterns (normalized — after layout_extraction normalizes)
_BULLET_START = ("• ", "● ", "▪ ", "▫ ", "► ", "‣ ", "– ", "— ")
_DASH_BULLET = ("- ", "-- ", "-")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _get_text(line: ExtractedLine) -> str:
    """Return the normalized text of a line, falling back to raw text."""
    return (line.normalized_text or line.text).strip()


def _text_has_leading_space(line: ExtractedLine) -> bool:
    """Check if the raw text has leading whitespace (indentation signal)."""
    return bool(line.text and line.text != line.text.lstrip() and line.text.strip())


def _is_bullet(line: ExtractedLine, text: str) -> bool:
    """Return True if the line starts with a bullet marker."""
    return text.startswith(_BULLET_START) or text.startswith(_DASH_BULLET)


def _strip_bullet(text: str) -> str:
    """Remove leading bullet marker from text."""
    for prefix in _BULLET_START + _DASH_BULLET:
        if text.startswith(prefix):
            return text[len(prefix) :].strip()
    return text


def _is_date_line(text: str) -> bool:
    """Return True if text is primarily a date range."""
    return bool(_DATE_RANGE_RE.search(text))


def _is_primary_date_line(text: str) -> bool:
    """Return True if text IS a date range (not just contains one).

    Used in strict contexts like education parsing where a line like
    "FPT University | 2019 – 2021" should NOT be treated as a date line.
    """
    stripped = text.strip()
    # Must be the date range itself or a short line that is a date range
    date_match = _DATE_RANGE_RE.search(stripped)
    if not date_match:
        return False
    # The date range should be the dominant content (≤ 10 chars of non-date)
    non_date = stripped[: date_match.start()] + stripped[date_match.end() :]
    return len(non_date.strip().replace("|", "").strip()) <= 5


def _is_job_title(text: str) -> bool:
    """Return True if text looks like a job/role title."""
    words = text.lower().split()
    return any(w in _JOB_TITLES for w in words)


def _looks_like_org(text: str, next_text: str = "") -> bool:
    """Return True if text looks like an organization name.

    Uses multiple signals:
    - Contains org suffix/keyword (Company, JSC, Đại học, etc.)
    - Next line is a date-range or pipe-separated metadata pattern
      (strong signal for two-line format: "Org\\nRole | Date")
    - Short, capitalized, not a job title
    """
    lower = text.lower()

    # Contains org suffix or keyword
    if _ORG_SUFFIXES_RE.search(lower):
        return True

    # Known Vietnamese org patterns
    if any(
        kw in lower for kw in ["corporation", "company", "joint stock", "tnhh", "jsc"]
    ):
        return True

    # Heuristic: short, capitalized, not a job title, and next line has date
    # This catches brand names like "TechCorp", "VNG", "MoMo", "FPT", etc.
    if _is_short(text) and text[0].isupper() and not _is_job_title(text):
        # Check if next line looks like role+date metadata
        if next_text and (_is_date_line(next_text) or "|" in next_text):
            return True
        # Check if next line is a known role/title
        if next_text and _is_job_title(next_text):
            return True

    return False


def _is_short(text: str, max_words: int = 6) -> bool:
    """Return True if text is a short line (≤ max_words words)."""
    return bool(text.strip()) and len(text.split()) <= max_words


def _is_title_case_or_caps(text: str) -> bool:
    """Return True if text is all-caps or mostly title-case."""
    stripped = text.strip()
    words = [w for w in stripped.split() if w]
    if not words:
        return False
    all_caps = all(w.isupper() for w in words if w.isalpha())
    if all_caps:
        return True
    title_count = sum(1 for w in words if w and w[0].isupper() and len(w) > 2)
    return title_count >= len(words) * 0.6


def _extract_date(text: str) -> str | None:
    """Extract a date range string from text, or None."""
    m = _DATE_RANGE_RE.search(text)
    return m.group(0) if m else None


def _looks_like_entry_headline(
    line: ExtractedLine,
    text: str,
    lines: Sequence[ExtractedLine],
    index: int,
) -> bool:
    """Determine if a line looks like an entry headline (job/project title).

    Uses combined signals:
    - Not a bullet
    - Not just a date
    - Short (≤ 6 words)
    - Starts uppercase
    - Has typography emphasis OR is title-case/all-caps
    """
    stripped = text.strip()
    if not stripped:
        return False

    # Must not be a bullet
    if _is_bullet(line, stripped):
        return False

    # Pipe-separated headlines (e.g. "Title | Role 2024") are entry boundaries
    if "|" in stripped and stripped[0].isupper():
        return True

    # Must not be a date or role+date metadata line
    if _is_date_line(stripped) or (
        _extract_date(stripped)
        and any(
            k in stripped.lower()
            for k in (
                "engineer",
                "developer",
                "freelance",
                "team of",
                "intern",
                "assistant",
            )
        )
    ):
        return False

    # Must be reasonably short
    if len(stripped.split()) > 8:
        return False

    # Must start uppercase
    if not stripped[0].isupper():
        return False

    # Prefer lines that are bold or larger font
    if line.font_weight is not None and line.font_weight >= 600:
        return True
    if line.font_size is not None and line.font_size >= 12.0:
        return True

    # Title-case or all-caps short phrase
    if _is_title_case_or_caps(stripped):
        return True

    # If it's the first content line after a section heading, likely a headline
    if index > 0:
        prev_text = _get_text(lines[index - 1])
        if not prev_text:  # blank line after section heading
            return True

    return False


def _looks_like_experience_boundary(line: ExtractedLine, text: str) -> bool:
    """Return whether text starts a new experience record."""
    if _SHARED_META_RE.match(text):
        return True
    if "|" in text:
        first = text.split("|", 1)[0].strip()
        return _is_job_title(first) and _extract_date(text) is not None
    return _is_job_title(text) and _looks_like_entry_headline(line, text, [line], 0)


def _append_subtitle(entry: CVEntryBlock, text: str) -> None:
    """Append metadata to an entry subtitle without losing earlier context."""
    entry.subtitle = f"{entry.subtitle} | {text}" if entry.subtitle else text


# ---------------------------------------------------------------------------
# 5.1  Experience parser
# ---------------------------------------------------------------------------


def _reconstruct_experience(lines: list[ExtractedLine]) -> list[CVBlockType]:
    """Parse experience section into entry blocks.

    Handles:
    - Organization, role, location, date on separate or shared lines.
    - "Role at Company | Location | Date" shared format.
    - Multiple positions at one organization (org carries forward).
    - Bullet points (•, -, etc.) and wrapped bullet continuations.
    - Date-only lines that are metadata for the preceding entry.

    Does NOT rely on "line after a bullet" to find the next employer.
    Uses combined date, typography, indentation and semantic signals.
    """
    blocks: list[CVBlockType] = []
    i = 0
    last_org: str | None = None

    while i < len(lines):
        text = _get_text(lines[i])
        if not text:
            i += 1
            continue

        # Try to parse as an entry
        entry, consumed = _parse_experience_entry(lines, i)
        if entry:
            # Forward the last known organization to entries that don't have one
            # (handles multi-entry same-company scenario)
            if entry.organization is None and last_org is not None:
                entry.organization = last_org
            if entry.organization:
                last_org = entry.organization
            blocks.append(entry)
            i += consumed
        else:
            # Not an entry — treat as bullet or paragraph
            if _is_bullet(lines[i], text):
                blocks.append(CVBulletBlock(text=_strip_bullet(text)))
            else:
                blocks.append(CVParagraphBlock(text=text))
            i += 1

    return blocks


def _parse_experience_entry(
    lines: list[ExtractedLine],
    start: int,
) -> tuple[CVEntryBlock | None, int]:
    """Parse one experience entry starting at index ``start``.

    Returns ``(entry, consumed_count)``.  If no entry could be parsed,
    returns ``(None, 1)`` so the caller advances by one line.

    Strategy (in priority order):

    1. Shared metadata: ``"Role at Company | Location | Date"``
    2. Pipe-separated: ``"Role | Company | Date"``
    3. Two-line: ``"Organization\\nRole | Date"`` (org on first line)
    4. Title-first: ``"Role\\nOrganization | Date"`` (title on first line)
    5. Bullet collection continues until blank line or next headline
    """
    entry = CVEntryBlock(title="")
    i = start
    lines_consumed = 1
    bullets: list[str] = []
    subtitle_parts: list[str] = []

    # --- Try shared metadata format first ---
    text = _get_text(lines[i])
    shared_match = _SHARED_META_RE.match(text)
    if shared_match:
        role = shared_match.group(1).strip()
        org = shared_match.group(2).strip()
        loc = shared_match.group(3).strip() if shared_match.group(3) else None
        extra_date = _extract_date(
            shared_match.group(4).strip() if shared_match.group(4) else ""
        )
        entry.title = role
        entry.organization = org
        if loc:
            entry.location = loc
        if extra_date:
            entry.date = extra_date
        lines_consumed += 1
        i += 1
        # Collect bullets
        while i < len(lines):
            next_text = _get_text(lines[i])
            if not next_text:
                next_index = i + 1
                while next_index < len(lines) and not _get_text(lines[next_index]):
                    next_index += 1
                if next_index < len(lines) and _is_bullet(
                    lines[next_index], _get_text(lines[next_index])
                ):
                    i = next_index
                    continue
                break
            if _is_bullet(lines[i], next_text):
                bullets.append(_strip_bullet(next_text))
                lines_consumed += 1
                i += 1
                # Wrapped continuation
                while i < len(lines):
                    nt = _get_text(lines[i])
                    if not nt:
                        break
                    if _is_bullet(lines[i], nt):
                        bullets.append(_strip_bullet(nt))
                        lines_consumed += 1
                        i += 1
                    elif bullets and nt:
                        if _looks_like_experience_boundary(lines[i], nt):
                            break
                        # Previous bullet ends mid-sentence → continuation
                        if (
                            not bullets[-1].rstrip().endswith((".", "!", "?"))
                            or nt[0].islower()
                            or _text_has_leading_space(lines[i])
                        ):
                            bullets[-1] += " " + nt.strip()
                            lines_consumed += 1
                            i += 1
                        else:
                            break
                    else:
                        break
                continue
            # Non-bullet non-blank after bullets → next entry
            if bullets:
                break
            # Metadata line
            if _is_date_line(next_text):
                entry.date = next_text
                lines_consumed += 1
                i += 1
                continue
            if _looks_like_org(next_text):
                entry.organization = next_text
                lines_consumed += 1
                i += 1
                continue
            break
        entry.bullets = bullets
        if not entry.title and not bullets:
            return None, 1
        return entry, max(i - start, 1)

    # --- Try pipe-separated format ---
    pipe_match = _PIPE_META_RE.match(text)
    if pipe_match and len(text.split("|")) >= 2:
        parts = [p.strip() for p in text.split("|") if p.strip()]
        if len(parts) >= 2:
            entry.title = parts[0]
            for part in parts[1:]:
                if _is_primary_date_line(part):
                    entry.date = part
                elif entry.organization is None:
                    entry.organization = part
                elif entry.location is None:
                    entry.location = part
                else:
                    _append_subtitle(entry, part)
            lines_consumed += 1
            i += 1
            # Collect bullets
            while i < len(lines):
                next_text = _get_text(lines[i])
                if not next_text:
                    next_index = i + 1
                    while next_index < len(lines) and not _get_text(lines[next_index]):
                        next_index += 1
                    if next_index < len(lines) and _is_bullet(
                        lines[next_index], _get_text(lines[next_index])
                    ):
                        i = next_index
                        continue
                    break
                if _is_bullet(lines[i], next_text):
                    bullets.append(_strip_bullet(next_text))
                    lines_consumed += 1
                    i += 1
                    while i < len(lines):
                        nt = _get_text(lines[i])
                        if not nt:
                            break
                        if _is_bullet(lines[i], nt):
                            bullets.append(_strip_bullet(nt))
                            lines_consumed += 1
                            i += 1
                        elif bullets and nt:
                            if _looks_like_experience_boundary(lines[i], nt):
                                break
                            if (
                                not bullets[-1].rstrip().endswith((".", "!", "?"))
                                or nt[0].islower()
                                or _text_has_leading_space(lines[i])
                            ):
                                bullets[-1] += " " + nt.strip()
                                lines_consumed += 1
                                i += 1
                            else:
                                break
                        else:
                            break
                    continue
                if bullets:
                    break
                if _is_date_line(next_text):
                    entry.date = next_text
                    lines_consumed += 1
                    i += 1
                    continue
                break
            entry.bullets = bullets
            if not entry.title and not bullets:
                return None, 1
            return entry, max(i - start, 1)

    # --- Two-line or title-first format ---
    # Look ahead to determine if first line is org or title
    # If first line is org-like and second line has pipe+date → two-line format
    # Otherwise, treat first line as title

    second_text = _get_text(lines[i + 1]) if i + 1 < len(lines) else ""
    first_is_org = (
        _looks_like_org(text, second_text)
        and not _is_job_title(text)
        and len(text) <= 90
    )
    second_has_pipe = "|" in second_text
    second_has_date = _is_date_line(second_text)

    if first_is_org and second_has_pipe:
        # Two-line format: "Organization\\nRole | Date"
        entry.organization = text
        lines_consumed += 1
        i += 1
        # Parse second line for role/date
        pipe_match2 = _PIPE_META_RE.match(second_text)
        if pipe_match2:
            parts = [p.strip() for p in second_text.split("|") if p.strip()]
            if len(parts) >= 1:
                entry.title = parts[0]
            if len(parts) >= 2 and _is_date_line(parts[1]):
                entry.date = parts[1]
            if (
                len(parts) >= 2
                and not _is_date_line(parts[1])
                and not _is_date_line(parts[0])
                and _is_date_line(parts[-1])
            ):
                entry.date = parts[-1]
        elif second_has_date:
            # Second line is just a date (unlikely but handle it)
            entry.date = second_text
        lines_consumed += 1
        i += 1
    elif first_is_org:
        # Org-only first line, rest is title/date/bullets
        entry.organization = text
        lines_consumed += 1
        i += 1
    else:
        date_in_first = _extract_date(text)
        if date_in_first:
            entry.date = date_in_first
            rem = text.replace(date_in_first, "").strip().rstrip(", -–—|")
            if "," in rem:
                parts = [p.strip() for p in rem.split(",", 1) if p.strip()]
                entry.title = parts[0]
                entry.organization = parts[1]
            elif rem:
                entry.title = rem
        elif text:
            entry.title = text
        lines_consumed += 1
        i += 1

    # Collect remaining lines (date, bullets, etc.)
    while i < len(lines):
        next_text = _get_text(lines[i])
        if not next_text:
            next_index = i + 1
            while next_index < len(lines) and not _get_text(lines[next_index]):
                next_index += 1
            if (
                next_index < len(lines)
                and _is_bullet(lines[next_index], _get_text(lines[next_index]))
                and (entry.title or entry.organization)
            ):
                i = next_index
                continue
            break

        if _is_bullet(lines[i], next_text):
            bullets.append(_strip_bullet(next_text))
            lines_consumed += 1
            i += 1
            while i < len(lines):
                nt = _get_text(lines[i])
                if not nt:
                    break
                if _is_bullet(lines[i], nt):
                    bullets.append(_strip_bullet(nt))
                    lines_consumed += 1
                    i += 1
                elif bullets and nt:
                    if _looks_like_experience_boundary(lines[i], nt):
                        break
                    if (
                        not bullets[-1].rstrip().endswith((".", "!", "?"))
                        or nt[0].islower()
                        or _text_has_leading_space(lines[i])
                    ):
                        bullets[-1] += " " + nt.strip()
                        lines_consumed += 1
                        i += 1
                    else:
                        break
                else:
                    break
            continue

        if bullets and _looks_like_experience_boundary(lines[i], next_text):
            break

        # Check for pipe-separated metadata on this line
        if "|" in next_text:
            parts = [p.strip() for p in next_text.split("|") if p.strip()]
            for part in parts:
                if _is_primary_date_line(part) and not entry.date:
                    entry.date = part
                elif _looks_like_org(part, "") and not entry.organization:
                    entry.organization = part
                elif part and not entry.title:
                    entry.title = part
            lines_consumed += 1
            i += 1
            continue

        if _is_primary_date_line(next_text):
            entry.date = next_text
            lines_consumed += 1
            i += 1
            continue

        if not entry.title:
            date_in_next = _extract_date(next_text)
            if date_in_next:
                entry.date = date_in_next
                rem = next_text.replace(date_in_next, "").strip().rstrip(", -–—|")
                if "," in rem:
                    parts = [p.strip() for p in rem.split(",", 1) if p.strip()]
                    entry.title = parts[0]
                    if len(parts) > 1:
                        _append_subtitle(entry, parts[1])
                else:
                    entry.title = rem
            elif _is_job_title(next_text) or _is_short(next_text):
                entry.title = next_text
            lines_consumed += 1
            i += 1
            continue

        if not entry.location and _is_location_line(next_text):
            entry.location = next_text
            lines_consumed += 1
            i += 1
            continue

        # Look ahead for org detection context
        next_next_text = _get_text(lines[i + 1]) if i + 1 < len(lines) else ""

        # Org on a separate line (after title)
        if _looks_like_org(next_text, next_next_text) and not entry.organization:
            org_name, loc_name = _split_organization_and_location(next_text)
            entry.organization = org_name
            if loc_name and not entry.location:
                entry.location = loc_name
            lines_consumed += 1
            i += 1
            continue

        # If we have bullets, a new non-bullet line is the next entry
        if bullets:
            break

        # Otherwise, could be subtitle or additional metadata
        if (
            entry.title
            and not entry.organization
            and _looks_like_org(next_text, next_next_text)
        ):
            org_name, loc_name = _split_organization_and_location(next_text)
            entry.organization = org_name
            if loc_name and not entry.location:
                entry.location = loc_name
            lines_consumed += 1
            i += 1
            continue

        # Otherwise collect as subtitle
        subtitle_parts.append(next_text)
        lines_consumed += 1
        i += 1

    entry.bullets = bullets
    if subtitle_parts:
        entry.subtitle = " ".join(subtitle_parts)

    if entry.organization:
        org_name, loc_name = _split_organization_and_location(entry.organization)
        entry.organization = org_name
        if loc_name and not entry.location:
            entry.location = loc_name

    if not entry.title and not bullets and not subtitle_parts:
        return None, 1

    return entry, max(i - start, 1)


_LOCATION_PATTERNS = re.compile(
    r"\b(?:Ho Chi Minh City|HCMC|Ha Noi|Hanoi|Da Nang|Asan|Seoul|Busan|South Korea|Korea|Vietnam|Viet Nam|USA|UK|Japan|Singapore|Taiwan|Germany|France|Canada|Australia)\b.*$",
    re.IGNORECASE,
)


def _split_organization_and_location(text: str) -> tuple[str, str | None]:
    """Split an organization or institution string into (name, location)."""
    m = _LOCATION_PATTERNS.search(text)
    if m:
        loc = text[m.start() :].strip(", ")
        org = text[: m.start()].strip(", -–—|")
        if org:
            return org, loc
    return text, None


def _is_location_line(text: str) -> bool:
    """Heuristic: text looks like a location."""
    lower = text.lower()
    location_keywords = (
        "hcmc",
        "ho chi minh",
        "ha noi",
        "hanoi",
        "da nang",
        "asan",
        "seoul",
        "south korea",
        "korea",
        "vietnam",
        "viet nam",
        "london",
        "paris",
        "tokyo",
        "sydney",
        "new york",
        "usa",
        "thanh pho",
        "province",
        "city",
    )
    return any(keyword in lower for keyword in location_keywords) or bool(
        re.search(r"(?:^|[,\s])(uk|tp\.?)(?:$|[,\s])", lower),
    )


def _is_institution_line(text: str) -> bool:
    """Return whether text names an educational institution."""
    lower = text.lower()
    return any(
        keyword in lower
        for keyword in ("university", "college", "institute", "đại học", "trường")
    )


def _is_degree_line(text: str) -> bool:
    """Return whether text names an academic degree."""
    lower = text.lower()
    return any(
        keyword in lower
        for keyword in (
            "bachelor",
            "master",
            "doctorate",
            "ph.d",
            "phd",
            "mba",
            "m.sc",
            "b.sc",
            "m.s.",
            "m.s",
            "b.s.",
            "b.s",
            "cử nhân",
            "thạc sĩ",
            "tiến sĩ",
            "kỹ sư",
        )
    )


# ---------------------------------------------------------------------------
# 5.2  Projects parser
# ---------------------------------------------------------------------------


def _reconstruct_projects(lines: list[ExtractedLine]) -> list[CVBlockType]:
    """Parse projects section into entry blocks.

    Similar to experience but:
    - Project titles may include tech stack indicators.
    - No organization field typically.
    - Technology metadata may appear in title or subtitle.
    """
    blocks: list[CVBlockType] = []
    i = 0

    while i < len(lines):
        text = _get_text(lines[i])
        if not text:
            i += 1
            continue

        # Try to parse as an entry
        entry, consumed = _parse_project_entry(lines, i)
        if entry:
            blocks.append(entry)
            i += consumed
        else:
            if _is_bullet(lines[i], text):
                blocks.append(CVBulletBlock(text=_strip_bullet(text)))
            else:
                blocks.append(CVParagraphBlock(text=text))
            i += 1

    return blocks


def _parse_project_entry(
    lines: list[ExtractedLine],
    start: int,
) -> tuple[CVEntryBlock | None, int]:
    """Parse one project entry starting at index ``start``."""
    raw_line = _get_text(lines[start])
    if (
        not raw_line
        or _is_bullet(lines[start], raw_line)
        or _is_primary_date_line(raw_line)
    ):
        return None, 1

    pipe_parts = [p.strip() for p in raw_line.split("|") if p.strip()]
    date_in_raw = _extract_date(raw_line)
    if len(pipe_parts) == 1 and date_in_raw:
        entry = CVEntryBlock(title=raw_line)
        entry.date = date_in_raw
        rem = raw_line.replace(date_in_raw, "").strip().rstrip(", -–—|")
        if "," in rem:
            parts = [p.strip() for p in rem.split(",", 1) if p.strip()]
            entry.title = parts[0]
            entry.organization = parts[1]
        elif rem:
            entry.title = rem
    else:
        title = pipe_parts[0] if pipe_parts else raw_line
        if not title or not title[0].isupper():
            return None, 1

        if len(pipe_parts) == 1 and not (_is_short(title) and title[0].isupper()):
            return None, 1

        entry = CVEntryBlock(title=title)
        if len(pipe_parts) > 1:
            metadata = []
            for part in pipe_parts[1:]:
                date_match = _extract_date(part)
                if date_match:
                    entry.date = date_match
                    role_rem = part.replace(date_match, "").strip().rstrip(", -–—|")
                    if role_rem:
                        metadata.append(role_rem)
                elif _is_primary_date_line(part) or _is_date_line(part):
                    entry.date = part
                else:
                    metadata.append(part)
            if metadata:
                entry.subtitle = " | ".join(metadata)

    i = start + 1

    while i < len(lines):
        text = _get_text(lines[i])
        if not text:
            next_index = i + 1
            while next_index < len(lines) and not _get_text(lines[next_index]):
                next_index += 1
            if next_index < len(lines) and _is_bullet(
                lines[next_index], _get_text(lines[next_index])
            ):
                i = next_index
                continue
            break

        if _is_bullet(lines[i], text):
            entry.bullets.append(_strip_bullet(text))
            i += 1
            while i < len(lines):
                continuation = _get_text(lines[i])
                if not continuation or _is_bullet(lines[i], continuation):
                    break
                physical_continuation = (
                    lines[i].joined_to_prev
                    or _text_has_leading_space(lines[i])
                    or continuation[0].islower()
                )
                if (
                    _looks_like_entry_headline(lines[i], continuation, lines, i)
                    and not physical_continuation
                ):
                    break
                should_join = physical_continuation or not entry.bullets[
                    -1
                ].rstrip().endswith(
                    (".", "!", "?"),
                )
                if not should_join:
                    break
                entry.bullets[-1] += " " + continuation
                i += 1
            continue

        if entry.bullets and _looks_like_entry_headline(lines[i], text, lines, i):
            break

        date_in_text = _extract_date(text)
        if date_in_text and not entry.bullets:
            entry.date = date_in_text
            role_subtitle = text.replace(date_in_text, "").strip().rstrip(", -–—|")
            if role_subtitle:
                _append_subtitle(entry, role_subtitle)
            i += 1
            continue

        if "|" in text:
            parts = [part.strip() for part in text.split("|") if part.strip()]
            metadata = []
            for part in parts:
                if _is_primary_date_line(part):
                    entry.date = part
                else:
                    metadata.append(part)
            if metadata:
                _append_subtitle(entry, " | ".join(metadata))
            i += 1
            continue

        if "," in text:
            _append_subtitle(entry, text)
            i += 1
            continue

        if _looks_like_entry_headline(lines[i], text, lines, i) and not (
            entry.subtitle is None and _is_job_title(text)
        ):
            break

        _append_subtitle(entry, text)
        i += 1

    return entry, max(i - start, 1)


# ---------------------------------------------------------------------------
# 5.3  Skills parser
# ---------------------------------------------------------------------------


def _reconstruct_skills(lines: list[ExtractedLine]) -> list[CVBlockType]:
    """Parse skills section into skill_group blocks.

    Recognizes:
      Label: item1, item2, item3
      Label2: item4, item5

    Handles wrapped continuations: lines that are continuations of the
    previous skill group are joined before splitting.
    """
    blocks: list[CVBlockType] = []

    # First, join wrapped continuation lines into logical skill-group lines
    logical_lines = _join_skill_continuations(lines)

    for line in logical_lines:
        text = _get_text(line)
        if not text:
            continue

        m = _SKILL_GROUP_RE.fullmatch(text)
        if m:
            label = text.split(":")[0].strip()
            skills_raw = m.group(1)
            skills = [s.strip() for s in skills_raw.split(",") if s.strip()]
            if skills:
                blocks.append(CVSkillGroupBlock(label=label, skills=skills))
                continue

        # Fallback: space-separated skills after a colon label
        m2 = _SKILL_GROUP_SPACE_RE.fullmatch(text)
        if m2 and "," not in text.split(":", 1)[-1]:
            label = text.split(":")[0].strip()
            skills_raw = m2.group(1)
            skills = [s.strip() for s in skills_raw.split() if s.strip()]
            if skills:
                blocks.append(CVSkillGroupBlock(label=label, skills=skills))
                continue

        # Not a skill-group pattern — bullet or paragraph
        if _is_bullet(line, text):
            blocks.append(CVBulletBlock(text=_strip_bullet(text)))
        else:
            blocks.append(CVParagraphBlock(text=text))

    return blocks


def _join_skill_continuations(
    lines: list[ExtractedLine],
) -> list[ExtractedLine]:
    """Join wrapped continuation lines into the preceding logical line.

    A continuation is when:
    - The previous line has a colon (label: ...) and ends with a comma
    - The current line starts lowercase or is indented (whitespace-prefixed)
    - The current line does not start a new skill group pattern

    Returns new list of lines where continuation text is appended to the
    previous line's ``text`` field.
    """
    if not lines:
        return []

    result: list[ExtractedLine] = []
    for line in lines:
        text = _get_text(line)
        if not text:
            continue

        if result:
            prev = result[-1]
            prev_text = _get_text(prev)

            # Check if this is a continuation of a skill group
            # Criteria:
            # 1. Previous line has a colon (label: ...)
            # 2. Previous line ends with comma (incomplete skill list)
            # 3. Current line starts with lowercase/whitespace (not a new heading)
            # 4. Current line is not a bullet
            # 5. Current line is not a new skill group
            has_colon = ":" in prev_text
            ends_with_comma = prev_text.rstrip().endswith(",")
            is_not_bullet = not _is_bullet(line, text)
            is_physical_continuation = (
                line.joined_to_prev
                or _text_has_leading_space(line)
                or text[0].islower()
            )
            is_not_new_skill_group = not _SKILL_GROUP_RE.fullmatch(text)

            if (
                has_colon
                and is_not_bullet
                and is_not_new_skill_group
                and (ends_with_comma or is_physical_continuation)
            ):
                # This is a continuation — append to previous
                prev_text_modified = prev_text.rstrip() + " " + text.strip()
                prev_copy = ExtractedLine(
                    text=prev.text,
                    page=prev.page,
                    x=prev.x,
                    y=prev.y,
                    width=prev.width,
                    height=prev.height,
                    font_size=prev.font_size,
                    font_weight=prev.font_weight,
                    bullet_marker=prev.bullet_marker,
                    normalized_text=prev_text_modified,
                    column_id=prev.column_id,
                    joined_to_prev=True,
                    is_page_break_marker=prev.is_page_break_marker,
                    is_layout_artifact=prev.is_layout_artifact,
                    page_height=prev.page_height,
                )
                result[-1] = prev_copy
                continue

        result.append(line)

    return result


# ---------------------------------------------------------------------------
# 5.4  Publications parser
# ---------------------------------------------------------------------------


def _reconstruct_publications(lines: list[ExtractedLine]) -> list[CVBlockType]:
    """Parse publications section into publication blocks.

    Joins all physical lines belonging to the same citation.
    Attempts to identify:
    - Authors
    - Title
    - Venue
    - Date
    - Status (e.g., "Under Review")

    If those parts cannot be confidently separated, the complete citation
    is stored in one publication block.  Never breaks a citation into
    a bold continuation.
    """
    blocks: list[CVBlockType] = []

    # Join all bullets into logical citations
    citations = _join_publication_citations(lines)

    for citation_text in citations:
        pub = _parse_publication_citation(citation_text)
        if pub:
            blocks.append(pub)

    return blocks


def _join_publication_citations(
    lines: list[ExtractedLine],
) -> list[str]:
    """Join physical lines into citation strings.

    A citation is typically 2-4 lines.  Lines are joined when:
    - The previous line has no terminal punctuation (or only a period
      that appears to be part of an abbreviation/title)
    - The next line is not a new section heading

    A period inside quotes ('...'') or followed by a comma is NOT
    terminal — it's part of the title or an abbreviation.
    """
    citations: list[str] = []
    current: list[str] = []

    for line in lines:
        text = _get_text(line)
        if not text:
            # Blank line ends current citation
            if current:
                citations.append(" ".join(current))
                current = []
            continue

        if current:
            prev_text = current[-1]
            # Check for terminal punctuation more carefully
            if _citation_continues(prev_text, text):
                current.append(text)
                continue
            citations.append(" ".join(current))

        # Start new citation
        current = [text]

    if current:
        citations.append(" ".join(current))

    return citations


def _citation_continues(prev_text: str, next_text: str) -> bool:
    """Determine if a citation should continue from prev_text to next_text.

    A period is NOT terminal if:
    - It's inside single or double quotes
    - It's followed by a comma (e.g. "...,' " or "...', ")
    - It appears to be part of an abbreviation
    """
    stripped_prev = prev_text.strip()
    stripped_next = next_text.strip()

    # Remove trailing whitespace
    stripped_prev = stripped_prev.rstrip()

    # If next line starts with a bullet marker, it is a new citation
    if stripped_next.startswith(("•", "-", "*", "–", "—", "▪", "▸")):
        return False

    # If previous line doesn't end with terminal punctuation, continue
    if not stripped_prev.endswith((".", "!", "?")):
        return True

    # If next text is clearly a new heading, don't continue after a complete line
    if _is_title_case_or_caps(stripped_next) and len(stripped_next.split()) <= 3:
        return False

    # Period is terminal ONLY if it's not inside quotes and not followed
    # by a comma (i.e., not "...,' " or "...', ")
    if stripped_prev.endswith((",'", "',")):
        return True  # Period inside/after quotes → not terminal

    if stripped_prev.endswith(("\"'", "'")):
        return True  # End of quoted title → not terminal

    # Period after an abbreviation (single uppercase letter + period)
    if re.search(r"\b[A-Z]\.$", stripped_prev):
        return True  # Abbreviation → not terminal

    # Period after common academic abbreviations
    if re.search(r"\b(vol|no|pp|et\s+al|etc)\.$", stripped_prev, re.IGNORECASE):
        return True

    # Period followed by comma → not terminal
    if stripped_prev.endswith((",", ".")) and "," in prev_text:
        # Check if there's a comma after the last period
        last_period_idx = prev_text.rfind(".")
        last_comma_idx = prev_text.rfind(",")
        if last_comma_idx > last_period_idx:
            return True

    return False


def _parse_publication_citation(text: str) -> CVPublicationBlock | None:
    """Parse a full citation string into a CVPublicationBlock."""
    if not text:
        return None

    stripped = _strip_bullet(text).strip()
    pub = CVPublicationBlock(title=stripped)

    # 1. Quoted title format
    authors, rest = _split_authors_from_citation(stripped)
    if authors:
        pub.authors = authors
        stripped = rest

    title, rest = _split_title_from_citation(stripped)
    if title:
        pub.title = title
        stripped = rest

    venue, date, status = _split_venue_from_citation(stripped)
    if venue:
        pub.venue = venue
    if date:
        pub.date = date
    if status:
        pub.status = status

    # 2. Period-separated format fallback: "Authors. Title. Venue, Date."
    if not pub.authors and not pub.venue and "." in pub.title:
        parts = [p.strip() for p in pub.title.split(".") if p.strip()]
        if len(parts) >= 2:
            # Check if first part contains "et al." or author names
            if "et al" in parts[0].lower() or re.search(r"\b[A-Z]\b", parts[0]):
                pub.authors = parts[0]
                parts = parts[1:]
            if len(parts) >= 2:
                pub.title = parts[0]
                tail = ". ".join(parts[1:])
                v, d, s = _split_venue_from_citation(tail)
                pub.venue = v
                pub.date = d
                pub.status = s
            elif len(parts) == 1:
                v, d, s = _split_venue_from_citation(parts[0])
                if d or s:
                    pub.date = d
                    pub.status = s
                    pub.venue = v

    return pub


def _split_authors_from_citation(text: str) -> tuple[str, str]:
    """Split authors from the beginning of a citation."""
    for q in ("'", '"', "“", "”"):
        quote_idx = text.find(q)
        if quote_idx == 0:
            return "", text
        if quote_idx > 0:
            authors_text = text[:quote_idx].strip().rstrip(",.")
            rest = text[quote_idx:].lstrip()
            return authors_text, rest

    stop_patterns = [
        "proceedings",
        "journal",
        "conference",
        "volume",
        "IEEE",
        "ACM",
        "Springer",
        "Elsevier",
        "CVPR",
        "ICML",
        "NeurIPS",
        "SIGIR",
    ]
    parts = text.split(",")
    author_parts = []
    rest = text

    for part in parts:
        stripped = part.strip()
        if not stripped:
            continue
        if any(kw.lower() in stripped.lower() for kw in stop_patterns):
            rest = part + ",".join(parts[parts.index(part) :])
            break
        if any(
            kw.lower() in stripped.lower()
            for kw in [
                "proceedings",
                "journal",
                "conference",
                "volume",
                "vol.",
                "pp.",
                "no.",
                "202",
                "201",
                "200",
            ]
        ):
            rest = part + ",".join(parts[parts.index(part) :])
            break
        author_parts.append(stripped)

    if author_parts:
        authors = ", ".join(author_parts)
        rest = ",".join(parts[len(author_parts) :]).lstrip(", ")
        return authors, rest

    return "", text


def _split_title_from_citation(text: str) -> tuple[str, str]:
    """Split title from citation text."""
    if text.startswith(("'", '"', "“", "”")):
        q_start = text[0]
        q_end = "”" if q_start == "“" else q_start
        end_quote = text.find(q_end, 1)
        if end_quote > 0:
            title = text[1:end_quote].strip()
            rest = text[end_quote + 1 :].lstrip(",. ")
            return title, rest

    parts = text.split(",")
    title_parts = []
    for part in parts[:-1]:
        stripped = part.strip()
        if stripped and len(stripped.split()) > 2:
            title_parts.append(stripped)

    if title_parts:
        title = ", ".join(title_parts)
        rest = parts[-1].strip() if parts else ""
        return title, rest

    return "", text


def _split_venue_from_citation(text: str) -> tuple[str | None, str | None, str | None]:
    """Split venue, date, and status from remaining citation text."""
    if not text:
        return None, None, None

    venue: str | None = None
    date: str | None = None
    status: str | None = None

    # Check for status indicator
    for status_kw in ["under review", "in press", "accepted", "forthcoming"]:
        if status_kw in text.lower():
            status = status_kw.title() if status_kw != "in press" else "In Press"
            text = text[: text.lower().index(status_kw)].rstrip("—, ").strip()
            break

    # Extract date
    date_match = _DATE_RANGE_RE.search(text)
    if date_match:
        date = date_match.group(0)
        text = text[: date_match.start()].rstrip(", .").strip()

    # Remaining text is likely the venue
    if text and text.strip():
        venue = text.strip().rstrip(". ,")

    return venue, date, status


# ---------------------------------------------------------------------------
# 5.5  Education parser
# ---------------------------------------------------------------------------


def _reconstruct_education(lines: list[ExtractedLine]) -> list[CVBlockType]:
    """Parse education section into education blocks.

    Identifies:
    - Institution
    - Degree
    - Field
    - Location
    - Date
    - Supporting details (GPA, honors, thesis)
    """
    blocks: list[CVBlockType] = []
    i = 0

    while i < len(lines):
        text = _get_text(lines[i])
        if not text:
            i += 1
            continue

        edu, consumed = _parse_education_record(lines, i)
        if edu:
            blocks.append(edu)
            i += consumed
        else:
            if _is_bullet(lines[i], text):
                blocks.append(CVBulletBlock(text=_strip_bullet(text)))
            else:
                blocks.append(CVParagraphBlock(text=text))
            i += 1

    return blocks


def _parse_education_record(
    lines: list[ExtractedLine],
    start: int,
) -> tuple[CVEducationBlock | None, int]:
    """Parse one education record starting at index ``start``."""
    edu = CVEducationBlock()
    i = start

    while i < len(lines):
        text = _get_text(lines[i])
        if not text:
            break

        if i > start and _is_institution_line(text) and edu.institution is not None:
            break
        if i > start and _is_degree_line(text) and edu.degree is not None:
            break

        parts = [part.strip() for part in text.split("|") if part.strip()]
        for part in parts:
            date_match = _extract_date(part)
            if date_match and not edu.date:
                edu.date = date_match
                part = part.replace(date_match, "").strip().rstrip("; ,")

            sub_parts = [sp.strip() for sp in part.split(";") if sp.strip()]
            for sp in sub_parts:
                lower = sp.lower()
                if _is_degree_line(sp) and edu.degree is None:
                    degree, field = _split_degree_and_field(sp)
                    edu.degree = degree
                    edu.field = field
                elif _is_institution_line(sp) and edu.institution is None:
                    edu.institution = sp
                elif _is_location_line(sp) and edu.location is None:
                    edu.location = sp
                elif (
                    "gpa" in lower
                    or "grade" in lower
                    or "focus:" in lower
                    or "thesis:" in lower
                    or _is_bullet(lines[i], sp)
                ):
                    edu.details.append(_strip_bullet(sp))
                elif (
                    edu.degree is not None
                    and edu.field is None
                    and not _is_institution_line(sp)
                    and not _is_location_line(sp)
                ):
                    edu.field = sp
                elif edu.institution is None and len(parts) > 1:
                    edu.institution = sp
                else:
                    edu.details.append(sp)
        i += 1

    if edu.institution:
        inst_name, loc_name = _split_organization_and_location(edu.institution)
        edu.institution = inst_name
        if loc_name and not edu.location:
            edu.location = loc_name

    # Must have at least some content
    if any(
        [
            edu.institution,
            edu.degree,
            edu.field,
            edu.location,
            edu.date,
            edu.details,
        ],
    ):
        return edu, max(i - start, 1)
    return None, 1


def _split_degree_and_field(text: str) -> tuple[str, str | None]:
    """Split common ``Degree in Field`` forms without guessing other text."""
    match = re.match(
        r"^(.+?\b(?:Science|Arts|Engineering|Philosophy|Administration))\s+in\s+(.+)$",
        text,
        re.IGNORECASE,
    )
    if not match:
        return text, None
    return match.group(1).strip(), match.group(2).strip()


# ---------------------------------------------------------------------------
# 5.6  Simple-section parsers
# ---------------------------------------------------------------------------


def _reconstruct_simple_section(
    lines: list[ExtractedLine],
    section_type: str,
) -> list[CVBlockType]:
    """Conservative handlers for certifications, languages, awards, activities, interests.

    Each item becomes an entry block if it has metadata, or a paragraph block
    otherwise.
    """
    blocks: list[CVBlockType] = []
    i = 0

    while i < len(lines):
        text = _get_text(lines[i])
        if not text:
            i += 1
            continue

        # Certifications: "Title | Issuer | Date" or "Title (Date)"
        if section_type == "certifications":
            entry, consumed = _parse_certification(lines, i)
            if entry:
                blocks.append(entry)
                i += consumed
                continue

        # Languages: "Language (proficiency)" format
        if section_type == "languages":
            entry, consumed = _parse_language(lines, i)
            if entry:
                blocks.append(entry)
                i += consumed
                continue

        # Awards: single-line entries with optional date
        if section_type == "awards":
            entry, consumed = _parse_award(lines, i)
            if entry:
                blocks.append(entry)
                i += consumed
                continue

        # Activities / interests: paragraph blocks
        if section_type in ("activities", "interests"):
            blocks.append(CVParagraphBlock(text=text))
            i += 1
            continue

        # Default: paragraph
        blocks.append(CVParagraphBlock(text=text))
        i += 1

    return blocks


def _parse_certification(
    lines: list[ExtractedLine],
    start: int,
) -> tuple[CVEntryBlock | None, int]:
    """Parse a certification entry."""
    text = _strip_bullet(_get_text(lines[start])).strip()
    if not text:
        return None, 1

    entry = CVEntryBlock(title=text)

    # 1. Extract date if present
    date_match = _extract_date(text)
    if date_match:
        entry.date = date_match
        text = text.replace(date_match, "").strip().rstrip("() -–—|")

    # 2. Extract title and organization separated by dash or pipe
    known_issuers = (
        "ibm",
        "deeplearning.ai",
        "deeplearning",
        "coursera",
        "udemy",
        "edx",
        "google",
        "microsoft",
        "oracle",
        "cisco",
        "meta",
        "linkedin",
    )
    if "|" in text:
        parts = [p.strip() for p in text.split("|") if p.strip()]
        if parts:
            entry.title = parts[0]
            if len(parts) > 1:
                entry.organization = parts[1]
    elif " – " in text or " - " in text or " — " in text:
        parts = [p.strip() for p in re.split(r"\s+[—–-]\s+", text) if p.strip()]
        if len(parts) > 1:
            p0_lower = parts[0].lower()
            p1_lower = parts[1].lower()
            if p0_lower in known_issuers or any(p0_lower == ki for ki in known_issuers):
                entry.organization = parts[0]
                entry.title = parts[1]
            elif (
                _is_institution_line(parts[1])
                or _ORG_SUFFIXES_RE.search(parts[1])
                or any(
                    k in p1_lower
                    for k in ("council", "institute", "university", "academy")
                )
            ):
                entry.title = parts[0]
                entry.organization = parts[1]
            else:
                entry.title = text
    elif text:
        entry.title = text

    return entry, 1


def _parse_language(
    lines: list[ExtractedLine],
    start: int,
) -> tuple[CVEntryBlock | None, int]:
    """Parse a language entry."""
    entry = CVEntryBlock(title="")
    text = _get_text(lines[start])

    # "Language (proficiency)" or "Language — Proficiency"
    paren_match = re.search(r"^(.+?)\s*[（(](.+?)[）)]\s*$", text)
    if paren_match:
        entry.title = paren_match.group(1).strip()
        entry.subtitle = paren_match.group(2).strip()
        return entry, 1

    # "Language — Proficiency"
    dash_match = re.search(r"^(.+?)\s*[—–-]\s+(.+)$", text)
    if dash_match:
        entry.title = dash_match.group(1).strip()
        entry.subtitle = dash_match.group(2).strip()
        return entry, 1

    # Single language name
    if _is_short(text):
        entry.title = text
        return entry, 1

    return None, 1


def _parse_award(
    lines: list[ExtractedLine],
    start: int,
) -> tuple[CVEntryBlock | None, int]:
    """Parse an award entry."""
    entry = CVEntryBlock(title="")
    text = _get_text(lines[start])

    # "Award name (Year)" or "Award name — Year"
    paren_match = re.search(r"^(.+?)\s*\((\d{4})\)\s*$", text)
    if paren_match:
        entry.title = paren_match.group(1).strip()
        entry.date = paren_match.group(2)
        return entry, 1

    dash_match = re.search(r"^(.+?)\s*[—–-]\s*(\d{4})\s*$", text)
    if dash_match:
        entry.title = dash_match.group(1).strip()
        entry.date = dash_match.group(2)
        return entry, 1

    # Single-line award
    if _is_short(text) and _is_title_case_or_caps(text):
        entry.title = text
        return entry, 1

    return None, 1


# ---------------------------------------------------------------------------
# 5.7  Unknown-section fallback
# ---------------------------------------------------------------------------


def _reconstruct_unknown_section(
    lines: list[ExtractedLine],
) -> list[CVBlockType]:
    """Fallback for unknown/custom sections.

    Preserves content with neutral formatting rather than guessing a headline.
    """
    blocks: list[CVBlockType] = []
    non_empty = [_get_text(line) for line in lines if _get_text(line)]

    if non_empty:
        blocks.append(
            CVUnknownBlock(
                lines=non_empty,
                confidence=0.3,
            )
        )
    return blocks


# ---------------------------------------------------------------------------
# Entry point: dispatch to the correct parser
# ---------------------------------------------------------------------------


def reconstruct_blocks(
    section_type: str,
    lines: list[ExtractedLine],
    claimed_line_ids: set[str] | None = None,
    section_title: str | None = None,
) -> list[CVBlockType]:
    """Reconstruct typed blocks for a detected section.

    Dispatches to the appropriate section-specific parser based on
    ``section_type``.

    This is the Phase 5 entry point.  Called from ``detect_sections()``
    after section boundaries have been identified.
    """
    if not lines:
        return []

    if section_type == "experience":
        blocks = _reconstruct_experience(lines)
    elif section_type == "projects":
        blocks = _reconstruct_projects(lines)
    elif section_type == "skills":
        blocks = _reconstruct_skills(lines)
    elif section_type == "publications":
        blocks = _reconstruct_publications(lines)
    elif section_type == "education":
        blocks = _reconstruct_education(lines)
    elif section_type in (
        "certifications",
        "languages",
        "awards",
        "activities",
        "interests",
    ):
        blocks = _reconstruct_simple_section(lines, section_type)
    else:
        blocks = _reconstruct_unknown_section(lines)

    return attach_reconstruction_metadata(
        blocks,
        lines,
        section_type,
        claimed_line_ids=claimed_line_ids,
        section_title=section_title,
    )


def _line_matches_block(line_text: str, block: CVBlockType) -> bool:
    line_clean = _strip_bullet(line_text).casefold().strip()
    line_clean = re.sub(r'[“”"\'`’]', "", line_clean)
    if not line_clean:
        return False

    primary_values: list[str] = []
    date_val = getattr(block, "date", None)
    date_clean = _strip_bullet(date_val).casefold().strip() if date_val else ""

    for val in _block_text_values(block):
        val_clean = _strip_bullet(val).casefold().strip()
        val_clean = re.sub(r'[“”"\'`’]', "", val_clean)
        if not val_clean:
            continue
        if val_clean == date_clean and re.match(
            r"^(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec|\d{4}|present|current|\s|-|/)+$",
            val_clean,
        ):
            continue
        primary_values.append(val_clean)

    # First match primary values (title, organization, bullets)
    for val_clean in primary_values:
        if len(val_clean) >= 3 and len(line_clean) >= 3:
            if val_clean in line_clean or line_clean in val_clean:
                return True
        else:
            if re.search(
                rf"(?<!\w){re.escape(val_clean)}(?!\w)", line_clean
            ) or re.search(rf"(?<!\w){re.escape(line_clean)}(?!\w)", val_clean):
                return True
        line_tokens = set(re.findall(r"\w+", line_clean))
        val_tokens = set(re.findall(r"\w+", val_clean))
        if line_tokens and val_tokens:
            overlap = len(line_tokens & val_tokens) / float(
                min(len(line_tokens), len(val_tokens))
            )
            if overlap >= 0.6:
                return True

    # Fallback: date matching ONLY if the line itself is a standalone date line
    return bool(
        date_clean
        and re.match(
            r"^(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec|\d{4}|present|current|\s|-|/)+$",
            line_clean,
        )
        and (date_clean in line_clean or line_clean in date_clean)
    )


def _line_exactly_matches_block(line_text: str, block: CVBlockType) -> bool:
    """Return whether a physical line exactly matches one block value."""
    line_clean = _strip_bullet(line_text).casefold().strip()
    line_clean = re.sub(r'[“”"\'`’]', "", line_clean)
    if not line_clean:
        return False

    return any(
        line_clean
        == re.sub(
            r'[“”"\'`’]',
            "",
            _strip_bullet(value).casefold().strip(),
        )
        for value in _block_text_values(block)
        if value
    )


def attach_reconstruction_metadata(
    blocks: list[CVBlockType],
    lines: list[ExtractedLine],
    section_type: str,
    claimed_line_ids: set[str] | None = None,
    section_title: str | None = None,
) -> list[CVBlockType]:
    """Attach confidence, source provenance, and parser warnings."""
    available_lines = [line for line in lines if _get_text(line)]
    all_source_ids = [
        line.source_line_id or f"p{line.page + 1}-l{index + 1}"
        for index, line in enumerate(available_lines)
    ]

    if claimed_line_ids is None:
        claimed_line_ids = set()

    positional_one_to_one = len(blocks) == len(available_lines) and all(
        line_id not in claimed_line_ids for line_id in all_source_ids
    )

    for block_idx, block in enumerate(blocks):
        block_line_ids: list[str] = []
        explicit_line_ids = list(dict.fromkeys(block.source_line_ids))
        if explicit_line_ids:
            available_ids = set(all_source_ids)
            for line_id in explicit_line_ids:
                if line_id in available_ids and line_id not in claimed_line_ids:
                    block_line_ids.append(line_id)
                    claimed_line_ids.add(line_id)
        elif positional_one_to_one:
            line_id = all_source_ids[block_idx]
            block_line_ids = [line_id]
            claimed_line_ids.add(line_id)
        else:
            unclaimed_lines = [
                (index, line)
                for index, line in enumerate(available_lines)
                if (line.source_line_id or f"p{line.page + 1}-l{index + 1}")
                not in claimed_line_ids
            ]
            exact_matches = [
                (index, line)
                for index, line in unclaimed_lines
                if _line_exactly_matches_block(_get_text(line), block)
            ]

            # Paragraph, bullet and skill-group blocks represent one physical
            # source line. Claiming every overlapping line here starves later
            # blocks that share a term (for example, "Python" and
            # "Python FastAPI"). Composite entries may legitimately own
            # several exact lines, such as title, organization and bullets.
            if exact_matches and isinstance(
                block,
                (CVParagraphBlock, CVBulletBlock, CVSkillGroupBlock),
            ):
                exact_matches = exact_matches[:1]

            candidate_lines = exact_matches or unclaimed_lines
            later_blocks = blocks[block_idx + 1 :]
            for index, line in candidate_lines:
                line_id = line.source_line_id or f"p{line.page + 1}-l{index + 1}"
                line_txt = _get_text(line).strip()
                if not exact_matches and any(
                    _line_exactly_matches_block(line_txt, later_block)
                    for later_block in later_blocks
                ):
                    continue
                if line_id not in claimed_line_ids and _line_matches_block(
                    line_txt, block
                ):
                    block_line_ids.append(line_id)
                    claimed_line_ids.add(line_id)
                    # For single-item block section types (like publications/certifications), stop after 1 line match
                    if section_type in (
                        "publications",
                        "certifications",
                        "languages",
                        "awards",
                        "interests",
                    ) and line_txt.startswith(("•", "-", "*", "–", "—", "▪", "▸")):
                        break

        if block_line_ids:
            block.source_line_ids = block_line_ids
        else:
            unclaimed = [lid for lid in all_source_ids if lid not in claimed_line_ids]
            if unclaimed:
                # Assign the next available unclaimed line in this section
                chosen_id = unclaimed[0]
                block.source_line_ids = [chosen_id]
                claimed_line_ids.add(chosen_id)
            else:
                block.source_line_ids = []
                block.reconstruction_warnings.append("missing_line_provenance")
                _logger.warning(
                    "Provenance allocation failed: section_type=%s, "
                    "block_index=%d, block_type=%s, section_lines=%d, "
                    "claimed_line_ids=%d, explicit_line_ids=%d",
                    section_type,
                    block_idx,
                    block.type,
                    len(available_lines),
                    len(claimed_line_ids),
                    len(explicit_line_ids),
                )

        stable_seed = "|".join(
            [
                section_type,
                section_title or "",
                str(block_idx),
                block.type,
                *_block_text_values(block),
            ],
        )
        block.block_id = (
            f"{section_type}-{sha256(stable_seed.encode('utf-8')).hexdigest()[:12]}"
        )
        block.confidence = _block_confidence(block)

        if isinstance(block, CVUnknownBlock):
            block.reconstruction_warnings.append("unknown_section")
        elif section_type in {"experience", "projects"} and isinstance(
            block,
            CVParagraphBlock,
        ):
            block.reconstruction_warnings.append("ambiguous_entry_boundary")
        elif isinstance(block, CVPublicationBlock) and not (
            (block.venue or block.status) and (block.date or block.title)
        ):
            block.reconstruction_warnings.append("publication_parse_incomplete")

    return blocks


def _block_text_values(block: CVBlockType) -> list[str]:
    values: list[str] = []
    for field_name in (
        "title",
        "subtitle",
        "organization",
        "location",
        "date",
        "text",
        "label",
        "authors",
        "venue",
        "status",
        "institution",
        "degree",
        "field",
    ):
        value = getattr(block, field_name, None)
        if isinstance(value, str) and value:
            values.append(value)
    for field_name in ("bullets", "skills", "details", "lines"):
        value = getattr(block, field_name, None)
        if isinstance(value, list):
            values.extend(str(item) for item in value)
    return values


def _block_confidence(block: CVBlockType) -> float:
    if isinstance(block, CVUnknownBlock):
        return min(block.confidence, 0.3)
    if isinstance(block, CVParagraphBlock):
        return 0.65
    if isinstance(block, CVBulletBlock):
        return 0.75
    if isinstance(block, CVEntryBlock):
        return (
            0.9
            if block.title
            and (block.organization or block.date or block.bullets or block.subtitle)
            else 0.65
        )
    if isinstance(block, CVSkillGroupBlock):
        return 0.9 if block.skills else 0.4
    if isinstance(block, CVPublicationBlock):
        return 0.9 if block.venue and block.date else 0.6
    if isinstance(block, CVEducationBlock):
        return 0.9 if block.institution and (block.degree or block.date) else 0.6
    return 0.5
