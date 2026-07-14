"""Source-language policy for CV Analysis."""

import re
import unicodedata
from typing import Literal

from app.models.domain import TailoredCV
from app.models.responses import CVAnalysisLLMResponse

CVLanguage = Literal["vi", "en"]

_VIETNAMESE_DIACRITICS = re.compile(
    r"[ăâđêôơưĂÂĐÊÔƠƯ]|[àáảãạằắẳẵặầấẩẫậèéẻẽẹềếểễệìíỉĩịòóỏõọồốổỗộờớởỡợùúủũụừứửữựỳýỷỹỵ]",
    re.IGNORECASE,
)

_VIETNAMESE_MARKERS = {
    "ban",
    "cac",
    "cho",
    "chuyen",
    "cong",
    "du an",
    "giao duc",
    "he thong",
    "hoc van",
    "khach hang",
    "kinh nghiem",
    "ky nang",
    "ho so",
    "an tuong",
    "lam viec",
    "lap trinh",
    "muc tieu",
    "nhan vien",
    "phat trien",
    "phu hop",
    "phoi hop",
    "quan ly",
    "thanh tich",
    "thuc hien",
    "thieu",
    "tieng viet",
    "tom tat",
    "tot",
    "trach nhiem",
    "toi",
    "ung vien",
    "vien",
    "gioi",
    "va",
    "voi",
    "trong",
    "cua",
    "duoc",
}

_ENGLISH_MARKERS = {
    "achievements",
    "built",
    "backend",
    "collaborated",
    "customers",
    "developed",
    "education",
    "employment",
    "excellent",
    "experience",
    "fit",
    "good",
    "highly",
    "qualified",
    "communicator",
    "candidate",
    "clear",
    "clearer",
    "missing",
    "profile",
    "professional",
    "projects",
    "readable",
    "reliable",
    "responsibilities",
    "skills",
    "services",
    "structure",
    "summary",
    "systems",
    "tech stack",
    "work",
    "additional",
    "clarify",
    "details",
    "relevant",
    "require",
    "review",
    "role",
    "section",
    "strong",
    "the",
    "this",
    "uses",
    "users",
    "with",
    "your",
}

_TECHNICAL_SKILL_TERMS = {
    "and",
    "amazon",
    "api",
    "aws",
    "azure",
    "cloud",
    "c",
    "csharp",
    "docker",
    "dotnet",
    "fastapi",
    "google",
    "kubernetes",
    "learning",
    "machine",
    "nodejs",
    "platform",
    "python",
    "services",
    "sql",
    "web",
}


def _normalized_text(text: str) -> str:
    decomposed = unicodedata.normalize("NFKD", text.lower())
    without_accents = "".join(
        character for character in decomposed if not unicodedata.combining(character)
    )
    return " ".join(re.findall(r"[a-z]+", without_accents))


def _marker_score(text: str, markers: set[str]) -> int:
    padded = f" {text} "
    return sum(
        2 if " " in marker else 1 for marker in markers if f" {marker} " in padded
    )


def _language_scores(text: str) -> tuple[int, int]:
    normalized = _normalized_text(text)
    accent_count = len(_VIETNAMESE_DIACRITICS.findall(text))
    vietnamese_marker_score = _marker_score(normalized, _VIETNAMESE_MARKERS)
    letter_count = max(1, len(re.findall(r"[a-z]", normalized)))
    accent_density = accent_count / letter_count
    accent_bonus = 8 if accent_count >= 2 and accent_density >= 0.04 else 0
    vietnamese_score = vietnamese_marker_score + accent_bonus
    english_score = _marker_score(normalized, _ENGLISH_MARKERS)
    return vietnamese_score, english_score


def detect_cv_language(cv_text: str) -> CVLanguage:
    """Classify a CV's primary language as Vietnamese or English.

    Vietnamese-specific characters are decisive. Marker scoring also supports
    common unaccented Vietnamese CV text produced by PDF extraction.
    """
    lines = [line.strip() for line in cv_text.splitlines() if line.strip()]
    body_lines = lines[1:] if len(lines) > 1 else lines
    body_lines = [
        line
        for line in body_lines
        if not re.search(
            r"@|https?://|www\.|\b(?:ho chi minh|hồ chí minh|viet nam|việt nam|ha noi|hà nội)\b|(?:\+?\d[\d\s().-]{7,}\d)",
            line,
            re.IGNORECASE,
        )
    ]
    body_text = "\n".join(body_lines) or cv_text
    vietnamese_score, english_score = _language_scores(body_text)
    return "vi" if vietnamese_score > english_score else "en"


