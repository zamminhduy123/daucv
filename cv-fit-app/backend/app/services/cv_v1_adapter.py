"""V1 → V2 Compatibility Adapter

Converts the legacy ``TailoredCV`` model (``sections[].items: string[]``)
into a ``CVDocumentV2`` without inventing facts.  The adapter is deterministic:
it never calls the LLM and never discards content.

Rules
-----
* Recognized bullets → bullet blocks (inside entry blocks when preceded by
  an entry headline, or as standalone bullet blocks).
* Clearly recognized entry titles → entry blocks.
* Uncertain non-bullet content → paragraph or unknown block.
* Never highlight uncertain content.
* Never discard content.
"""

import logging
import re
import unicodedata

from app.models.cv_document_v2 import (
    CVBlockType,
    CVBulletBlock,
    CVDocumentV2,
    CVEducationBlock,
    CVEntryBlock,
    CVIdentity,
    CVParagraphBlock,
    CVPublicationBlock,
    CVSection,
    CVSkillGroupBlock,
)
from app.models.domain import TailoredCV, TailoredCVSection

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Section-type heuristics
# ---------------------------------------------------------------------------

_SECTIONS_EXPERIENCE = {
    "work experience",
    "experience",
    "professional experience",
    "employment history",
    "work history",
    "career history",
    "kinh nghiem",
    "kinh nghiem lam viec",
    "kinh nghem",
    "qua trinh lam viec",
    "lich su lam viec",
}

_SECTIONS_PROJECTS = {
    "projects",
    "personal projects",
    "academic projects",
    "du an",
    "du an ca nhan",
    "cac du an",
    "kinh nghiem du an",
}

_SECTIONS_SKILLS = {
    "technical skills",
    "skills",
    "key skills",
    "core competencies",
    "ky nang",
    "ky nang chuyen mon",
    "ky nang mem",
    "cong nghe su dung",
    "cong nghe",
}

_SECTIONS_EDUCATION = {
    "education",
    "education & certifications",
    "hoc van",
    "trinh do hoc van",
    "bang cap",
    "qua trinh hoc tap",
}

_SECTIONS_PUBLICATIONS = {
    "publications",
    "cong bo khoa hoc",
}

_SECTIONS_CERTIFICATIONS = {
    "certifications",
    "certificates",
    "professional certifications",
    "chung chi",
    "chung chi nghe nghiep",
    "chung nhan",
}

_SECTIONS_LANGUAGES = {
    "languages",
    "ngoai ngu",
    "ngon ngu",
}

_SECTIONS_SUMMARY = {
    "summary",
    "professional summary",
    "profile",
    "about me",
    "tom tat",
    "gioi thieu",
    "muc tieu nghe nghiep",
}

_SECTIONS_OTHER = {
    "awards",
    "giai thuong",
    "thanh tuu",
    "volunteering",
    "hoat dong",
    "hoat dong xa hoi",
    "hoat dong tinh nguyen",
    "activities",
    "interests",
    "hobbies",
    "lien he",
    "contact",
    "contact information",
    "thong tin ca nhan",
    "thong tin lien he",
    "so luoc",
    "additional information",
}


def _normalize_heading(value: str) -> str:
    """Lowercase, strip accents, strip trailing colon."""
    decomposed = unicodedata.normalize("NFKD", value.rstrip(":").strip().lower())
    return "".join(ch for ch in decomposed if not unicodedata.combining(ch))


def _classify_section(section: TailoredCVSection) -> str:
    """Return a CVSectionType guess for a TailoredCVSection."""
    norm = _normalize_heading(section.title)
    if norm in _SECTIONS_SUMMARY:
        return "summary"
    if norm in _SECTIONS_EXPERIENCE:
        return "experience"
    if norm in _SECTIONS_PROJECTS:
        return "projects"
    if norm in _SECTIONS_SKILLS:
        return "skills"
    if norm in _SECTIONS_EDUCATION:
        return "education"
    if norm in _SECTIONS_PUBLICATIONS:
        return "publications"
    if norm in _SECTIONS_CERTIFICATIONS:
        return "certifications"
    if norm in _SECTIONS_LANGUAGES:
        return "languages"
    if any(t in norm for t in _SECTIONS_OTHER):
        if "award" in norm or "thanh tuu" in norm:
            return "awards"
        if "hoat dong" in norm or "volunteer" in norm:
            return "activities"
        if "interest" in norm or "hobby" in norm:
            return "interests"
        return "custom"
    return "custom"


# ---------------------------------------------------------------------------
# Entry detection heuristics
# ---------------------------------------------------------------------------

