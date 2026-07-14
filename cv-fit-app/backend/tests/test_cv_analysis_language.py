import asyncio
from types import SimpleNamespace

import pytest

from app.models.domain import (
    EvidenceAnalysis,
    PrioritizedKeyword,
    SuggestedEdit,
    TailoredCV,
    TailoredCVSection,
)
from app.models.responses import CVAnalysisLLMResponse
from app.prompts.system_prompts import build_cv_analysis_prompt
from app.services import ai_service, cv_analysis_service
from app.services.cv_language import (
    AnalysisLanguageMismatchError,
    detect_cv_language,
    detect_tailored_cv_language,
    ensure_analysis_response_language,
)
from app.services.cv_quality_checks import build_scored_analysis
from app.services.tailored_cv_pdf import render_tailored_cv_html


def _analysis_response(*, summary: str) -> CVAnalysisLLMResponse:
    edit = SuggestedEdit(
        section="Experience",
        original_text="Built backend services.",
        improved_safe="Built reliable backend services.",
        improved_with_placeholders="Built backend services for [N users].",
        metric_questions=["How many users did the services support?"],
        unsupported_assumptions=[],
        rewrite_risk="safe",
        reason="Uses clearer wording.",
    )
    return CVAnalysisLLMResponse(
        match_headline="Strong fit",
        match_summary=summary,
        technical_match=80,
        experience_relevance=80,
        keyword_coverage=80,
        impact_evidence=70,
        tone_quality=80,
        ats_readiness=80,
        missing_keywords=["Kubernetes"],
        suggested_edits=[edit, edit.model_copy()],
        cv_strengths=["Clear experience", "Readable structure"],
        prioritized_keywords=[
            PrioritizedKeyword(keyword="Kubernetes", priority="High")
        ],
        evidence_analysis=[
            EvidenceAnalysis(
                claim="Backend delivery",
                evidence_strength="Medium",
                comment="Relevant experience is present but lightly quantified.",
            )
        ],
        tailored_cv=TailoredCV(name="Duy"),
    )


def _vietnamese_analysis_response() -> CVAnalysisLLMResponse:
    response = _analysis_response(
        summary="Hồ sơ phù hợp nhưng vẫn còn một vài khoảng trống quan trọng."
    )
    edits = [
        edit.model_copy(
            update={
                "section": "Kinh nghiệm",
                "original_text": "Phát triển dịch vụ backend.",
                "improved_safe": "Phát triển các dịch vụ backend ổn định.",
                "improved_with_placeholders": (
                    "Phát triển dịch vụ backend cho [N người dùng]."
                ),
                "metric_questions": ["Dịch vụ hỗ trợ bao nhiêu người dùng?"],
                "reason": "Cách diễn đạt rõ ràng hơn.",
            }
        )
        for edit in response.suggested_edits
    ]
    return response.model_copy(
        update={
            "match_headline": "Mức độ phù hợp tốt",
            "suggested_edits": edits,
            "cv_strengths": ["Kinh nghiệm rõ ràng", "Cấu trúc dễ đọc"],
            "evidence_analysis": [
                EvidenceAnalysis(
                    claim="Khả năng phát triển backend",
                    evidence_strength="Medium",
                    comment="Kinh nghiệm phù hợp nhưng còn thiếu số liệu cụ thể.",
                )
            ],
        }
    )


def test_scored_analysis_keeps_deterministic_copy_in_english() -> None:
    result = build_scored_analysis(
        _analysis_response(summary="The profile is relevant but has a few gaps."),
        source_language="en",
    )

    assert result.match_headline == (
        "Good fit — the CV has a strong foundation but still needs optimization."
    )
    assert result.match_summary.startswith("CV Match: 70%.")
    assert "Deducted 8 points" in result.match_summary
    assert "The profile is relevant but has a few gaps." in result.match_summary


def test_source_language_detection_handles_vietnamese_english_and_unaccented_cv() -> (
    None
):
    assert (
        detect_cv_language(
            "KINH NGHIỆM LÀM VIỆC\nPhát triển hệ thống và phối hợp với khách hàng."
        )
        == "vi"
    )


def test_english_cv_with_vietnamese_identity_is_classified_by_body_language() -> None:
    cv_text = """NGUYỄN THỊ HỒNG HẠNH
Hồ Chí Minh, Việt Nam
PROFESSIONAL SUMMARY
Software engineer.
WORK EXPERIENCE
Built APIs.
EDUCATION
Computer Science
SKILLS
Python, FastAPI
"""

    assert detect_cv_language(cv_text) == "en"


