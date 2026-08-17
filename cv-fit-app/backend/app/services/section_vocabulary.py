"""Canonical section heading vocabulary for CV reconstruction (Phase 4).

Maps heading variants (English + Vietnamese, accented and unaccented) to
canonical ``CVSectionType`` values.  This is the single source of truth that
replaces the three scattered sets in ``layout_extraction.py``,
``cv_quality_checks.py``, and ``cv_v1_adapter.py``.

Every entry is stored in its **NFKD-decomposed, lowercase, accent-stripped**
form so that lookups work regardless of diacritics.  The original (pre-normalized)
form is retained so the detector can report the exact heading text found.
"""

from __future__ import annotations

import re
import unicodedata

# ---------------------------------------------------------------------------
# 1. Canonical section type (mirrors CVSectionType)
# ---------------------------------------------------------------------------

SECTION_TYPE = str  # "summary" | "experience" | "projects" | "skills" | "education" |
# "publications" | "certifications" | "languages" | "awards" |
# "activities" | "interests" | "custom"

SECTION_TYPE_TO_VIETNAMESE: dict[str, str] = {
    "summary": "Tóm tắt chuyên môn",
    "experience": "Kinh nghiệm làm việc",
    "projects": "Dự án tiêu biểu",
    "skills": "Kỹ năng & Chuyên môn",
    "education": "Học vấn",
    "publications": "Công bố khoa học",
    "certifications": "Chứng chỉ & Đào tạo",
    "languages": "Ngoại ngữ",
    "awards": "Giải thưởng & Danh hiệu",
    "activities": "Hoạt động & Lãnh đạo",
    "interests": "Sở thích",
    "custom": "Thông tin bổ sung",
}

SECTION_TYPE_TO_ENGLISH: dict[str, str] = {
    "summary": "Professional Summary",
    "experience": "Work Experience",
    "projects": "Projects",
    "skills": "Skills & Expertise",
    "education": "Education",
    "publications": "Publications",
    "certifications": "Certifications & Training",
    "languages": "Languages",
    "awards": "Honors & Awards",
    "activities": "Activities & Leadership",
    "interests": "Interests",
    "custom": "Additional Information",
}

# ---------------------------------------------------------------------------
# 2. Vocabulary definitions
# ---------------------------------------------------------------------------

# Each value is a list of raw heading strings (any case, any diacritics).
# The lookup infrastructure will normalize them at import time.

_SECTIONS_SUMMARY: list[str] = [
    "professional summary",
    "summary",
    "key skills",
    "core competencies",
    "about me",
    "about",
    "professional profile",
    "profile",
    "career summary",
    "tom tat",
    "gioi thieu",
    "muc tieu",
    "so luoc",
    "tien viet",
    "tieu su",
    "giới thiệu",
    "mục tiêu",
    "tóm tắt",
    "sơ lược",
    "tiên vật",
    "tiểu sử",
]

_SECTIONS_EXPERIENCE: list[str] = [
    "work experience",
    "experience",
    "professional experience",
    "employment history",
    "work history",
    "career history",
    "research experience",
    "software engineering experience",
    "engineering experience",
    "kinh nghiem",
    "kinh nghiem lam viec",
    "kinh nghem",
    "qua trinh lam viec",
    "lich su lam viec",
    "kinh nghiệm",
    "kinh nghiệm làm việc",
    "quá trình làm việc",
    "lịch sử làm việc",
]

_SECTIONS_PROJECTS: list[str] = [
    "projects",
    "personal projects",
    "academic projects",
    "applied ai projects",
    "ai projects",
    "du an",
    "du an ca nhan",
    "cac du an",
    "kinh nghiem du an",
    "dự án",
    "dự án cá nhân",
    "các dự án",
    "kinh nghiệm dự án",
]

_SECTIONS_SKILLS: list[str] = [
    "technical skills",
    "skills",
    "key skills",
    "core competencies",
    "ky nang",
    "ky nang chuyen mon",
    "ky nang mem",
    "cong nghe su dung",
    "cong nghe",
    "kỹ năng",
    "kỹ năng chuyên môn",
    "kỹ năng mềm",
    "công nghệ sử dụng",
    "công nghệ",
]

_SECTIONS_EDUCATION: list[str] = [
    "education",
    "education & certifications",
    "education and certifications",
    "hoc van",
    "hoc van va chung chi",
    "hoc van va chung chi",
    "học vấn",
    "học vấn và chứng chỉ",
]

_SECTIONS_PUBLICATIONS: list[str] = [
    "publications",
    "published papers",
    "scientific publications",
    "cong bo khoa hoc",
    "cong bo",
    "bai bao khoa hoc",
    "công bố khoa học",
    "công bố",
    "bài báo khoa học",
]

_SECTIONS_CERTIFICATIONS: list[str] = [
    "certifications",
    "certificates",
    "certifications & licenses",
    "chung chi",
    "chung chi nghe",
    "chứng chỉ",
    "chứng chỉ nghề",
]

_SECTIONS_LANGUAGES: list[str] = [
    "languages",
    "language proficiency",
    "ngon ngu",
    "ngon ngu giao tiep",
    "ngôn ngữ",
    "ngôn ngữ giao tiếp",
]

_SECTIONS_AWARDS: list[str] = [
    "awards",
    "honours",
    "honors",
    "distinctions",
    "giai thuong",
    "giải thưởng",
]

_SECTIONS_ACTIVITIES: list[str] = [
    "activities",
    "extracurricular activities",
    "volunteering",
    "hoat dong",
    "hoat dong ngoai khia",
    "hoat dong tình nguyen",
    "hoạt động",
    "hoạt động ngoại khóa",
    "hoạt động tình nguyện",
]