_ROLE_TOKENS = {
    "engineer",
    "developer",
    "designer",
    "manager",
    "lead",
    "analyst",
    "consultant",
    "ky su",
    "lap trinh vien",
    "chuyen vien",
    "quan ly",
    "intern",
    "fresher",
    "junior",
    "senior",
    "specialist",
    "director",
    "vp",
    "ceo",
    "cto",
    "cfo",
    "co founder",
    "founder",
    "teacher",
    "gia su",
    "nhan vien",
    "truong",
    "scientist",
    "researcher",
    "architect",
    "plumber",
    "nurse",
}

_DATE_TOKENS = {"present", "hien tai", "nay", "20", "19"}


def _is_entry_headline(item: str) -> bool:
    """Heuristic: does *item* look like a job/project entry headline?"""
    stripped = item.lstrip("•●▪◦ ").strip()
    if not stripped:
        return False
    if stripped[0].islower():
        return False
    if re.search(r"[.!?;:]$", stripped):
        return False
    lowered = stripped.lower()
    # Year pattern such as "2020 to 2023"
    if re.search(r"\b(20|19)\d{2}\b", lowered):
        return True
    # Role keyword pattern: "Software Engineer at ABC"
    if any(re.search(rf"\b{re.escape(t)}\b", lowered) for t in _ROLE_TOKENS):
        return True
    # Dash-separated project/company or project/technology patterns
    # A line with an en-dash/em-dash or slash that has capitalised parts on both sides
    return bool(
        re.search(r"[—–]\s*[A-Z]", stripped) or re.search(r" /\s*[A-Z]", stripped),
    )


_EDUCATION_HEADLINE_TOKENS = {
    "university",
    "college",
    "school",
    "institute",
    "academy",
    "dai hoc",
    "cao dang",
    "hoc vien",
    "truong",
}

_EDUCATION_NAME_CONNECTORS = {
    "of",
    "the",
    "and",
    "for",
    "in",
    "dai",
    "hoc",
    "cao",
    "dang",
    "vien",
    "truong",
}


def _is_education_headline(item: str) -> bool:
    """Highlight only institution-name-shaped legacy education lines."""
    stripped = item.strip()
    if not stripped or re.search(r"[.!?;:]$", stripped):
        return False
    candidate_original = re.sub(
        r"\s*(?:[—–|-]\s*)?(?:19|20)\d{2}(?:\s*[—–-]\s*(?:19|20)\d{2})?.*$",
        "",
        stripped,
    ).strip(" —–|-\t")
    normalized = _normalize_heading(candidate_original)
    if not any(
        re.search(rf"\b{re.escape(token)}\b", normalized)
        for token in _EDUCATION_HEADLINE_TOKENS
    ):
        return False
    words = re.findall(r"[^\W\d_]+", candidate_original, re.UNICODE)
    return bool(words) and all(
        word.lower() in _EDUCATION_NAME_CONNECTORS or word[0].isupper()
        for word in words
    )


# ---------------------------------------------------------------------------
# Skill-group detection
# ---------------------------------------------------------------------------


def _looks_like_skill_group(item: str) -> tuple[bool, tuple[str, list[str]] | None]:
    """Return (is_group, (label, skills) | None)."""
    match = re.match(r"^([A-ZÀ-Ỹa-zà-ỹÀ-ă][^\r\n:]{1,30})\s*:\s*(.+)$", item)
    if not match:
        return False, None
    label = match.group(1).strip()
    skills_raw = match.group(2).strip()
    # Must look like a comma/ampersand-separated list of short tokens
    parts = [s.strip() for s in re.split(r"[,;·&]+", skills_raw) if s.strip()]
    if len(parts) < 2 or len(parts) > 12:
        return False, None
    if any(len(p) < 1 for p in parts):
        return False, None
    return True, (label, [p for p in parts])


# ---------------------------------------------------------------------------
# Line continuation (wrapped bullets)
# ---------------------------------------------------------------------------

_BULLET_START = re.compile(r"^[•●▪◦]\s*")


def _normalize_items(items: list[str]) -> list[str]:
    """Join wrapped continuation lines (lowercase after a bullet)."""
    normalized: list[str] = []
    for item in items:
        stripped = item.strip()
        if not stripped:
            continue
        if (
            normalized
            and _BULLET_START.match(normalized[-1])
            and stripped
            and stripped[0].islower()
        ):
            normalized[-1] = f"{normalized[-1].rstrip()} {stripped}"
        else:
            normalized.append(item)
    return normalized


# ---------------------------------------------------------------------------
# Public adapter
# ---------------------------------------------------------------------------