def test_vietnamese_prose_does_not_require_a_known_heading_marker() -> None:
    cv_text = "TÓM TẮT\nLập trình viên có năm năm làm sản phẩm số."

    assert detect_cv_language(cv_text) == "vi"
    assert (
        detect_cv_language(
            "WORK EXPERIENCE\nDeveloped backend systems and collaborated with customers."
        )
        == "en"
    )
    assert (
        detect_cv_language(
            "KINH NGHIEM LAM VIEC\nPhat trien he thong va phoi hop voi khach hang."
        )
        == "vi"
    )


def test_analysis_prompt_names_the_detected_source_language_explicitly() -> None:
    prompt = build_cv_analysis_prompt("Analyze this CV.", source_language="en")

    assert "DETECTED SOURCE CV LANGUAGE: ENGLISH" in prompt
    assert "Every user-facing text field must be written in English" in prompt


def test_analysis_response_in_wrong_language_is_rejected() -> None:
    response = _analysis_response(
        summary="The profile is relevant but still has a few important gaps."
    )

    with pytest.raises(AnalysisLanguageMismatchError):
        ensure_analysis_response_language(response, expected_language="vi")

    ensure_analysis_response_language(response, expected_language="en")


@pytest.mark.parametrize(
    "wrong_value",
    [
        "Strong fit",
        "Good fit",
        "Missing",
        "Excellent candidate",
        "Outstanding applicant",
        "Highly qualified",
        "Proven communicator",
        "Clear impact",
    ],
)
def test_short_english_analysis_fields_are_rejected_for_vietnamese_cv(
    wrong_value: str,
) -> None:
    response = _vietnamese_analysis_response().model_copy(
        update={"match_headline": wrong_value}
    )

    with pytest.raises(AnalysisLanguageMismatchError):
        ensure_analysis_response_language(response, expected_language="vi")


def test_unrecognized_english_prose_is_rejected_in_each_analysis_field() -> None:
    response = _vietnamese_analysis_response().model_copy(
        update={
            "cv_strengths": ["Outstanding applicant"],
            "evidence_analysis": [
                EvidenceAnalysis(
                    claim="Clear impact",
                    evidence_strength="Medium",
                    comment="Proven communicator.",
                )
            ],
        }
    )

    with pytest.raises(AnalysisLanguageMismatchError):
        ensure_analysis_response_language(response, expected_language="vi")


def test_language_neutral_keywords_remain_valid_for_vietnamese_analysis() -> None:
    response = _vietnamese_analysis_response().model_copy(
        update={
            "missing_keywords": ["Amazon Web Services"],
            "prioritized_keywords": [
                PrioritizedKeyword(keyword="Google Cloud Platform", priority="High")
            ],
        }
    )

    ensure_analysis_response_language(response, expected_language="vi")


def test_short_vietnamese_analysis_field_is_rejected_for_english_cv() -> None:
    response = _analysis_response(
        summary="The profile is relevant but still has a few important gaps."
    ).model_copy(update={"match_headline": "Phù hợp tốt"})

    with pytest.raises(AnalysisLanguageMismatchError):
        ensure_analysis_response_language(response, expected_language="en")


@pytest.mark.parametrize("wrong_value", ["Ung vien gioi", "Ho so an tuong"])
def test_unaccented_vietnamese_prose_is_rejected_for_english_cv(
    wrong_value: str,
) -> None:
    response = _analysis_response(
        summary="The profile is relevant but still has a few important gaps."
    ).model_copy(update={"match_headline": wrong_value})

    with pytest.raises(AnalysisLanguageMismatchError):
        ensure_analysis_response_language(response, expected_language="en")


def test_tailored_cv_candidate_in_wrong_language_is_rejected_independently() -> None:
    response = _vietnamese_analysis_response().model_copy(
        update={
            "tailored_cv": TailoredCV(
                name="Nguyễn Văn An",
                headline="Backend Engineer",
                summary="Experienced engineer building reliable customer systems.",
                sections=[
                    TailoredCVSection(
                        title="Work Experience",
                        items=["Developed backend services for customer workflows."],
                    )
                ],
            )
        }
    )

    with pytest.raises(AnalysisLanguageMismatchError):
        ensure_analysis_response_language(response, expected_language="vi")


def test_tailored_cv_skill_items_are_language_neutral() -> None:
    response = _vietnamese_analysis_response().model_copy(
        update={
            "tailored_cv": TailoredCV(
                name="Nguyễn Văn An",
                summary="Phát triển hệ thống ổn định cho khách hàng.",
                sections=[
                    TailoredCVSection(
                        title="Kỹ năng",
                        items=[
                            "Amazon Web Services",
                            "Google Cloud Platform",
                            "Machine Learning",
                        ],
                    )
                ],
            )
        }
    )

    ensure_analysis_response_language(response, expected_language="vi")


