"""Unit tests for Phase 7/8 CV Export Service and Variant Re-binding."""

from datetime import datetime, timezone
from uuid import UUID, uuid4

import pytest

from app.models.cv_document_v2 import CVDocumentV2, CVIdentity, CVParagraphBlock
from app.models.cv_translation import CVTranslationDiagnostics, CVTranslationVariant
from app.schemas.tailored_cv import TailoredCVVersionResponse
from app.services import cv_export_service


def _sample_doc() -> CVDocumentV2:
    return CVDocumentV2(
        schema_version=2,
        extraction_version="v3",
        parser_version="v3",
        reconstruction_version=4,
        requires_reprocessing=False,
        identity=CVIdentity(full_name="Nguyễn Văn A", email="a@example.com"),
        summary=CVParagraphBlock(
            type="paragraph", block_id="b_sum", text="Tóm tắt bản thân."
        ),
        sections=[],
    )


def _sample_version(v_id: UUID, u_id: UUID) -> TailoredCVVersionResponse:
    doc = _sample_doc()
    now = datetime.now(timezone.utc)
    return TailoredCVVersionResponse(
        id=v_id,
        user_id=u_id,
        jd_text="Job Description for Senior Developer",
        tailored_cv={"name": "Nguyễn Văn A", "sections": []},
        document_v2=doc,
        source_document_v2=doc,
        selected_design="classic_ats",
        template_id="classic_ats",
        template_version=1,
        render_version=1,
        document_schema_version=2,
        reconstruction_version=4,
        reconstruction_status="current",
        tailoring_pipeline_version=3,
        source_language="vi",
        created_at=now,
        updated_at=now,
    )


@pytest.mark.asyncio
async def test_create_translation_uses_improved_document_v2(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    u_id = uuid4()
    v_id = uuid4()
    version = _sample_version(v_id, u_id)

    async def mock_get_version(
        *args: object, **kwargs: object
    ) -> TailoredCVVersionResponse:
        return version

    async def mock_tx(*args: object, **kwargs: object) -> CVTranslationVariant:
        doc = _sample_doc()
        doc.summary.text = "Summary in English."
        return CVTranslationVariant(
            user_id=u_id,
            tailored_cv_version_id=v_id,
            source_document_hash="src_hash",
            translated_document_hash="trans_hash",
            source_language="vi",
            target_language="en",
            status="completed",
            operation_id="op_123",
            translated_document=doc,
            diagnostics=CVTranslationDiagnostics(
                source_document_hash="src_hash",
                translated_document_hash="trans_hash",
                source_language="vi",
                target_language="en",
                is_valid=True,
            ),
        )

    monkeypatch.setattr("app.services.cv_export_service.get_version", mock_get_version)
    monkeypatch.setattr(
        "app.services.cv_export_service.verify_exportable_v3_gates", lambda v: None
    )
    monkeypatch.setattr(
        "app.services.cv_export_service.execute_translation_transaction", mock_tx
    )

    variant = await cv_export_service.create_translation(v_id, u_id, "en")
    assert variant.status == "completed"
    assert variant.target_language == "en"


@pytest.mark.asyncio
async def test_get_preview_verifies_variant_rebinding(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    u_id = uuid4()
    v_id = uuid4()
    variant_id = uuid4()
    version = _sample_version(v_id, u_id)

    translated_doc = _sample_doc()
    translated_doc.summary.text = "Summary translated."

    from app.services.cv_export_service import _doc_hash

    src_h = _doc_hash(version.document_v2)
    trans_h = _doc_hash(translated_doc)

    variant = CVTranslationVariant(
        id=variant_id,
        user_id=u_id,
        tailored_cv_version_id=v_id,
        source_document_hash=src_h,
        translated_document_hash=trans_h,
        source_language="vi",
        target_language="en",
        status="completed",
        operation_id="op_123",
        translated_document=translated_doc,
        diagnostics=CVTranslationDiagnostics(
            source_document_hash=src_h,
            translated_document_hash=trans_h,
            source_language="vi",
            target_language="en",
            is_valid=True,
        ),
    )

    async def mock_get_version(
        *args: object, **kwargs: object
    ) -> TailoredCVVersionResponse:
        return version

    async def mock_get_variant(*args: object, **kwargs: object) -> CVTranslationVariant:
        return variant

    monkeypatch.setattr("app.services.cv_export_service.get_version", mock_get_version)
    monkeypatch.setattr(
        "app.services.cv_export_service.verify_exportable_v3_gates", lambda v: None
    )
    monkeypatch.setattr(
        "app.services.cv_export_service.get_translation_variant", mock_get_variant
    )

    preview = await cv_export_service.get_preview(
        v_id, u_id, translation_variant_id=variant_id
    )
    assert preview.html is not None


@pytest.mark.asyncio
async def test_export_rejects_stale_translation_variant(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    u_id = uuid4()
    v_id = uuid4()
    variant_id = uuid4()
    version = _sample_version(v_id, u_id)

    translated_doc = _sample_doc()

    # Tampered / mismatched source hash
    variant = CVTranslationVariant(
        id=variant_id,
        user_id=u_id,
        tailored_cv_version_id=v_id,
        source_document_hash="stale_hash_mismatch",
        translated_document_hash="trans_h",
        source_language="vi",
        target_language="en",
        status="completed",
        operation_id="op_123",
        translated_document=translated_doc,
        diagnostics=CVTranslationDiagnostics(
            source_document_hash="stale_hash_mismatch",
            translated_document_hash="trans_h",
            source_language="vi",
            target_language="en",
            is_valid=True,
        ),
    )

    async def mock_get_version(
        *args: object, **kwargs: object
    ) -> TailoredCVVersionResponse:
        return version

    async def mock_get_variant(*args: object, **kwargs: object) -> CVTranslationVariant:
        return variant

    monkeypatch.setattr("app.services.cv_export_service.get_version", mock_get_version)
    monkeypatch.setattr(
        "app.services.cv_export_service.verify_exportable_v3_gates", lambda v: None
    )
    monkeypatch.setattr(
        "app.services.cv_export_service.get_translation_variant", mock_get_variant
    )

    with pytest.raises(ValueError, match="stale variant"):
        await cv_export_service.get_preview(
            v_id, u_id, translation_variant_id=variant_id
        )