def v1_to_v2(cv: TailoredCV) -> CVDocumentV2:
    """Convert a legacy ``TailoredCV`` document into ``CVDocumentV2``.

    This function is deterministic and never discards content.  Uncertain
    content becomes paragraph or unknown blocks instead of being forced into
    entry or heading structures.
    """
    # --- Identity -----------------------------------------------------------
    identity = CVIdentity(
        name=cv.name or "",
        headline=cv.headline or "",
        contact_lines=[line for line in (cv.contact_lines or []) if line.strip()],
    )

    # --- Summary ------------------------------------------------------------
    summary_block: CVParagraphBlock | None = None
    summary_parts = [cv.summary.strip()] if cv.summary and cv.summary.strip() else []
    for section in cv.sections or []:
        if _classify_section(section) != "summary":
            continue
        section_summary = " ".join(_normalize_items(section.items)).strip()
        if section_summary and section_summary not in summary_parts:
            summary_parts.append(section_summary)
    if summary_parts:
        summary_block = CVParagraphBlock(
            block_id="v1-summary",
            text="\n".join(summary_parts),
        )

    # --- Sections -----------------------------------------------------------
    sections: list[CVSection] = []
    for section in cv.sections or []:
        if not section.title and not section.items:
            continue
        section_type = _classify_section(section)
        # Summary content is already in summary_block; skip it from sections
        if section_type == "summary":
            continue
        blocks = _section_to_blocks(section)
        sections.append(
            CVSection(type=section_type, title=section.title, blocks=blocks),
        )

    # --- Fallback: derive from legacy fields --------------------------------
    if not sections:
        if cv.experience:
            sec = CVSection(
                id="experience",
                type="experience",
                title="Experience",
                blocks=_experience_to_blocks(cv.experience),
            )
            sections.append(sec)
        if cv.skills:
            sections.append(
                CVSection(
                    id="skills",
                    type="skills",
                    title="Skills",
                    blocks=[CVSkillGroupBlock(skills=cv.skills)],
                ),
            )
        if cv.education and cv.education.strip():
            sections.append(
                CVSection(
                    id="education",
                    type="education",
                    title="Education",
                    blocks=[CVEducationBlock(details=[cv.education.strip()])],
                ),
            )

    for section_index, section in enumerate(sections):
        section.id = f"v1-section-{section_index}"
        for block_index, block in enumerate(section.blocks):
            block.block_id = f"{section.id}-block-{block_index}"

    return CVDocumentV2(
        schema_version=2,
        reconstruction_version=1,
        requires_reprocessing=True,
        identity=identity,
        summary=summary_block,
        sections=sections,
    )


# ---------------------------------------------------------------------------
# Section parsers
# ---------------------------------------------------------------------------


def _section_to_blocks(section: TailoredCVSection) -> list[CVBlockType]:
    """Parse items in a TailoredCVSection into typed blocks."""
    items = _normalize_items(section.items)
    section_type = _classify_section(section)

    if section_type == "skills":
        return _parse_skill_section(items)

    if section_type in ("publications",):
        return _parse_publications_section(items)

    if section_type == "education":
        return _parse_education_section(items)

    # General: entries + bullets
    return _parse_general_section(items, section_type == "summary")


# ---------------------------------------------------------------------------
# Skill section parser
# ---------------------------------------------------------------------------


def _parse_skill_section(items: list[str]) -> list[CVBlockType]:
    """Split skill items into labeled skill groups when possible."""
    groups: list[CVSkillGroupBlock] = []
    loose: list[str] = []

    for item in items:
        is_group, info = _looks_like_skill_group(item)
        if is_group:
            label, skills = info
            groups.append(CVSkillGroupBlock(label=label, skills=skills))
        else:
            cleaned = item.lstrip("•●▪◦ ").strip()
            if cleaned:
                loose.append(cleaned)

    if groups:
        if loose:
            groups.append(CVSkillGroupBlock(skills=loose))
        return groups
    if loose:
        return [CVSkillGroupBlock(skills=loose)]
    return [CVParagraphBlock(text=" ".join(items))]


# ---------------------------------------------------------------------------
# Publications section parser
# ---------------------------------------------------------------------------


def _parse_publications_section(items: list[str]) -> list[CVBlockType]:
    blocks: list[CVPublicationBlock] = []
    current: list[str] = []

    for item in items:
        cleaned = item.lstrip("•●▪◦ ").strip()
        if not cleaned:
            continue
        if current and _is_entry_headline(cleaned):
            blocks.append(CVPublicationBlock(title=" ".join(current)))
            current = [cleaned]
        else:
            current.append(cleaned)

    if current:
        blocks.append(CVPublicationBlock(title=" ".join(current)))

    return blocks or [CVParagraphBlock(text=" ".join(items))]


