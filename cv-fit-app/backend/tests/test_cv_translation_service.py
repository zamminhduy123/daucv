"""Tests for Phase 7 Evidence-Constrained CV Translation Variants."""

import pytest

from app.models.cv_document_v2 import (
    CVDocumentV2,
    CVEntryBlock,
    CVIdentity,
    CVIdentitySourceMap,
    CVParagraphBlock,
    CVSection,
)
from app.services.cv_translation_service import (
    TranslationBatchResponse,
    TranslationItem,
    translate_cv_document,
)
from app.services.cv_translation_validation import (
    TranslationValidationError,
)


def _sample_doc() -> CVDocumentV2:
    return CVDocumentV2(
        schema_version=2,
        extraction_version="v3",
        parser_version="v3",
        reconstruction_version=4,
        requires_reprocessing=False,
        identity=CVIdentity(
            full_name="Nguyễn Văn A",
            headline="Backend Developer",
            email="nguyenvana@example.com",
            phone="0912345678",
            location="Hà Nội, Việt Nam",
            links=["https://github.com/nguyenvana"],
            source_block_ids=["b_id"],
            field_source_block_ids=CVIdentitySourceMap(
                full_name=["b_id"],
                headline=["b_id"],
                email=["b_id"],
                phone=["b_id"],
                location=["b_id"],
                links={},
            ),
            name="Nguyễn Văn A",
            contact_lines=["email: nguyenvana@example.com"],
        ),
        summary=CVParagraphBlock(
            type="paragraph",
            block_id="b_sum",
            text="Lập trình viên Backend với 5 năm kinh nghiệm xây dựng hệ thống microservices.",
        ),
        sections=[
            CVSection(
                id="sec_exp",
                type="experience",
                title="Kinh nghiệm làm việc",
                confidence=1.0,
                source_block_ids=["b_exp"],
                blocks=[
                    CVEntryBlock(
                        type="entry",
                        block_id="b_exp_1",
                        title="Senior Backend Engineer",
                        organization="TechCorp Vietnam",
                        date="2020 - Present",
                        bullets=[
                            "Phát triển hệ thống xử lý 10,000 requests/s với FastAPI.",
                            "Tối ưu hóa cơ sở dữ liệu PostgreSQL giảm 40% latency.",
                        ],
                    )
                ],
            )
        ],
        unmapped_content=[],
        reconstruction_warnings=[],
    )


@pytest.mark.asyncio
async def test_same_language_bypass() -> None:
    doc = _sample_doc()
    trans_doc, diag = await translate_cv_document(
        doc, target_language="vi", source_language="vi"
    )
    assert diag.is_valid is True
    assert diag.translated_count == 0
    assert trans_doc.identity.full_name == "Nguyễn Văn A"


@pytest.mark.asyncio
async def test_translation_to_english_preserves_protected_facts(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    doc = _sample_doc()

    async def mock_llm(*args: object, **kwargs: object) -> TranslationBatchResponse:
        return TranslationBatchResponse(
            translations=[
                TranslationItem(
                    field_id="summary.text",
                    translated_text="Backend Developer with 5 years of experience building microservices systems.",
                ),
                TranslationItem(
                    field_id="sections[0].blocks[0].title",
                    translated_text="Senior Backend Engineer",
                ),
                TranslationItem(
                    field_id="sections[0].blocks[0].date",
                    translated_text="2020 - Present",
                ),
                TranslationItem(
                    field_id="sections[0].blocks[0].bullets[0]",
                    translated_text="Developed system handling 10,000 requests/s with FastAPI.",
                ),
                TranslationItem(
                    field_id="sections[0].blocks[0].bullets[1]",
                    translated_text="Optimized PostgreSQL database reducing latency by 40%.",
                ),
            ]
        )

    monkeypatch.setattr(
        "app.services.cv_translation_service.call_llm_with_fallback", mock_llm
    )

    trans_doc, diag = await translate_cv_document(
        doc, target_language="en", source_language="vi"
    )

    assert diag.is_valid is True
    assert trans_doc.sections[0].title == "Work Experience"
    assert "10,000" in trans_doc.sections[0].blocks[0].bullets[0]
    assert "40%" in trans_doc.sections[0].blocks[0].bullets[1]


@pytest.mark.asyncio
async def test_translation_validation_rejects_mutated_numbers(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    doc = _sample_doc()

    async def mock_llm_bad(*args: object, **kwargs: object) -> TranslationBatchResponse:
        # 10,000 mutated to 99,000 -> must fail validation
        return TranslationBatchResponse(
            translations=[
                TranslationItem(
                    field_id="summary.text",
                    translated_text="Backend Developer with 5 years of experience.",
                ),
                TranslationItem(
                    field_id="sections[0].blocks[0].title",
                    translated_text="Senior Backend Engineer",
                ),
                TranslationItem(
                    field_id="sections[0].blocks[0].date",
                    translated_text="2020 - Present",
                ),
                TranslationItem(
                    field_id="sections[0].blocks[0].bullets[0]",
                    translated_text="Developed system handling 99,000 requests/s with FastAPI.",
                ),
                TranslationItem(
                    field_id="sections[0].blocks[0].bullets[1]",
                    translated_text="Optimized PostgreSQL database reducing latency by 40%.",
                ),
            ]
        )

    monkeypatch.setattr(
        "app.services.cv_translation_service.call_llm_with_fallback", mock_llm_bad
    )

    with pytest.raises(TranslationValidationError, match="Protected facts mutated"):
        await translate_cv_document(doc, target_language="en", source_language="vi")
