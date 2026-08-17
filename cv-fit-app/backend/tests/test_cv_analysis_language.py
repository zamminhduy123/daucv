import asyncio
from hashlib import sha256
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from fastapi import HTTPException
from pydantic import ValidationError

from app.models.cv_document_v2 import (
    CVDocumentV2,
    CVParagraphBlock,
    CVReconstructionDiagnostics,
    CVRewriteDecision,
    CVRewriteOperation,
    CVSection,
    CVSourceCoverageDiagnostics,
    CVTailoringDiagnostics,
    CVUnmappedContent,
    LLMUnmappedReference,
)
from app.models.cv_raw_extraction import (
    ExtractionMethod,
    RawBlock,
    RawExtraction,
    RawPage,
)
from app.models.cv_structuring import LLMSemanticCVResponse
from app.models.domain import (
    EvidenceAnalysis,
    PrioritizedKeyword,
    SuggestedEdit,
    TailoredCV,
    TailoredCVSection,
)
from app.models.requests import LayoutLine
from app.models.responses import CVAnalysisLLMResponse
from app.prompts.system_prompts import build_cv_analysis_prompt
from app.services import (
    ai_service,
    cv_analysis_service,
    cv_provenance_service,
    cv_source_grounding,
    cv_structuring_service,
)
from app.services.cv_language import (
    AnalysisLanguageMismatchError,
    detect_cv_language,
    detect_tailored_cv_language,
    ensure_analysis_response_language,
)
from app.services.cv_quality_checks import build_scored_analysis
from app.services.cv_reconstruction_service import (
    InvalidSourceReferenceError,
    finalize_document_provenance,
    validate_reconstruction_gate,
)
from app.services.cv_rewrite_service import (
    CVRewriteEvidenceBundle,
    CVRewriteOperationsPayload,
    build_evidence_bundle,
    rewrite_cv,
    verify_and_rebind_user_edit,
)
from app.services.cv_structuring_service import (
    CVStructuringResult,
    SemanticGroundingError,
)
from app.services.cv_tailoring_service import (
    CVRewriteSemanticVerdict,
    hash_field_value,
    validate_block_rewrite_deterministic,
    validate_tailored_document_gate,
    verify_block_rewrite_semantics,
    verify_block_rewrite_semantics_with_validator,
)
from app.services.tailored_cv_metadata import (
    canonical_source_document_hash,
    issue_tailoring_entitlement_v3,
    verify_tailoring_entitlement_v3,
)
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
            PrioritizedKeyword(keyword="Kubernetes", priority="High"),
        ],
        evidence_analysis=[
            EvidenceAnalysis(
                claim="Backend delivery",
                evidence_strength="Medium",
                comment="Relevant experience is present but lightly quantified.",
            ),
        ],
        tailored_cv=TailoredCV(name="Duy"),
    )


def _vietnamese_analysis_response() -> CVAnalysisLLMResponse:
    response = _analysis_response(
        summary="Hồ sơ phù hợp nhưng vẫn còn một vài khoảng trống quan trọng.",
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
            },
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
                ),
            ],
        },
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
            "KINH NGHIỆM LÀM VIỆC\nPhát triển hệ thống và phối hợp với khách hàng.",
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
            "WORK EXPERIENCE\nDeveloped backend systems and collaborated with customers.",
        )
        == "en"
    )
    assert (
        detect_cv_language(
            "KINH NGHIEM LAM VIEC\nPhat trien he thong va phoi hop voi khach hang.",
        )
        == "vi"
    )


def test_analysis_prompt_names_the_detected_source_language_explicitly() -> None:
    prompt = build_cv_analysis_prompt("Analyze this CV.", source_language="en")

    assert "DETECTED SOURCE CV LANGUAGE: ENGLISH" in prompt
    assert "Every user-facing text field must be written in English" in prompt


def test_analysis_response_in_wrong_language_is_rejected() -> None:
    response = _analysis_response(
        summary="The profile is relevant but still has a few important gaps.",
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
        update={"match_headline": wrong_value},
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
                ),
            ],
        },
    )

    with pytest.raises(AnalysisLanguageMismatchError):
        ensure_analysis_response_language(response, expected_language="vi")


def test_language_neutral_keywords_remain_valid_for_vietnamese_analysis() -> None:
    response = _vietnamese_analysis_response().model_copy(
        update={
            "missing_keywords": ["Amazon Web Services"],
            "prioritized_keywords": [
                PrioritizedKeyword(keyword="Google Cloud Platform", priority="High"),
            ],
        },
    )

    ensure_analysis_response_language(
        response,
        expected_language="vi",
        source_reference_text="Amazon Web Services, Google Cloud Platform",
    )


@pytest.mark.parametrize(
    "wrong_keyword",
    [
        "You need stronger leadership evidence",
        "This candidate needs stronger communication",
    ],
)
def test_keyword_lists_reject_wrong_language_narrative(
    wrong_keyword: str,
) -> None:
    response = _vietnamese_analysis_response().model_copy(
        update={
            "missing_keywords": [wrong_keyword],
            "prioritized_keywords": [
                PrioritizedKeyword(keyword=wrong_keyword, priority="High"),
            ],
        },
    )

    with pytest.raises(AnalysisLanguageMismatchError):
        ensure_analysis_response_language(response, expected_language="vi")


def test_short_vietnamese_analysis_field_is_rejected_for_english_cv() -> None:
    response = _analysis_response(
        summary="The profile is relevant but still has a few important gaps.",
    ).model_copy(update={"match_headline": "Phù hợp tốt"})

    with pytest.raises(AnalysisLanguageMismatchError):
        ensure_analysis_response_language(response, expected_language="en")


@pytest.mark.parametrize("wrong_value", ["Ung vien gioi", "Ho so an tuong"])
def test_unaccented_vietnamese_prose_is_rejected_for_english_cv(
    wrong_value: str,
) -> None:
    response = _analysis_response(
        summary="The profile is relevant but still has a few important gaps.",
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
                    ),
                ],
            ),
        },
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
                            "Project Management",
                            "React Native",
                            "Natural Language Processing",
                            "Data Analysis",
                            "Microsoft Office",
                            "UI UX Design",
                        ],
                    ),
                ],
            ),
        },
    )

    ensure_analysis_response_language(
        response,
        expected_language="vi",
        source_cv_text=(
            "Amazon Web Services, Google Cloud Platform, Machine Learning, "
            "Project Management, React Native, Natural Language Processing, "
            "Data Analysis, Microsoft Office, UI UX Design"
        ),
    )


@pytest.mark.parametrize(
    "wrong_skill",
    [
        "Highly qualified communicator",
        "This candidate is highly qualified",
        "This candidate has strong cloud experience",
        "Outstanding applicant",
        "Proven leader",
        "Exceptional Strategic Thinker",
        "Creative Problem Solver",
        "Results Driven Innovator",
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
            ),
        },
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
            ),
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
        ),
    )

    assert result == "correct language"
    assert provider.calls == 2