def _tailored_cv_text(cv: TailoredCV) -> str:
    values = [
        cv.name,
        cv.headline,
        cv.summary,
        cv.education,
        *cv.contact_lines,
        *cv.skills,
        *(section.title for section in cv.sections),
        *(item for section in cv.sections for item in section.items),
        *(experience.company for experience in cv.experience),
        *(experience.role for experience in cv.experience),
        *(
            bullet
            for experience in cv.experience
            for bullet in experience.bullet_points
        ),
    ]
    return "\n".join(value for value in values if value.strip())


def detect_tailored_cv_language(cv: TailoredCV) -> CVLanguage:
    """Detect the primary language of structured Tailored CV content."""
    return detect_cv_language(_tailored_cv_text(cv))


class AnalysisLanguageMismatchError(ValueError):
    """Raised when CV Analysis prose does not use the source CV language."""


def _generated_analysis_fields(response: CVAnalysisLLMResponse) -> list[str]:
    values = [
        response.match_headline,
        response.match_summary,
        *response.cv_strengths,
    ]
    for edit in response.suggested_edits:
        values.extend(
            [
                edit.section,
                edit.improved_safe,
                edit.improved_with_placeholders,
                edit.reason,
                *edit.metric_questions,
                *edit.unsupported_assumptions,
            ]
        )
    for evidence in response.evidence_analysis:
        values.extend([evidence.claim, evidence.comment])
    return [value for value in values if value.strip()]


def _tailored_cv_prose_fields(cv: TailoredCV) -> list[str]:
    """Return generated narrative fields, excluding language-neutral identity data."""
    values = [
        cv.summary,
        *(section.title for section in cv.sections),
        *(
            item
            for section in cv.sections
            if not _is_skills_section(section.title)
            for item in section.items
        ),
        *(
            bullet
            for experience in cv.experience
            for bullet in experience.bullet_points
        ),
    ]
    return [value for value in values if value.strip()]


def _is_skills_section(title: str) -> bool:
    normalized = _normalized_text(title)
    return any(
        marker in normalized
        for marker in ("skills", "ky nang", "technologies", "cong nghe")
    )


def _tailored_cv_skill_fields(cv: TailoredCV) -> list[str]:
    return [
        item
        for section in cv.sections
        if _is_skills_section(section.title)
        for item in section.items
        if item.strip()
    ]


def _is_language_neutral_technical_skill(text: str) -> bool:
    tokens = set(_normalized_text(text).split())
    return bool(tokens) and tokens <= _TECHNICAL_SKILL_TERMS


def _group_conflicts_with_language(
    text: str,
    expected_language: CVLanguage,
    *,
    require_expected_evidence: bool = True,
) -> bool:
    if not text.strip():
        return False
    vietnamese_score, english_score = _language_scores(text)
    if expected_language == "vi":
        if english_score > vietnamese_score:
            return True

        # Vietnamese output should contain Vietnamese evidence in every prose
        # field. This closes the ambiguous-score gap where ordinary English
        # phrases (for example, "Highly qualified") contain no marker from
        # either language. Single-token technical terms are validated as
        # keywords elsewhere and are intentionally language-neutral.
        word_count = len(_normalized_text(text).split())
        return require_expected_evidence and word_count >= 2 and vietnamese_score == 0
    if vietnamese_score > english_score:
        return True
    word_count = len(_normalized_text(text).split())
    return require_expected_evidence and word_count >= 2 and english_score == 0


def ensure_analysis_response_language(
    response: CVAnalysisLLMResponse,
    *,
    expected_language: CVLanguage,
) -> None:
    """Reject a response whose analysis prose is predominantly in another language."""
    generated_fields = _generated_analysis_fields(response)
    tailored_text = _tailored_cv_text(response.tailored_cv)
    tailored_prose_fields = _tailored_cv_prose_fields(response.tailored_cv)
    tailored_skill_fields = _tailored_cv_skill_fields(response.tailored_cv)
    prose_mismatch = any(
        _group_conflicts_with_language(field, expected_language)
        for field in [*generated_fields, *tailored_prose_fields, tailored_text]
    )
    skill_mismatch = any(
        not _is_language_neutral_technical_skill(field)
        and _group_conflicts_with_language(
            field,
            expected_language,
            require_expected_evidence=False,
        )
        for field in tailored_skill_fields
    )
    if prose_mismatch or skill_mismatch:
        expected_name = "Vietnamese" if expected_language == "vi" else "English"
        raise AnalysisLanguageMismatchError(
            f"CV Analysis response must use {expected_name}."
        )
