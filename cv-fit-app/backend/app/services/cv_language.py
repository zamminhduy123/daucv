"""Source-language policy for CV Analysis."""

import re
import unicodedata
from typing import Literal

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
}

_ENGLISH_MARKERS = {
    "achievements",
    "built",
    "collaborated",
    "customers",
    "developed",
    "education",
    "experience",
    "professional",
    "projects",
    "responsibilities",
    "skills",
    "summary",
    "systems",
    "work",
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
    vietnamese_score = _marker_score(normalized, _VIETNAMESE_MARKERS) + min(
        accent_count, 4
    )
    english_score = _marker_score(normalized, _ENGLISH_MARKERS)
    return vietnamese_score, english_score


def detect_cv_language(cv_text: str) -> CVLanguage:
    """Classify a CV's primary language as Vietnamese or English.

    Vietnamese-specific characters are decisive. Marker scoring also supports
    common unaccented Vietnamese CV text produced by PDF extraction.
    """
    vietnamese_score, english_score = _language_scores(cv_text)
    return "vi" if vietnamese_score > english_score else "en"


class AnalysisLanguageMismatchError(ValueError):
    """Raised when CV Analysis prose does not use the source CV language."""


def _joined(values: list[str]) -> str:
    return "\n".join(value for value in values if value.strip())


def _analysis_language_groups(response: CVAnalysisLLMResponse) -> list[str]:
    core = _joined(
        [response.match_headline, response.match_summary, *response.cv_strengths]
    )
    keywords = _joined(
        [
            *response.missing_keywords,
            *(item.keyword for item in response.prioritized_keywords),
        ]
    )
    edit_values: list[str] = []
    for edit in response.suggested_edits:
        edit_values.extend(
            [
                edit.section,
                edit.improved_safe,
                edit.improved_with_placeholders,
                edit.reason,
                *edit.metric_questions,
                *edit.unsupported_assumptions,
            ]
        )
    evidence_values: list[str] = []
    for evidence in response.evidence_analysis:
        evidence_values.extend([evidence.claim, evidence.comment])

    tailored_values = [
        response.tailored_cv.headline,
        response.tailored_cv.summary,
        *(section.title for section in response.tailored_cv.sections),
        *(item for section in response.tailored_cv.sections for item in section.items),
    ]
    return [
        core,
        keywords,
        _joined(edit_values),
        _joined(evidence_values),
        _joined(tailored_values),
    ]


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
        _group_conflicts_with_language(group, expected_language)
        for group in _analysis_language_groups(response)
    ):
        expected_name = "Vietnamese" if expected_language == "vi" else "English"
        raise AnalysisLanguageMismatchError(
            f"CV Analysis response must use {expected_name}."
        )