async def _no_sleep(_: float) -> None:
    return None


def _structured_source(text: str) -> CVStructuringResult:
    raw = cv_structuring_service.build_manual_text_extraction(text)
    document = CVDocumentV2(
        parser_version="llm-semantic-1.0",
        sections=[
            CVSection(
                id="semantic-section-1",
                type="experience",
                title="Experience",
                blocks=[],
            )
        ],
        reconstruction_diagnostics=CVReconstructionDiagnostics(
            source_coverage=CVSourceCoverageDiagnostics(
                raw_block_count=len(raw.pages[0].blocks),
                accounted_block_count=len(raw.pages[0].blocks),
                significant_character_count=len(text),
                mapped_character_count=len(text),
                coverage_ratio=1.0,
            )
        ),
    )
    return CVStructuringResult(raw, text, document, False)


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
            summary="The profile is relevant but still has a few important gaps.",
        )
        validator = kwargs["result_validator"]
        assert callable(validator)
        validator(response)
        return response

    monkeypatch.setattr(cv_analysis_service, "call_llm_with_fallback", fake_llm)

    async def fake_structure(**kwargs: object) -> CVStructuringResult:
        return _structured_source(str(kwargs["cv_text"]))

    monkeypatch.setattr(cv_analysis_service, "structure_cv", fake_structure)

    response = asyncio.run(
        cv_analysis_service.analyze_cv(
            cv_text=(
                "Nguyễn Duy\nWORK EXPERIENCE\n"
                "Developed backend systems and collaborated with customers."
            ),
            jd_text="Backend Engineer",
        ),
    )

    assert "DETECTED SOURCE CV LANGUAGE: ENGLISH" in captured["prompt"]
    assert captured["max_retries"] == 1
    assert response.match_headline.startswith("Good fit")
    assert response.source_language == "en"
    assert response.document_v2 is not None
    assert response.source_document_v2 is not None
    assert response.reconstruction_diagnostics is not None


def test_analyze_cv_does_not_treat_client_layout_lines_as_authoritative(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, object] = {}

    async def fake_llm(*_: object, **__: object) -> CVAnalysisLLMResponse:
        return _analysis_response(
            summary="The profile is relevant but still has a few important gaps.",
        )

    async def fake_structure(**kwargs: object) -> CVStructuringResult:
        captured["structure_kwargs"] = kwargs
        return _structured_source(str(kwargs["cv_text"]))

    monkeypatch.setattr(cv_analysis_service, "call_llm_with_fallback", fake_llm)
    monkeypatch.setattr(cv_analysis_service, "structure_cv", fake_structure)

    response = asyncio.run(
        cv_analysis_service.analyze_cv(
            cv_text="NGUYEN VAN DUY\nBackend Developer",
            jd_text="Backend Engineer",
            layout_data=[
                LayoutLine(
                    text="NGUYEN VAN DUY",
                    page=1,
                    x=72,
                    y=88,
                    width=180,
                    height=14,
                    font_size=16,
                    font_weight=700,
                    normalized_text="NGUYEN VAN DUY",
                    column_id="main",
                    joined_to_prev=False,
                    is_page_break_marker=True,
                    is_layout_artifact=False,
                    page_height=842,
                    source_line_id="p2-l1",
                ),
            ],
        ),
    )

    structure_kwargs = captured["structure_kwargs"]
    assert isinstance(structure_kwargs, dict)
    assert "layout_data" not in structure_kwargs
    assert response.document_v2 is not None


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

    async def fake_structure(**kwargs: object) -> CVStructuringResult:
        return _structured_source(str(kwargs["cv_text"]))

    monkeypatch.setattr(cv_analysis_service, "structure_cv", fake_structure)

    response = asyncio.run(
        cv_analysis_service.analyze_cv(
            cv_text=(
                "NGUYỄN VĂN AN\nKINH NGHIỆM LÀM VIỆC\n"
                "Phát triển hệ thống backend và phối hợp với khách hàng."
            ),
            jd_text="Kỹ sư Backend",
        ),
    )

    assert "NGÔN NGỮ CV NGUỒN ĐÃ XÁC ĐỊNH: TIẾNG VIỆT" in captured["prompt"]
    assert response.match_headline.startswith("Phù hợp tốt")
    assert "Bị trừ 8 điểm" in response.match_summary


def _semantic_response_for(raw: RawExtraction) -> LLMSemanticCVResponse:
    ids = [block.block_id for page in raw.pages for block in page.blocks]
    return LLMSemanticCVResponse.model_validate(
        {
            "identity": {
                "full_name": "NGUYỄN MINH AN",
                "email": "an@example.test",
                "confidence": 0.99,
                "field_source_block_ids": {
                    "full_name": [ids[0]],
                    "email": [ids[1]],
                },
            },
            "summary": {
                "text": "Giữ nguyên câu chữ của ứng viên.",
                "confidence": 0.95,
                "source_block_ids": [ids[3]],
            },
            "sections": [
                {
                    "type": "custom",
                    "title": "DỰ ÁN CỘNG ĐỒNG",
                    "confidence": 0.92,
                    "source_block_ids": [ids[4]],
                    "blocks": [
                        {
                            "type": "paragraph",
                            "text": "Điều phối chương trình bằng tiếng Việt.",
                            "confidence": 0.93,
                            "source_block_ids": [ids[5]],
                        }
                    ],
                }
            ],
            "unmapped_references": [
                {
                    "block_id": ids[2],
                    "reason": "ambiguous_content",
                    "confidence": 0.7,
                }
            ],
            "confidence": 0.94,
        }
    )


