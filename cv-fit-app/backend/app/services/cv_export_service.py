"""Unified server-owned export orchestration service for Phase 6/7/8."""

import hashlib
import json
import logging
from typing import Literal
from uuid import UUID

from app.core.db import Database
from app.models.cv_document_v2 import CVDocumentV2
from app.models.cv_translation import CVTranslationVariant
from app.schemas.tailored_cv import CVPreviewResponse, TailoredCVVersionResponse
from app.services.cv_template_render_service import render_cv_document
from app.services.cv_translation_transaction import execute_translation_transaction
from app.services.tailored_cv_pdf import generate_tailored_cv_pdf
from app.services.tailored_cv_service import (
    TailoredCVNotFoundError,
    get_version,
    verify_exportable_v3_gates,
)

_logger = logging.getLogger(__name__)


def _doc_hash(doc: CVDocumentV2) -> str:
    return hashlib.sha256(
        json.dumps(doc.model_dump(mode="json"), sort_keys=True).encode("utf-8")
    ).hexdigest()


def _verify_exportable_translation_variant(
    version: TailoredCVVersionResponse,
    variant: CVTranslationVariant,
) -> None:
    """Safely verify translation variant integrity before export re-binding."""
    if variant.tailored_cv_version_id != version.id:
        raise ValueError("Translation variant does not match requested CV version.")

    if variant.status != "completed":
        raise ValueError("Translation variant status is not completed.")

    if not variant.diagnostics.is_valid:
        raise ValueError(
            "Translation variant diagnostics indicate invalid translation."
        )

    if variant.translation_version != 1:
        raise ValueError(
            f"Unsupported translation version: {variant.translation_version}"
        )

    if not version.document_v2:
        raise ValueError("Document V2 missing for tailored CV version.")

    expected_src_hash = _doc_hash(version.document_v2)
    if variant.source_document_hash != expected_src_hash:
        raise ValueError(
            "Translation variant source document hash mismatch (stale variant)."
        )

    expected_trans_hash = _doc_hash(variant.translated_document)
    if variant.translated_document_hash != expected_trans_hash:
        raise ValueError(
            "Translation variant translated document hash mismatch (tampered variant)."
        )


async def get_preview(
    version_id: UUID,
    user_id: UUID,
    translation_variant_id: UUID | None = None,
) -> CVPreviewResponse:
    """Orchestrate canonical server HTML preview for original or translated CV document."""
    version = await get_version(version_id, user_id)
    verify_exportable_v3_gates(version)

    document = version.document_v2
    source_lang = version.source_language or "vi"

    if translation_variant_id is not None:
        variant = await get_translation_variant(translation_variant_id, user_id)
        _verify_exportable_translation_variant(version, variant)
        document = variant.translated_document
        source_lang = variant.target_language

    if not document:
        raise ValueError("Document V2 missing for exportable CV version.")

    target_template = version.template_id or version.selected_design or "classic_ats"
    render_result = render_cv_document(
        document=document,
        template_id=target_template,
        template_version=version.template_version,
        language=source_lang,
    )

    return CVPreviewResponse(
        html=render_result.html,
        diagnostics=render_result.diagnostics,
        render_hash=render_result.render_hash,
    )


async def generate_pdf(
    version_id: UUID,
    user_id: UUID,
    translation_variant_id: UUID | None = None,
) -> bytes:
    """Orchestrate PDF generation for original or translated CV document."""
    version = await get_version(version_id, user_id)
    verify_exportable_v3_gates(version)

    document = version.document_v2
    source_lang = version.source_language or "vi"

    if translation_variant_id is not None:
        variant = await get_translation_variant(translation_variant_id, user_id)
        _verify_exportable_translation_variant(version, variant)
        document = variant.translated_document
        source_lang = variant.target_language

    if not document:
        raise ValueError("Document V2 missing for exportable CV version.")

    target_template = version.template_id or version.selected_design or "classic_ats"

    return await generate_tailored_cv_pdf(
        tailored_cv=version.tailored_cv,
        design=target_template,
        document_v2=document,
        language=source_lang,
        template_id=target_template,
        template_version=version.template_version,
    )