_SECTIONS_INTERESTS: list[str] = [
    "interests",
    "personal interests",
    "di chan",
    "sở thích",
]

_SECTIONS_STRENGTHS: list[str] = [
    "strengths",
    "key strengths",
    "core strengths",
    "my strengths",
    "diem manh",
    "điểm mạnh",
    "uu diem",
    "ưu điểm",
]

_SECTIONS_MOST_PROUD_OF: list[str] = [
    "most proud of",
    "proudest achievements",
    "key achievements",
    "major achievements",
    "achievements",
    "tu hao nhat",
    "tự hào nhất",
    "thanh tuu",
    "thành tựu",
]

_SECTIONS_OTHER: list[str] = [
    "contact",
    "lien he",
    "thông tin",
    "thong tin",
    "lien he",
    "contact information",
    "liên hệ",
    "thông tin",
    "thòng tin",
]

# ---------------------------------------------------------------------------
# 3. Lookup tables (built at import time)
# ---------------------------------------------------------------------------


def _normalize(text: str) -> str:
    """NFKD-decompose, lowercase, strip accents, collapse whitespace, strip leading numbers/bullets & trailing colons/punctuation."""
    cleaned_str = text.strip()
    # Strip leading numbers/bullets like "1.", "1)", "I.", "#", "-", "•", "▪", "◦"
    cleaned_str = re.sub(r"^[0-9IVXLCDMivxlcdm]+[\.\)]\s*", "", cleaned_str)
    cleaned_str = re.sub(r"^[\#\-\*•▪◦]\s*", "", cleaned_str)
    # Strip trailing colons, dashes, equals signs
    cleaned_str = re.sub(r"[\:\-\=]+$", "", cleaned_str).strip()

    decomposed = unicodedata.normalize("NFKD", cleaned_str.lower())
    cleaned = "".join(c for c in decomposed if not unicodedata.combining(c))
    return " ".join(cleaned.split())


# MAPPING: normalized variant → (canonical_type, original_display)
_VOCABULARY: dict[str, tuple[SECTION_TYPE, str]] = {}

_SECTION_GROUPS: list[tuple[SECTION_TYPE, list[str]]] = [
    ("summary", _SECTIONS_SUMMARY),
    ("experience", _SECTIONS_EXPERIENCE),
    ("projects", _SECTIONS_PROJECTS),
    ("skills", _SECTIONS_SKILLS),
    ("education", _SECTIONS_EDUCATION),
    ("publications", _SECTIONS_PUBLICATIONS),
    ("certifications", _SECTIONS_CERTIFICATIONS),
    ("languages", _SECTIONS_LANGUAGES),
    ("awards", _SECTIONS_AWARDS),
    ("activities", _SECTIONS_ACTIVITIES),
    ("interests", _SECTIONS_INTERESTS),
    ("custom", _SECTIONS_STRENGTHS),
    ("custom", _SECTIONS_MOST_PROUD_OF),
    ("other", _SECTIONS_OTHER),  # "other" → "custom" at classification time
]

for canonical, variants in _SECTION_GROUPS:
    for variant in variants:
        norm = _normalize(variant)
        if norm:
            _VOCABULARY[norm] = (canonical, variant)

# All recognized canonical types (excluding "other")
RECOGNIZED_TYPES: set[SECTION_TYPE] = {
    t for t, _ in _VOCABULARY.values() if t != "other"
}

# ---------------------------------------------------------------------------
# 4. Public API
# ---------------------------------------------------------------------------


def classify_heading(text: str) -> tuple[SECTION_TYPE, str] | None:
    """Classify a heading text into a canonical section type.

    Returns ``(canonical_type, display_text)`` or ``None`` if the heading
    does not match any known vocabulary entry.

    The lookup uses NFKD decomposition + accent stripping so that
    "KỸ NĂNG", "Ky nang", "ky năng", etc. all match. Also handles multi-column
    concatenated headers (e.g. "EDUCATION EXPERIENCE", "SKILLS ACTIVITIES").
    """
    norm = _normalize(text)
    if not norm:
        return None
    entry = _VOCABULARY.get(norm)
    if entry is not None:
        canonical, original = entry
        if canonical == "other":
            return ("custom", original)
        return (canonical, original)

    # Fallback for concatenated multi-column headers (e.g., "EDUCATION EXPERIENCE", "SKILLS ACTIVITIES")
    words = norm.split()
    if 2 <= len(words) <= 4:
        for word in words:
            word_entry = _VOCABULARY.get(word)
            if word_entry is not None:
                canonical, original = word_entry
                if canonical != "other":
                    return (canonical, text.strip())

    return None


def is_known_section_type(section_type: str) -> bool:
    """Check if a canonical section type is one we recognize."""
    return section_type in RECOGNIZED_TYPES or section_type == "custom"


# ---------------------------------------------------------------------------
# 5. Quick self-test
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    tests = [
        ("WORK EXPERIENCE", "experience"),
        ("KINH NGHIỆM LÀM VIỆC", "experience"),
        ("PROJECTS", "projects"),
        ("DỰ ÁN", "projects"),
        ("TECHNICAL SKILLS", "skills"),
        ("KỸ NĂNG", "skills"),
        ("CÔNG BỐ KHOA HỌC", "publications"),
        ("HỌC VẤN", "education"),
        ("CHỨNG CHỈ", "certifications"),
        ("NGÔN NGỮ", "languages"),
        ("GIẢI THƯỞNG", "awards"),
        ("HOẠT ĐỘNG", "activities"),
        ("SỞ THÍCH", "interests"),
        ("CUSTOM THING", None),
    ]
    for text, expected in tests:
        result = classify_heading(text)
        got = result[0] if result else None
        status = "✓" if got == expected else "✗"
        print(f"  {status} {text!r:30s} → {got!r:15s} (expected {expected!r})")
