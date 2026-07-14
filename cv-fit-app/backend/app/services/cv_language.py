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
    "lam viec",
    "muc tieu",
    "nhan vien",
    "phat trien",
    "phoi hop",
    "quan ly",
    "thanh tich",
    "thuc hien",
    "tieng viet",
    "trach nhiem",
    "toi",
    "va",
    "voi",
    "trong",
    "cua",
    "duoc",
}

_ENGLISH_MARKERS = {
    "achievements",
    "built",
    "collaborated",
    "customers",
    "developed",
    "education",
    "employment",
    "experience",
    "profile",
    "professional",
    "projects",
    "responsibilities",
    "skills",
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
    "with",
    "your",
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
    accent_bonus = min(accent_count, 4) if vietnamese_marker_score else 0
    vietnamese_score = vietnamese_marker_score + accent_bonus
    english_score = _marker_score(normalized, _ENGLISH_MARKERS)
    return vietnamese_score, english_score


def detect_cv_language(cv_text: str) -> CVLanguage:
    """Classify a CV's primary language as Vietnamese or English.

    Vietnamese-specific characters are decisive. Marker scoring also supports
    common unaccented Vietnamese CV text produced by PDF extraction.
    """
    vietnamese_score, english_score = _language_scores(cv_text)
    return "vi" if vietnamese_score > english_score else "en"


def detect_tailored_cv_language(cv: TailoredCV) -> CVLanguage:
    """Detect the primary language of structured Tailored CV content."""
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
    return detect_cv_language("\n".join(value for value in values if value.strip()))


class AnalysisLanguageMismatchError(ValueError):
    """Raised when CV Analysis prose does not use the source CV language."""


def _generated_analysis_fields(response: CVAnalysisLLMResponse) -> list[str]:
    values = [
        response.match_headline,
        response.match_summary,
        *response.cv_strengths,
        *response.missing_keywords,
        *(item.keyword for item in response.prioritized_keywords),
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
    values.extend(
        [
            response.tailored_cv.headline,
            response.tailored_cv.summary,
            *(section.title for section in response.tailored_cv.sections),
            *(
                item
                for section in response.tailored_cv.sections
                for item in section.items
            ),
        ]
    )
    return [value for value in values if value.strip()]


def _group_conflicts_with_language(text: str, expected_language: CVLanguage) -> bool:
    if not text.strip():
        return False
    vietnamese_score, english_score = _language_scores(text)
    if expected_language == "vi":
        return english_score >= vietnamese_score + 2
    return vietnamese_score >= english_score + 2


def ensure_analysis_response_language(
    response: CVAnalysisLLMResponse,
    *,
    expected_language: CVLanguage,
) -> None:
    """Reject a response whose analysis prose is predominantly in another language."""
    if any(
        _group_conflicts_with_language(field, expected_language)
        for field in _generated_analysis_fields(response)
    ):
        expected_name = "Vietnamese" if expected_language == "vi" else "English"
        raise AnalysisLanguageMismatchError(
            f"CV Analysis response must use {expected_name}."
        )