async def create_translation(
    version_id: UUID,
    user_id: UUID,
    target_language: Literal["vi", "en"],
) -> CVTranslationVariant:
    """Create translation variant for a validated tailored CV version."""
    version = await get_version(version_id, user_id)
    verify_exportable_v3_gates(version)

    # Translate Phase 5 improved document_v2
    doc_to_translate = version.document_v2 or version.source_document_v2
    if not doc_to_translate:
        raise ValueError("Document V2 missing for translation.")

    source_lang = version.source_language or "vi"
    return await execute_translation_transaction(
        user_id=user_id,
        version_id=version_id,
        source_document=doc_to_translate,
        target_language=target_language,
        source_language=source_lang,
    )


async def get_translation_variant(
    variant_id: UUID,
    user_id: UUID,
) -> CVTranslationVariant:
    """Fetch translation variant with owner authorization check."""
    row = await Database.fetch_one(
        "SELECT * FROM public.cv_translation_variants WHERE id = $1 AND user_id = $2",
        variant_id,
        user_id,
    )
    if not row:
        raise TailoredCVNotFoundError

    doc = (
        CVDocumentV2.model_validate(json.loads(row["translated_document"]))
        if isinstance(row["translated_document"], str)
        else CVDocumentV2.model_validate(row["translated_document"])
    )
    from app.models.cv_translation import CVTranslationDiagnostics

    diag = (
        CVTranslationDiagnostics.model_validate(
            json.loads(row["translation_diagnostics"])
        )
        if isinstance(row["translation_diagnostics"], str)
        else CVTranslationDiagnostics.model_validate(row["translation_diagnostics"])
    )

    return CVTranslationVariant(
        id=row["id"],
        user_id=row["user_id"],
        tailored_cv_version_id=row["tailored_cv_version_id"],
        source_document_hash=row["source_document_hash"],
        translated_document_hash=row["translated_document_hash"],
        source_language=row["source_language"],
        target_language=row["target_language"],
        translation_version=row["translation_version"],
        translator_version=row["translator_version"],
        status=row["status"],
        operation_id=row["operation_id"],
        translated_document=doc,
        diagnostics=diag,
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


async def list_translations(
    version_id: UUID,
    user_id: UUID,
) -> list[CVTranslationVariant]:
    """List all translation variants for a specific CV version."""
    rows = await Database.fetch_all(
        "SELECT * FROM public.cv_translation_variants WHERE tailored_cv_version_id = $1 AND user_id = $2 ORDER BY created_at DESC",
        version_id,
        user_id,
    )
    results = []

    from app.models.cv_translation import CVTranslationDiagnostics

    for row in rows:
        doc = (
            CVDocumentV2.model_validate(json.loads(row["translated_document"]))
            if isinstance(row["translated_document"], str)
            else CVDocumentV2.model_validate(row["translated_document"])
        )
        diag = (
            CVTranslationDiagnostics.model_validate(
                json.loads(row["translation_diagnostics"])
            )
            if isinstance(row["translation_diagnostics"], str)
            else CVTranslationDiagnostics.model_validate(row["translation_diagnostics"])
        )
        results.append(
            CVTranslationVariant(
                id=row["id"],
                user_id=row["user_id"],
                tailored_cv_version_id=row["tailored_cv_version_id"],
                source_document_hash=row["source_document_hash"],
                translated_document_hash=row["translated_document_hash"],
                source_language=row["source_language"],
                target_language=row["target_language"],
                translation_version=row["translation_version"],
                translator_version=row["translator_version"],
                status=row["status"],
                operation_id=row["operation_id"],
                translated_document=doc,
                diagnostics=diag,
                created_at=row["created_at"],
                updated_at=row["updated_at"],
            )
        )
    return results