def test_semantic_structuring_success_preserves_multilingual_custom_content(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = """NGUYỄN MINH AN
an@example.test
TÓM TẮT
Giữ nguyên câu chữ của ứng viên.
DỰ ÁN CỘNG ĐỒNG
Điều phối chương trình bằng tiếng Việt.
"""
    raw = cv_structuring_service.build_manual_text_extraction(source)
    semantic = _semantic_response_for(raw)
    captured: dict[str, object] = {}

    async def fake_parser(
        system_prompt: str,
        user_input: str,
        response_model: type,
        **kwargs: object,
    ) -> LLMSemanticCVResponse:
        captured["prompt"] = system_prompt
        captured["input"] = user_input
        assert response_model is LLMSemanticCVResponse
        validator = kwargs["result_validator"]
        assert callable(validator)
        validator(semantic)
        return semantic

    monkeypatch.setattr(
        cv_structuring_service,
        "call_llm_with_fallback",
        fake_parser,
    )
    result = asyncio.run(cv_structuring_service.structure_cv(cv_text=source))

    assert result.used_fallback is False
    assert result.document.parser_version == "llm-semantic-1.0"
    assert result.document.requires_reprocessing is False
    assert result.document.identity.full_name == "NGUYỄN MINH AN"
    assert result.document.summary is not None
    assert result.document.summary.text == "Giữ nguyên câu chữ của ứng viên."
    assert result.document.sections[0].type == "custom"
    assert result.document.sections[0].title == "DỰ ÁN CỘNG ĐỒNG"
    assert result.document.sections[0].blocks[0].text == (
        "Điều phối chương trình bằng tiếng Việt."
    )
    assert (
        result.document.sections[0]
        .blocks[0]
        .block_id.startswith("semantic-section-1-block-")
    )
    assert "bbox=" in str(captured["input"])
    assert "Do not improve, rewrite, paraphrase" in str(captured["prompt"])


def test_semantic_parser_schema_rejects_server_owned_and_unknown_source_ids() -> None:
    raw = cv_structuring_service.build_manual_text_extraction(
        "NAME\nEXPERIENCE\nBuilt source system."
    )
    known_id = raw.pages[0].blocks[1].block_id
    with pytest.raises(ValidationError):
        LLMSemanticCVResponse.model_validate(
            {
                "identity": {},
                "sections": [],
                "unmapped_references": [],
                "confidence": 1,
                "raw_extraction_id": "forged-server-id",
            }
        )

    forged = LLMSemanticCVResponse.model_validate(
        {
            "identity": {},
            "sections": [
                {
                    "type": "experience",
                    "title": "EXPERIENCE",
                    "source_block_ids": [known_id],
                    "blocks": [
                        {
                            "type": "paragraph",
                            "text": "Built source system.",
                            "source_block_ids": ["forged-block-id"],
                        }
                    ],
                }
            ],
            "unmapped_references": [],
            "confidence": 0.5,
        }
    )
    with pytest.raises(InvalidSourceReferenceError):
        cv_structuring_service.assemble_semantic_document(
            raw=raw,
            response=forged,
            source_text="NAME\nEXPERIENCE\nBuilt source system.",
            raw_extraction_ref_id=None,
        )


def test_semantic_parser_exhaustion_is_explicit_deterministic_fallback(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    retries: list[tuple[int, int]] = []

    async def failing_parser(*_: object, **kwargs: object) -> None:
        on_retry = kwargs["on_retry"]
        assert callable(on_retry)
        await on_retry(2, 4)
        raise HTTPException(status_code=503, detail="synthetic provider failure")

    async def record_retry(attempt: int, total: int) -> None:
        retries.append((attempt, total))

    monkeypatch.setattr(
        cv_structuring_service,
        "call_llm_with_fallback",
        failing_parser,
    )
    result = asyncio.run(
        cv_structuring_service.structure_cv(
            cv_text="NAME\nEXPERIENCE\nBuilt source system.",
            on_retry=record_retry,
        )
    )

    assert retries == [(2, 4)]
    assert result.used_fallback is True
    assert result.document.requires_reprocessing is True
    assert result.document.parser_version == "deterministic-fallback-1.0"
    assert "semantic_parser_fallback" in result.document.reconstruction_warnings


def test_pdf_raw_reference_is_owner_checked_and_authoritative(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    raw = RawExtraction(
        method=ExtractionMethod.NATIVE_BLOCKS,
        pages=[
            RawPage(
                page=1,
                blocks=[
                    RawBlock(
                        block_id="p1-b1",
                        page=1,
                        text="AUTHORITATIVE NAME",
                        extraction_method=ExtractionMethod.NATIVE_BLOCKS,
                    ),
                    RawBlock(
                        block_id="p1-b2",
                        page=1,
                        text="EXPERIENCE",
                        extraction_method=ExtractionMethod.NATIVE_BLOCKS,
                        reading_order=1,
                    ),
                ],
            )
        ],
    )
    semantic = LLMSemanticCVResponse.model_validate(
        {
            "identity": {
                "full_name": "AUTHORITATIVE NAME",
                "field_source_block_ids": {"full_name": ["p1-b1"]},
            },
            "sections": [],
            "unmapped_references": [
                {"block_id": "p1-b2", "reason": "ambiguous_content"}
            ],
            "confidence": 0.9,
        }
    )
    file_service = AsyncMock()
    file_service.load_raw_extraction.return_value = raw

    async def fake_parser(*_: object, **__: object) -> LLMSemanticCVResponse:
        return semantic

    monkeypatch.setattr(
        cv_structuring_service,
        "call_llm_with_fallback",
        fake_parser,
    )
    result = asyncio.run(
        cv_structuring_service.structure_cv(
            cv_text="AUTHORITATIVE NAME\nEXPERIENCE",
            raw_extraction_ref_id="raw-ref-id",
            user_id="owner",
            file_service=file_service,
        )
    )

    file_service.load_raw_extraction.assert_awaited_once_with("owner", "raw-ref-id")
    assert result.source_text == "AUTHORITATIVE NAME\n\nEXPERIENCE"
    assert result.document.raw_extraction_id == "raw-ref-id"


def test_pdf_ref_denial_and_text_disagreement_stop_before_parser(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    parser = AsyncMock()
    monkeypatch.setattr(
        cv_structuring_service,
        "call_llm_with_fallback",
        parser,
    )
    denied_service = AsyncMock()
    denied_service.load_raw_extraction.return_value = None
    with pytest.raises(HTTPException) as denied:
        asyncio.run(
            cv_structuring_service.structure_cv(
                cv_text="Submitted CV",
                raw_extraction_ref_id="denied-ref",
                user_id="other-owner",
                file_service=denied_service,
            )
        )
    assert denied.value.status_code == 404

    raw = RawExtraction(
        method=ExtractionMethod.NATIVE_BLOCKS,
        pages=[
            RawPage(
                page=1,
                blocks=[
                    RawBlock(
                        block_id="p1-b1",
                        page=1,
                        text="Authoritative PDF candidate content",
                        extraction_method=ExtractionMethod.NATIVE_BLOCKS,
                    )
                ],
            )
        ],
    )
    mismatch_service = AsyncMock()
    mismatch_service.load_raw_extraction.return_value = raw
    with pytest.raises(HTTPException) as mismatch:
        asyncio.run(
            cv_structuring_service.structure_cv(
                cv_text="Materially altered manual candidate content",
                raw_extraction_ref_id="raw-ref",
                user_id="owner",
                file_service=mismatch_service,
            )
        )
    assert mismatch.value.status_code == 409
    parser.assert_not_awaited()


def test_manual_text_source_blocks_are_stable_and_authoritative() -> None:
    source = "NAME\n\nKỸ NĂNG\nPython\nCustom heading\nCustom content"
    first = cv_structuring_service.build_manual_text_extraction(source)
    second = cv_structuring_service.build_manual_text_extraction(source)

    assert first == second
    assert first.method == ExtractionMethod.MANUAL_TEXT
    assert [block.reading_order for block in first.pages[0].blocks] == list(
        range(len(first.pages[0].blocks))
    )
    assert all(
        block.block_id.startswith("manual-p1-b") for block in first.pages[0].blocks
    )
    assert _block_ids(first) == [
        "manual-p1-b1",
        "manual-p1-b2",
        "manual-p1-b3",
        "manual-p1-b4",
        "manual-p1-b5",
    ]


def _block_ids(raw) -> list[str]:
    return [block.block_id for page in raw.pages for block in page.blocks]


def _paragraph_response(
    *,
    heading_id: str,
    body_ids: list[str],
    text: str,
) -> LLMSemanticCVResponse:
    return LLMSemanticCVResponse.model_validate(
        {
            "identity": {},
            "sections": [
                {
                    "type": "experience",
                    "title": "EXPERIENCE",
                    "source_block_ids": [heading_id],
                    "blocks": [
                        {
                            "type": "paragraph",
                            "text": text,
                            "source_block_ids": body_ids,
                        }
                    ],
                }
            ],
            "unmapped_references": [],
            "confidence": 0.9,
        }
    )


class _SequenceProvider:
    name = "grounding-test-provider"
    model = "grounding-test-model"

    def __init__(self, responses: list[LLMSemanticCVResponse]) -> None:
        self.responses = responses
        self.calls = 0

    async def generate_structured(self, **_: object) -> SimpleNamespace:
        response = self.responses[min(self.calls, len(self.responses) - 1)]
        self.calls += 1
        return SimpleNamespace(data=response, input_tokens=0, output_tokens=0)


def _install_test_provider(
    monkeypatch: pytest.MonkeyPatch,
    responses: list[LLMSemanticCVResponse],
) -> _SequenceProvider:
    provider = _SequenceProvider(responses)
    monkeypatch.setattr(ai_service.config, "PROVIDERS", [provider])
    monkeypatch.setattr(ai_service.asyncio, "sleep", AsyncMock())
    monkeypatch.setattr(ai_service, "log_llm_request", lambda _: None)
    return provider


def test_grounding_accepts_conservative_layout_normalization_and_all_leaf_types() -> (
    None
):
    decomposed_name = "NGUYE\u0302N MINH AN"
    source = "\n".join(
        [
            decomposed_name,
            "Senior Backend Engineer | an@example.test | +84 912 345 678 | Hà Nội | https://example.test/an",
            "TÓM TẮT",
            "Xây dựng API trên",
            "nhiều thị trường.",
            "KINH NGHIỆM",
            "Senior Backend Engineer | Acme Corp",
            "Hà Nội | 2022–2024 | Built APIs.",
            "KỸ NĂNG",
            "Languages | Python | SQL",
            "CÔNG BỐ",
            "Reliable APIs | Nguyễn An | Journal X | 2024 | Published",
            "HỌC VẤN",
            "FTU | Bachelor | Economics | Hà Nội | 2018–2022 | Graduated with honors",
            "KHÁC",
            "• Built APIs | Improved reliability",
            "Additional exact line",
        ]
    )
    raw = cv_structuring_service.build_manual_text_extraction(source)
    ids = _block_ids(raw)
    response = LLMSemanticCVResponse.model_validate(
        {
            "identity": {
                "full_name": "NGUYÊN MINH AN",
                "headline": "Senior Backend Engineer",
                "email": "an@example.test",
                "phone": "+84 912 345 678",
                "location": "Hà Nội",
                "links": ["https://example.test/an"],
                "field_source_block_ids": {
                    "full_name": [ids[0]],
                    "headline": [ids[1]],
                    "email": [ids[1]],
                    "phone": [ids[1]],
                    "location": [ids[1]],
                    "links": {"https://example.test/an": [ids[1]]},
                },
            },
            "summary": {
                "text": "Xây dựng API trên nhiều thị trường.",
                "source_block_ids": [ids[3], ids[4]],
            },
            "sections": [
                {
                    "type": "experience",
                    "title": "KINH NGHIỆM",
                    "source_block_ids": [ids[5]],
                    "blocks": [
                        {
                            "type": "entry",
                            "title": "Senior Backend Engineer",
                            "organization": "Acme Corp",
                            "location": "Hà Nội",
                            "date": "2022–2024",
                            "bullets": ["Built APIs."],
                            "source_block_ids": [ids[6], ids[7]],
                        }
                    ],
                },
                {
                    "type": "skills",
                    "title": "KỸ NĂNG",
                    "source_block_ids": [ids[8]],
                    "blocks": [
                        {
                            "type": "skill_group",
                            "label": "Languages",
                            "skills": ["Python", "SQL"],
                            "source_block_ids": [ids[9]],
                        }
                    ],
                },
                {
                    "type": "publications",
                    "title": "CÔNG BỐ",
                    "source_block_ids": [ids[10]],
                    "blocks": [
                        {
                            "type": "publication",
                            "title": "Reliable APIs",
                            "authors": "Nguyễn An",
                            "venue": "Journal X",
                            "date": "2024",
                            "status": "Published",
                            "source_block_ids": [ids[11]],
                        }
                    ],
                },
                {
                    "type": "education",
                    "title": "HỌC VẤN",
                    "source_block_ids": [ids[12]],
                    "blocks": [
                        {
                            "type": "education",
                            "institution": "FTU",
                            "degree": "Bachelor",
                            "field": "Economics",
                            "location": "Hà Nội",
                            "date": "2018–2022",
                            "details": ["Graduated with honors"],
                            "source_block_ids": [ids[13]],
                        }
                    ],
                },
                {
                    "type": "custom",
                    "title": "KHÁC",
                    "source_block_ids": [ids[14]],
                    "blocks": [
                        {
                            "type": "paragraph",
                            "text": "Built APIs Improved reliability",
                            "source_block_ids": [ids[15]],
                        },
                        {
                            "type": "bullet",
                            "text": "Additional exact line",
                            "source_block_ids": [ids[16]],
                        },
                        {
                            "type": "unknown",
                            "lines": ["Additional exact line"],
                            "source_block_ids": [ids[16]],
                        },
                    ],
                },
            ],
            "unmapped_references": [
                {"block_id": ids[2], "reason": "ambiguous_content"}
            ],
            "confidence": 0.9,
        }
    )

    cv_structuring_service.validate_semantic_grounding(raw, response)
    document = cv_structuring_service.assemble_semantic_document(
        raw=raw,
        response=response,
        source_text=source,
        raw_extraction_ref_id=None,
    )

    assert document.identity.full_name == "NGUYÊN MINH AN"
    assert document.sections[0].title == "KINH NGHIỆM"
    assert document.sections[-1].title == "KHÁC"


@pytest.mark.parametrize(
    ("source", "body_ids", "returned_text"),
    [
        (
            "EXPERIENCE\nBuilt APIs.",
            [1],
            "Built 100 APIs and increased revenue by 80%.",
        ),
        ("EXPERIENCE\nBuilt APIs.", [1], "Created backend services."),
        ("EXPERIENCE\nXây dựng API.", [1], "Built APIs."),
        ("EXPERIENCE\nBuilt APIs.\nWorked at Acme.", [2], "Built APIs."),
        (
            "EXPERIENCE\nBuilt APIs across\nmultiple markets.",
            [1],
            "Built APIs across multiple markets.",
        ),
        ("EXPERIENCE\nBuilt APIs.", [1], "built APIs."),
    ],
    ids=[
        "invented-metrics",
        "paraphrase",
        "translation",
        "wrong-known-block",
        "partial-source-ids",
        "case-change",
    ],
)
def test_grounding_rejects_unattributed_parser_text(
    source: str,
    body_ids: list[int],
    returned_text: str,
) -> None:
    raw = cv_structuring_service.build_manual_text_extraction(source)
    ids = _block_ids(raw)
    response = _paragraph_response(
        heading_id=ids[0],
        body_ids=[ids[index] for index in body_ids],
        text=returned_text,
    )

    with pytest.raises(SemanticGroundingError) as error:
        cv_structuring_service.validate_semantic_grounding(raw, response)

    assert error.value.field_path == "sections[0].blocks[0].text"
    assert error.value.reason == "not_in_cited_source"
    assert returned_text not in str(error.value)


def test_assembly_defense_rejects_invented_metric_reproduction() -> None:
    source = "EXPERIENCE\nBuilt APIs."
    raw = cv_structuring_service.build_manual_text_extraction(source)
    ids = _block_ids(raw)
    response = _paragraph_response(
        heading_id=ids[0],
        body_ids=[ids[1]],
        text="Built 100 APIs and increased revenue by 80%.",
    )

    with pytest.raises(SemanticGroundingError):
        cv_structuring_service.assemble_semantic_document(
            raw=raw,
            response=response,
            source_text=source,
            raw_extraction_ref_id=None,
        )


def test_user_visible_section_title_must_preserve_source_language_and_case() -> None:
    source = "KINH NGHIỆM\nXây dựng API."
    raw = cv_structuring_service.build_manual_text_extraction(source)
    ids = _block_ids(raw)
    response = _paragraph_response(
        heading_id=ids[0],
        body_ids=[ids[1]],
        text="Xây dựng API.",
    )
    response.sections[0].title = "KINH NGHIỆM"
    cv_structuring_service.validate_semantic_grounding(raw, response)
    response.sections[0].title = "Experience"

    with pytest.raises(SemanticGroundingError) as error:
        cv_structuring_service.validate_semantic_grounding(raw, response)

    assert error.value.field_path == "sections[0].title"
    assert response.sections[0].type == "experience"


def test_grounding_validator_retries_then_accepts_grounded_response(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = "EXPERIENCE\nBuilt APIs."
    raw = cv_structuring_service.build_manual_text_extraction(source)
    ids = _block_ids(raw)
    invalid = _paragraph_response(
        heading_id=ids[0],
        body_ids=[ids[1]],
        text="Built 100 APIs.",
    )
    valid = _paragraph_response(
        heading_id=ids[0],
        body_ids=[ids[1]],
        text="Built APIs.",
    )
    retries: list[tuple[int, int]] = []
    provider = _install_test_provider(monkeypatch, [invalid, valid])

    async def record_retry(attempt: int, total: int) -> None:
        retries.append((attempt, total))

    result = asyncio.run(
        cv_structuring_service.structure_cv(
            cv_text=source,
            on_retry=record_retry,
        )
    )

    assert provider.calls == 2
    assert retries == [(2, 2)]
    assert result.used_fallback is False
    assert result.document.sections[0].blocks[0].text == "Built APIs."


def test_grounding_exhaustion_returns_explicit_stale_fallback(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    source = "EXPERIENCE\nBuilt APIs."
    raw = cv_structuring_service.build_manual_text_extraction(source)
    ids = _block_ids(raw)
    invalid = _paragraph_response(
        heading_id=ids[0],
        body_ids=[ids[1]],
        text="Built 100 APIs.",
    )
    retries: list[tuple[int, int]] = []
    provider = _install_test_provider(monkeypatch, [invalid])

    async def record_retry(attempt: int, total: int) -> None:
        retries.append((attempt, total))

    result = asyncio.run(
        cv_structuring_service.structure_cv(
            cv_text=source,
            on_retry=record_retry,
        )
    )

    assert provider.calls == cv_structuring_service.CV_STRUCTURING_MAX_RETRIES
    assert retries == [(2, cv_structuring_service.CV_STRUCTURING_MAX_RETRIES)]
    assert result.used_fallback is True
    assert result.document.requires_reprocessing is True
    assert result.document.parser_version == "deterministic-fallback-1.0"
    assert "semantic_parser_fallback" in result.document.reconstruction_warnings
    assert "Built APIs." not in caplog.text
    assert "Built 100 APIs." not in caplog.text


@pytest.mark.parametrize(
    "parser_error",
    [RuntimeError("synthetic programming error"), HTTPException(status_code=400)],
)
def test_structuring_does_not_hide_unexpected_or_non_retryable_errors(
    monkeypatch: pytest.MonkeyPatch,
    parser_error: Exception,
) -> None:
    async def failing_parser(*_: object, **__: object) -> None:
        raise parser_error

    monkeypatch.setattr(
        cv_structuring_service,
        "call_llm_with_fallback",
        failing_parser,
    )

    with pytest.raises(type(parser_error)) as raised:
        asyncio.run(
            cv_structuring_service.structure_cv(
                cv_text="EXPERIENCE\nBuilt APIs.",
            )
        )

    assert raised.value is parser_error


def test_multiblock_grounding_uses_authoritative_order_and_unused_occurrences() -> None:
    raw = RawExtraction(
        method=ExtractionMethod.MANUAL_TEXT,
        pages=[
            RawPage(
                page=1,
                blocks=[
                    RawBlock(
                        block_id="b2",
                        page=1,
                        text="second",
                        extraction_method=ExtractionMethod.MANUAL_TEXT,
                        reading_order=1,
                    ),
                    RawBlock(
                        block_id="b1",
                        page=1,
                        text="first",
                        extraction_method=ExtractionMethod.MANUAL_TEXT,
                        reading_order=0,
                    ),
                ],
            )
        ],
    )
    source = cv_source_grounding.normalize_source(raw)

    def leaf(value: str) -> cv_source_grounding.SemanticTextLeaf:
        return cv_source_grounding.SemanticTextLeaf(
            field_path="summary.text",
            value=value,
            normalized_value=cv_source_grounding.normalize_grounding_text(value),
            source_block_ids=["b2", "b1"],
            semantic_owner="summary",
        )

    matches = cv_source_grounding.match_leaf_to_source(leaf("first second"), source)
    assert [match.block_id for match in matches] == ["b1", "b2"]
    assert cv_source_grounding.match_leaf_to_source(leaf("second first"), source) == []
    assert (
        cv_source_grounding.match_leaf_to_source(
            leaf("first invented 80% second"),
            source,
        )
        == []
    )

    repeated_raw = RawExtraction(
        method=ExtractionMethod.MANUAL_TEXT,
        pages=[
            RawPage(
                page=1,
                blocks=[
                    RawBlock(
                        block_id="r3",
                        page=1,
                        text="second",
                        extraction_method=ExtractionMethod.MANUAL_TEXT,
                        reading_order=2,
                    ),
                    RawBlock(
                        block_id="r1",
                        page=1,
                        text="first",
                        extraction_method=ExtractionMethod.MANUAL_TEXT,
                        reading_order=0,
                    ),
                    RawBlock(
                        block_id="r2",
                        page=1,
                        text="second first",
                        extraction_method=ExtractionMethod.MANUAL_TEXT,
                        reading_order=1,
                    ),
                ],
            )
        ],
    )
    repeated_source = cv_source_grounding.normalize_source(repeated_raw)
    repeated_leaf = cv_source_grounding.SemanticTextLeaf(
        field_path="sections[0].blocks[0].text",
        value="first second",
        normalized_value="first second",
        source_block_ids=["r3", "r2", "r1"],
        semantic_owner="paragraph",
    )
    first_match = cv_source_grounding.match_leaf_to_source(
        repeated_leaf,
        repeated_source,
    )
    used_spans = {match.block_id: [(match.start, match.end)] for match in first_match}
    second_match = cv_source_grounding.match_leaf_to_source(
        repeated_leaf,
        repeated_source,
        used_spans=used_spans,
    )

    assert [match.block_id for match in first_match] == ["r1", "r2"]
    assert [match.block_id for match in second_match] == ["r2", "r3"]


def _current_gate_document() -> CVDocumentV2:
    return CVDocumentV2(
        sections=[
            CVSection(
                id="experience",
                type="experience",
                title="EXPERIENCE",
            )
        ],
        reconstruction_diagnostics=CVReconstructionDiagnostics(
            source_coverage=CVSourceCoverageDiagnostics(
                raw_block_count=1,
                accounted_block_count=1,
                significant_character_count=10,
                mapped_character_count=10,
                coverage_ratio=1.0,
            )
        ),
    )


def test_reconstruction_gate_rejects_present_or_missing_authoritative_diagnostics() -> (
    None
):
    clean = _current_gate_document()
    validate_reconstruction_gate(clean)

    # substantive_unmapped_character_count > 0 now logs a warning (not raises)
    diagnostic_warning = _current_gate_document()
    coverage = diagnostic_warning.reconstruction_diagnostics.source_coverage
    assert coverage is not None
    coverage.substantive_unmapped_character_count = 4
    # Should NOT raise — downgraded to warning
    validate_reconstruction_gate(diagnostic_warning)

    missing_diagnostic = _current_gate_document()
    missing_diagnostic.reconstruction_diagnostics = None
    with pytest.raises(ValueError, match="source coverage diagnostics are missing"):
        validate_reconstruction_gate(missing_diagnostic)

    legacy = _current_gate_document()
    legacy.reconstruction_version = 3
    legacy.reconstruction_diagnostics = None
    with pytest.raises(ValueError, match="legacy reconstruction is stale"):
        validate_reconstruction_gate(legacy)


@pytest.mark.parametrize(
    "reason",
    ["parser_omission", "unknown_section", "ambiguous_content"],
)
def test_reconstruction_gate_allows_substantive_unmapped_content_with_warning(
    reason: str,
) -> None:
    """Substantive unmapped content is now a warning (not a fatal gate error)."""
    document = _current_gate_document()
    document.unmapped_content = [
        CVUnmappedContent(
            block_id="b-unmapped",
            text="Unmapped award 2024",
            page=1,
            reason=reason,
        )
    ]

    # Should NOT raise — downgraded to warning to prevent pipeline gridlock
    validate_reconstruction_gate(document)


def test_finalization_assigns_stable_full_block_fragment_ids_and_document_hash() -> (
    None
):
    raw = RawExtraction(
        method=ExtractionMethod.MANUAL_TEXT,
        pages=[
            RawPage(
                page=1,
                blocks=[
                    RawBlock(
                        block_id="b1",
                        page=1,
                        text="EXPERIENCE",
                        extraction_method=ExtractionMethod.MANUAL_TEXT,
                        reading_order=0,
                    ),
                    RawBlock(
                        block_id="b2",
                        page=1,
                        text="Built APIs.",
                        extraction_method=ExtractionMethod.MANUAL_TEXT,
                        reading_order=1,
                    ),
                ],
            )
        ],
    )
    llm_unmapped = [
        LLMUnmappedReference(
            block_id="b1",
            reason="unknown_section",
        )
    ]

    first = finalize_document_provenance(raw, CVDocumentV2(), llm_unmapped)
    second = finalize_document_provenance(raw, CVDocumentV2(), llm_unmapped)

    first_fragments = {
        item.block_id: (
            item.fragment_id,
            item.source_start,
            item.source_end,
        )
        for item in first.unmapped_content
    }
    second_fragments = {
        item.block_id: (
            item.fragment_id,
            item.source_start,
            item.source_end,
        )
        for item in second.unmapped_content
    }
    assert first_fragments == second_fragments
    assert first_fragments["b1"][1:] == (0, len("EXPERIENCE"))
    assert first_fragments["b2"][1:] == (0, len("Built APIs."))

    first_json = first.model_dump_json()
    second_json = second.model_dump_json()
    assert (
        sha256(first_json.encode()).hexdigest()
        == sha256(second_json.encode()).hexdigest()
    )

    finalized_again = finalize_document_provenance(raw, first, llm_unmapped)
    assert (
        sha256(finalized_again.model_dump_json().encode()).hexdigest()
        == sha256(first_json.encode()).hexdigest()
    )


@pytest.mark.parametrize(
    "source_text",
    ["Skills:", "Experience:", "Email:", "Your Achievement"],
)
def test_unmapped_alphanumeric_labels_cannot_be_tagged_as_decorative(
    source_text: str,
) -> None:
    raw = RawExtraction(
        method=ExtractionMethod.MANUAL_TEXT,
        pages=[
            RawPage(
                page=1,
                blocks=[
                    RawBlock(
                        block_id="label-block",
                        page=1,
                        text=source_text,
                        extraction_method=ExtractionMethod.MANUAL_TEXT,
                        reading_order=0,
                    )
                ],
            )
        ],
    )
    result = cv_provenance_service.audit_source_conservation(
        raw,
        CVDocumentV2(),
        [
            LLMUnmappedReference(
                block_id="label-block",
                reason="decorative_content",
            )
        ],
    )

    assert result.is_valid is False
    assert result.diagnostics.substantive_unmapped_character_count > 0
    assert result.diagnostics.benign_unmapped_character_count == 0
    assert {issue.code for issue in result.diagnostics.issues} == {
        "substantive_source_omission"
    }


def _phase5_source_document() -> CVDocumentV2:
    return CVDocumentV2(
        summary=CVParagraphBlock(
            block_id="summary-1",
            text="Supported internal reporting.",
            source_block_ids=["raw-1"],
        ),
        sections=[
            CVSection(id="experience", type="experience", title="EXPERIENCE"),
        ],
        reconstruction_diagnostics=CVReconstructionDiagnostics(
            source_coverage=CVSourceCoverageDiagnostics(
                raw_block_count=1,
                accounted_block_count=1,
                significant_character_count=29,
                mapped_character_count=29,
                coverage_ratio=1.0,
            ),
        ),
    )


@pytest.mark.asyncio
async def test_rewrite_semantics_rejects_bidirectional_claim_change_before_llm(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    bundle = CVRewriteEvidenceBundle(
        block_id="summary-1",
        field="text",
        original_value="Supported internal reporting.",
        original_value_hash=hash_field_value("Supported internal reporting."),
        cited_raw_block_ids=["raw-1"],
        ordered_raw_evidence=["Supported internal reporting."],
    )
    operation = CVRewriteOperation(
        block_id="summary-1",
        field="text",
        original_value_hash=bundle.original_value_hash,
        proposed_value="Owned regulatory compliance reporting.",
    )
    router = AsyncMock()
    monkeypatch.setattr(
        "app.services.cv_tailoring_service.call_llm_with_fallback",
        router,
    )

    valid, reasons = verify_block_rewrite_semantics(bundle, operation)

    assert valid is False
    assert "semantic_new_claim_detected" in reasons
    router.assert_not_awaited()


@pytest.mark.asyncio
async def test_rewrite_semantics_uses_independent_fail_closed_validator(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    bundle = CVRewriteEvidenceBundle(
        block_id="summary-1",
        field="text",
        original_value="Supported internal reporting.",
        original_value_hash=hash_field_value("Supported internal reporting."),
        cited_raw_block_ids=["raw-1"],
        ordered_raw_evidence=["Supported internal reporting."],
    )
    operation = CVRewriteOperation(
        block_id="summary-1",
        field="text",
        original_value_hash=bundle.original_value_hash,
        proposed_value="Internal reporting supported.",
    )
    router = AsyncMock(
        return_value=CVRewriteSemanticVerdict(
            no_new_claims=False,
            no_lost_claims=True,
            reason_codes=["uncertain"],
        ),
    )
    monkeypatch.setattr(
        "app.services.cv_tailoring_service.call_llm_with_fallback",
        router,
    )

    valid, reasons = await verify_block_rewrite_semantics_with_validator(
        bundle,
        operation,
    )

    assert valid is False
    assert reasons == ["semantic_new_claim_detected", "semantic_validator_uncertain"]
    assert router.await_args.kwargs["feature_name"] == "cv_rewrite_semantic_validator"


@pytest.mark.asyncio
async def test_rewrite_semantics_rejects_contradictory_reason_code(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    original = "Supported internal reporting."
    bundle = CVRewriteEvidenceBundle(
        block_id="summary-1",
        field="text",
        original_value=original,
        original_value_hash=hash_field_value(original),
        cited_raw_block_ids=["raw-1"],
        ordered_raw_evidence=[original],
    )
    operation = CVRewriteOperation(
        block_id="summary-1",
        field="text",
        original_value_hash=bundle.original_value_hash,
        proposed_value="Internal reporting supported.",
    )
    monkeypatch.setattr(
        "app.services.cv_tailoring_service.call_llm_with_fallback",
        AsyncMock(
            return_value=CVRewriteSemanticVerdict(
                no_new_claims=True,
                no_lost_claims=True,
                reason_codes=["new_claim"],
            ),
        ),
    )

    assert await verify_block_rewrite_semantics_with_validator(bundle, operation) == (
        False,
        ["semantic_new_claim_detected"],
    )


@pytest.mark.parametrize(
    ("original", "proposed", "expected_reason"),
    [
        (
            "Supported 5 teams and 5 projects.",
            "Supported 5 teams and projects.",
            "existing_number_removed",
        ),
        (
            "Supported 5 teams and projects.",
            "Supported 5 teams and 5 projects.",
            "unsupported_number_invented",
        ),
    ],
)
def test_rewrite_deterministic_preserves_numeric_occurrence_counts(
    original: str,
    proposed: str,
    expected_reason: str,
) -> None:
    bundle = CVRewriteEvidenceBundle(
        block_id="summary-1",
        field="text",
        original_value=original,
        original_value_hash=hash_field_value(original),
        cited_raw_block_ids=["raw-1"],
        ordered_raw_evidence=[original],
    )
    operation = CVRewriteOperation(
        block_id="summary-1",
        field="text",
        original_value_hash=bundle.original_value_hash,
        proposed_value=proposed,
    )

    valid, reasons = validate_block_rewrite_deterministic(bundle, operation)

    if expected_reason == "existing_number_removed":
        # Number removal is now allowed — deterministic gate no longer blocks this
        assert valid is True
        assert expected_reason not in reasons
    else:
        assert valid is False
        assert expected_reason in reasons
    assert verify_block_rewrite_semantics(bundle, operation) == (True, [])


def test_rewrite_deterministic_rejects_operation_field_mismatch() -> None:
    original = "Supported internal reporting."
    bundle = CVRewriteEvidenceBundle(
        block_id="summary-1",
        field="text",
        original_value=original,
        original_value_hash=hash_field_value(original),
        cited_raw_block_ids=["raw-1"],
        ordered_raw_evidence=[original],
    )
    operation = CVRewriteOperation(
        block_id="summary-1",
        field="bullets",
        original_value_hash=bundle.original_value_hash,
        proposed_value="Internal reporting supported.",
    )

    assert validate_block_rewrite_deterministic(bundle, operation) == (
        False,
        ["field_mismatch"],
    )


@pytest.mark.asyncio
async def test_wrong_field_llm_operation_is_never_applied(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = _phase5_source_document()
    original = "Supported internal reporting."
    raw = RawExtraction(
        method=ExtractionMethod.MANUAL_TEXT,
        pages=[
            RawPage(
                page=1,
                blocks=[
                    RawBlock(
                        block_id="raw-1",
                        page=1,
                        text=original,
                        extraction_method=ExtractionMethod.MANUAL_TEXT,
                    )
                ],
            )
        ],
    )
    operation = CVRewriteOperation(
        block_id="summary-1",
        field="bullets",
        original_value_hash=hash_field_value(original),
        proposed_value="Internal reporting supported.",
    )
    monkeypatch.setattr(
        "app.services.cv_rewrite_service.call_llm_with_fallback",
        AsyncMock(return_value=CVRewriteOperationsPayload(operations=[operation])),
    )

    result = await rewrite_cv(
        source_document=source,
        source_raw_extraction=raw,
        jd_text="",
        source_language="en",
    )

    assert result.tailored_document == source
    assert result.diagnostics.accepted_count == 0
    assert result.diagnostics.preserved_count == 1


@pytest.mark.asyncio
async def test_rewrite_semantic_provider_failure_closes_but_programming_error_surfaces(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    bundle = CVRewriteEvidenceBundle(
        block_id="summary-1",
        field="text",
        original_value="Supported internal reporting.",
        original_value_hash=hash_field_value("Supported internal reporting."),
        cited_raw_block_ids=["raw-1"],
        ordered_raw_evidence=["Supported internal reporting."],
    )
    operation = CVRewriteOperation(
        block_id="summary-1",
        field="text",
        original_value_hash=bundle.original_value_hash,
        proposed_value="Internal reporting supported.",
    )
    provider_failure = AsyncMock(
        side_effect=HTTPException(status_code=503, detail="provider unavailable"),
    )
    monkeypatch.setattr(
        "app.services.cv_tailoring_service.call_llm_with_fallback",
        provider_failure,
    )
    assert await verify_block_rewrite_semantics_with_validator(bundle, operation) == (
        False,
        ["semantic_validator_unavailable"],
    )

    programming_error = AsyncMock(side_effect=RuntimeError("programming bug"))
    monkeypatch.setattr(
        "app.services.cv_tailoring_service.call_llm_with_fallback",
        programming_error,
    )
    with pytest.raises(RuntimeError, match="programming bug"):
        await verify_block_rewrite_semantics_with_validator(bundle, operation)


def test_tailored_gate_rejects_changed_summary_without_matching_decision() -> None:
    source = _phase5_source_document()
    tailored = source.model_copy(deep=True)
    assert tailored.summary is not None
    tailored.summary.text = "Owned regulatory compliance reporting."
    diagnostics = CVTailoringDiagnostics(
        source_document_hash=canonical_source_document_hash(source),
        jd_hash="",
        preserved_count=1,
        decisions=[
            CVRewriteDecision(
                operation_id="summary-preserved",
                block_id="summary-1",
                field="text",
                status="preserved",
                original_value_hash=hash_field_value(source.summary.text),
                proposed_value_hash=hash_field_value(source.summary.text),
            )
        ],
    )

    with pytest.raises(ValueError, match="non-accepted block differs"):
        validate_tailored_document_gate(source, tailored, diagnostics)


@pytest.mark.asyncio
async def test_missing_cited_raw_block_is_preserved_and_never_rewriteable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = _phase5_source_document()
    raw = RawExtraction(
        method=ExtractionMethod.MANUAL_TEXT,
        pages=[
            RawPage(
                page=1,
                blocks=[
                    RawBlock(
                        block_id="different-raw-id",
                        page=1,
                        text="Supported internal reporting.",
                        extraction_method=ExtractionMethod.MANUAL_TEXT,
                    )
                ],
            )
        ],
    )
    assert source.summary is not None
    assert build_evidence_bundle(source, raw, source.summary, "text", "en") is None
    router = AsyncMock()
    monkeypatch.setattr(
        "app.services.cv_rewrite_service.call_llm_with_fallback", router
    )

    result = await rewrite_cv(
        source_document=source,
        source_raw_extraction=raw,
        jd_text="",
        source_language="en",
    )

    router.assert_not_awaited()
    assert result.tailored_document == source
    assert result.diagnostics.preserved_count == 1
    assert result.diagnostics.decisions[0].reason_codes == [
        "missing_authoritative_raw_provenance"
    ]


def test_rewrite_evidence_uses_authoritative_raw_reading_order() -> None:
    source = _phase5_source_document()
    assert source.summary is not None
    source.summary.source_block_ids = ["raw-2", "raw-1"]
    raw = RawExtraction(
        method=ExtractionMethod.MANUAL_TEXT,
        pages=[
            RawPage(
                page=1,
                blocks=[
                    RawBlock(
                        block_id="raw-2",
                        page=1,
                        text="reporting.",
                        extraction_method=ExtractionMethod.MANUAL_TEXT,
                        reading_order=1,
                    ),
                    RawBlock(
                        block_id="raw-1",
                        page=1,
                        text="Supported internal",
                        extraction_method=ExtractionMethod.MANUAL_TEXT,
                        reading_order=0,
                    ),
                ],
            )
        ],
    )

    bundle = build_evidence_bundle(source, raw, source.summary, "text", "en")

    assert bundle is not None
    assert bundle.cited_raw_block_ids == ["raw-1", "raw-2"]
    assert bundle.ordered_raw_evidence == ["Supported internal", "reporting."]


def test_verified_user_edit_rebinds_same_one_time_analysis_key(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from uuid import UUID

    monkeypatch.setenv("NEXTAUTH_SECRET", "test-secret")
    user_id = UUID("11111111-1111-1111-1111-111111111111")
    source = _phase5_source_document()
    current = source.model_copy(deep=True)
    assert source.summary is not None
    source_hash = hash_field_value(source.summary.text)
    diagnostics = CVTailoringDiagnostics(
        source_document_hash=canonical_source_document_hash(source),
        jd_hash="",
        preserved_count=1,
        decisions=[
            CVRewriteDecision(
                operation_id="summary-preserved",
                block_id="summary-1",
                field="text",
                status="preserved",
                original_value_hash=source_hash,
                proposed_value_hash=source_hash,
            )
        ],
    )
    entitlement = issue_tailoring_entitlement_v3(
        user_id,
        "Synthetic CV",
        "",
        source,
        current,
        diagnostics,
    )
    analysis_key = entitlement.split(".")[2]
    edited = current.model_copy(deep=True)
    assert edited.summary is not None
    edited.summary.text = "Internal reporting supported."

    result = verify_and_rebind_user_edit(
        user_id=user_id,
        source_cv_text="Synthetic CV",
        jd_text="",
        source_document=source,
        current_tailored_document=current,
        edited_document=edited,
        diagnostics=diagnostics,
        tailoring_entitlement=entitlement,
    )

    assert result.tailored_document.summary is not None
    assert result.tailored_document.summary.origin.value == "user_edit"
    assert result.diagnostics.accepted_count == 1
    assert result.diagnostics.decisions[0].reason_codes == ["user_edit"]
    assert (
        verify_tailoring_entitlement_v3(
            result.tailoring_entitlement,
            user_id,
            "Synthetic CV",
            "",
            source,
            result.tailored_document,
            result.diagnostics,
        )
        == analysis_key
    )