@pytest.mark.parametrize(
    "wrong_skill",
    [
        "Highly qualified communicator",
        "This candidate is highly qualified",
        "This candidate has strong cloud experience",
    ],
)
def test_tailored_cv_skills_section_rejects_wrong_language_narrative(
    wrong_skill: str,
) -> None:
    response = _vietnamese_analysis_response().model_copy(
        update={
            "tailored_cv": TailoredCV(
                name="Nguyễn Văn An",
                summary="Phát triển hệ thống ổn định cho khách hàng.",
                sections=[TailoredCVSection(title="Kỹ năng", items=[wrong_skill])],
            )
        }
    )

    with pytest.raises(AnalysisLanguageMismatchError):
        ensure_analysis_response_language(response, expected_language="vi")


def test_english_schema_fallbacks_cannot_hide_inside_vietnamese_analysis() -> None:
    payload = _vietnamese_analysis_response().model_dump()
    payload["suggested_edits"] = payload["suggested_edits"][:1]
    payload["cv_strengths"] = payload["cv_strengths"][:1]
    response = CVAnalysisLLMResponse(**payload)

    with pytest.raises(AnalysisLanguageMismatchError):
        ensure_analysis_response_language(response, expected_language="vi")


def test_unaccented_vietnamese_tailored_cv_keeps_vietnamese_renderer_labels() -> None:
    cv = TailoredCV(
        name="Nguyen Van An",
        summary="Phat trien he thong va phoi hop voi khach hang.",
        sections=[
            TailoredCVSection(
                title="KINH NGHIEM LAM VIEC",
                items=["Phat trien dich vu backend on dinh."],
            )
        ],
    )

    assert detect_tailored_cv_language(cv) == "vi"
    assert "Tóm tắt" in render_tailored_cv_html(cv, "classic_ats")


def test_llm_call_retries_when_response_language_validation_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class Provider:
        name = "test"
        model = "test-model"

        def __init__(self) -> None:
            self.calls = 0

        async def generate_structured(self, **_: object) -> SimpleNamespace:
            self.calls += 1
            data = "wrong language" if self.calls == 1 else "correct language"
            return SimpleNamespace(data=data, input_tokens=1, output_tokens=1)

    provider = Provider()
    monkeypatch.setattr(ai_service.config, "PROVIDERS", [provider])
    monkeypatch.setattr(ai_service.asyncio, "sleep", _no_sleep)

    def validate(value: str) -> None:
        if value != "correct language":
            raise AnalysisLanguageMismatchError("wrong language")

    result = asyncio.run(
        ai_service.call_llm_with_fallback(
            "Return JSON.",
            "input",
            str,
            max_retries=2,
            result_validator=validate,
        )
    )

    assert result == "correct language"
    assert provider.calls == 2


async def _no_sleep(_: float) -> None:
    return None


def test_analyze_cv_uses_source_language_for_prompt_validation_and_scoring(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, object] = {}

    async def fake_llm(
        system_prompt: str,
        _: str,
        __: type,
        **kwargs: object,
    ) -> CVAnalysisLLMResponse:
        captured["prompt"] = system_prompt
        captured.update(kwargs)
        response = _analysis_response(
            summary="The profile is relevant but still has a few important gaps."
        )
        validator = kwargs["result_validator"]
        assert callable(validator)
        validator(response)
        return response

    monkeypatch.setattr(cv_analysis_service, "call_llm_with_fallback", fake_llm)

    response = asyncio.run(
        cv_analysis_service.analyze_cv(
            cv_text=(
                "Nguyễn Duy\nWORK EXPERIENCE\n"
                "Developed backend systems and collaborated with customers."
            ),
            jd_text="Backend Engineer",
        )
    )

    assert "DETECTED SOURCE CV LANGUAGE: ENGLISH" in captured["prompt"]
    assert captured["max_retries"] == 2
    assert response.match_headline.startswith("Good fit")
    assert response.source_language == "en"


def test_analyze_cv_keeps_vietnamese_source_analysis_in_vietnamese(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, object] = {}

    async def fake_llm(
        system_prompt: str,
        _: str,
        __: type,
        **kwargs: object,
    ) -> CVAnalysisLLMResponse:
        captured["prompt"] = system_prompt
        response = _vietnamese_analysis_response()
        validator = kwargs["result_validator"]
        assert callable(validator)
        validator(response)
        return response

    monkeypatch.setattr(cv_analysis_service, "call_llm_with_fallback", fake_llm)

    response = asyncio.run(
        cv_analysis_service.analyze_cv(
            cv_text=(
                "NGUYỄN VĂN AN\nKINH NGHIỆM LÀM VIỆC\n"
                "Phát triển hệ thống backend và phối hợp với khách hàng."
            ),
            jd_text="Kỹ sư Backend",
        )
    )

    assert "NGÔN NGỮ CV NGUỒN ĐÃ XÁC ĐỊNH: TIẾNG VIỆT" in captured["prompt"]
    assert response.match_headline.startswith("Phù hợp tốt")
    assert "Bị trừ 8 điểm" in response.match_summary