# ---------------------------------------------------------------------------
# Education section parser
# ---------------------------------------------------------------------------


def _parse_education_section(items: list[str]) -> list[CVBlockType]:
    cleaned_items = [item.lstrip("•●▪◦ ").strip() for item in items if item.strip()]
    blocks: list[CVEducationBlock] = []
    current_institution: str | None = None
    current_details: list[str] = []

    def flush() -> None:
        nonlocal current_institution, current_details
        if current_institution or current_details:
            blocks.append(
                CVEducationBlock(
                    institution=current_institution,
                    details=current_details,
                ),
            )
        current_institution = None
        current_details = []

    for cleaned in cleaned_items:
        if _is_education_headline(cleaned):
            flush()
            current_institution = cleaned
        else:
            current_details.append(cleaned)

    flush()
    return blocks


# ---------------------------------------------------------------------------
# General section parser (experience, projects, etc.)
# ---------------------------------------------------------------------------


def _parse_general_section(items: list[str], is_summary: bool) -> list[CVBlockType]:
    if is_summary:
        return [CVParagraphBlock(text=" ".join(items))]

    blocks: list[CVBlockType] = []
    current_entry: list[str] = []

    for item in items:
        is_bullet_char = bool(re.match(r"^[•●▪◦]", item))
        cleaned = item.lstrip("•●▪◦ ").strip()
        if not cleaned:
            continue

        if _is_entry_headline(cleaned):
            if current_entry:
                bullets, extra = _split_bullets(current_entry)
                blocks.append(
                    CVEntryBlock(
                        title=" ".join(extra),
                        bullets=[_clean_bullet(b) for b in bullets],
                    ),
                )
            current_entry = [cleaned]
        elif is_bullet_char:
            # This is a bullet — should it belong to the current entry?
            if current_entry:
                current_entry.append(item)
            else:
                blocks.append(CVBulletBlock(text=_clean_bullet(item)))
        # Non-bullet, non-headline: belongs to current entry if we have one
        elif current_entry:
            current_entry.append(cleaned)
        else:
            # Orphan content → paragraph
            blocks.append(CVParagraphBlock(text=cleaned))

    # Flush last entry
    if current_entry:
        bullets, extra = _split_bullets(current_entry)
        blocks.append(
            CVEntryBlock(
                title=" ".join(extra),
                bullets=[_clean_bullet(b) for b in bullets],
            ),
        )

    return blocks if blocks else [CVParagraphBlock(text=" ".join(items))]


def _split_bullets(lines: list[str]) -> tuple[list[str], list[str]]:
    """Separate bullet lines from headline lines in an entry."""
    bullets: list[str] = []
    headline: list[str] = []
    for line in lines:
        is_bullet_char = bool(re.match(r"^[•●▪◦]", line))
        cleaned = line.lstrip("•●▪◦ ").strip()
        if not cleaned:
            continue
        if is_bullet_char:
            bullets.append(line)
        elif _is_entry_headline(cleaned) and headline:
            # Second headline → previous headline was part of title
            headline.append(cleaned)
        elif not headline and not bullets:
            headline.append(cleaned)
        elif bullets:
            bullets.append(cleaned)
        else:
            headline.append(cleaned)
    return bullets, headline


def _clean_bullet(item: str) -> str:
    """Remove leading bullet character."""
    return re.sub(r"^[•●▪◦]\s*", "", item.strip())


# ---------------------------------------------------------------------------
# Experience field parser (from legacy TailoredCV.experience)
# ---------------------------------------------------------------------------


def _experience_to_blocks(experiences: list) -> list[CVBlockType]:
    """Convert legacy TailoredCV.experience list to entry blocks."""
    blocks: list[CVEntryBlock] = []
    for exp in experiences:
        company = getattr(exp, "company", "") or ""
        role = getattr(exp, "role", "") or ""
        bullets = getattr(exp, "bullet_points", []) or []
        title_parts = [p for p in [role, company] if p]
        blocks.append(
            CVEntryBlock(
                title=" — ".join(title_parts),
                bullets=[
                    _clean_bullet(b) if isinstance(b, str) else str(b) for b in bullets
                ],
            ),
        )
    return blocks


def v1_to_v2_safe(cv: TailoredCV | None) -> CVDocumentV2 | None:
    """Safely convert — returns None if *cv* is None or invalid."""
    if cv is None:
        return None
    try:
        return v1_to_v2(cv)
    except Exception:
        logger.warning("V1→V2 adapter failed; returning None", exc_info=True)
        return None
