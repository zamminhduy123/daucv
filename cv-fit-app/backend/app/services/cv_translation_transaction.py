"""Operation lifecycle and credit transaction manager for Phase 7 CV Translation Variants."""

import hashlib
import json
import logging
from typing import Literal
from uuid import UUID

from app.core.db import Database
from app.dependencies import refund_credits, reserve_credits
from app.models.cv_document_v2 import CVDocumentV2
from app.models.cv_translation import (
    CVTranslationDiagnostics,
    CVTranslationVariant,
)
from app.services.cv_translation_service import translate_cv_document

_logger = logging.getLogger(__name__)


def compute_translation_operation_id(
    user_id: UUID,
    version_id: UUID,
    source_document_hash: str,
    target_language: str,
) -> str:
    """Generate deterministic operation_id for translation idempotency."""
    key_str = f"{user_id}:{version_id}:{source_document_hash}:{target_language}"
    return hashlib.sha256(key_str.encode("utf-8")).hexdigest()


async def execute_translation_transaction(
    user_id: UUID,
    version_id: UUID,
    source_document: CVDocumentV2,
    target_language: Literal["vi", "en"],
    source_language: str = "vi",
) -> CVTranslationVariant:
    """Orchestrate translation operation lifecycle with transactional credit reservation and single-refund safety."""
    src_hash = hashlib.sha256(
        json.dumps(source_document.model_dump(mode="json"), sort_keys=True).encode()
    ).hexdigest()
    op_id = compute_translation_operation_id(
        user_id, version_id, src_hash, target_language
    )

    # 1. Check for cached completed variant in DB
    existing_row = await Database.fetch_one(
        """SELECT * FROM public.cv_translation_variants
           WHERE user_id = $1 AND tailored_cv_version_id = $2 AND source_document_hash = $3 AND target_language = $4 AND status = 'completed'
           ORDER BY created_at DESC LIMIT 1""",
        user_id,
        version_id,
        src_hash,
        target_language,
    )
    if existing_row:
        diag = (
            CVTranslationDiagnostics.model_validate(
                json.loads(existing_row["translation_diagnostics"])
            )
            if isinstance(existing_row["translation_diagnostics"], str)
            else CVTranslationDiagnostics.model_validate(
                existing_row["translation_diagnostics"]
            )
        )
        doc = (
            CVDocumentV2.model_validate(json.loads(existing_row["translated_document"]))
            if isinstance(existing_row["translated_document"], str)
            else CVDocumentV2.model_validate(existing_row["translated_document"])
        )
        return CVTranslationVariant(
            id=existing_row["id"],
            user_id=existing_row["user_id"],
            tailored_cv_version_id=existing_row["tailored_cv_version_id"],
            source_document_hash=existing_row["source_document_hash"],
            translated_document_hash=existing_row["translated_document_hash"],
            source_language=existing_row["source_language"],
            target_language=existing_row["target_language"],
            translation_version=existing_row["translation_version"],
            translator_version=existing_row["translator_version"],
            status=existing_row["status"],
            operation_id=existing_row["operation_id"],
            translated_document=doc,
            diagnostics=diag,
            created_at=existing_row["created_at"],
            updated_at=existing_row["updated_at"],
        )

    # 2. Same language bypass — translate and persist without credit deduction
    if target_language == source_language:
        translated_doc, diag = await translate_cv_document(
            source_document,
            target_language=target_language,
            source_language=source_language,
        )
        diag_json = diag.model_dump_json()
        doc_json = translated_doc.model_dump_json()
        row = await Database.fetch_one(
            """INSERT INTO public.cv_translation_variants (
                   user_id, tailored_cv_version_id, source_document_hash, translated_document_hash,
                   source_language, target_language, translation_version, translator_version,
                   status, operation_id, translated_document, translation_diagnostics
               )
               VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11::jsonb, $12::jsonb)
               RETURNING *""",
            user_id,
            version_id,
            src_hash,
            diag.translated_document_hash,
            source_language,
            target_language,
            1,
            "v1_same_language_bypass",
            "completed",
            op_id,
            doc_json,
            diag_json,
        )
        if not row:
            raise RuntimeError(
                "Database insert for same-language translation variant returned no row"
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
            translated_document=translated_doc,
            diagnostics=diag,
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )

    # 3. Cross-language translation with transactional credit reservation & single refund
    await reserve_credits(
        user_id=user_id,
        amount=1,
        tx_type="cv_translation",
        description="CV translation credit reservation",
    )

    try:
        translated_doc, diag = await translate_cv_document(
            source_document,
            target_language=target_language,
            source_language=source_language,
        )

        diag_json = diag.model_dump_json()
        doc_json = translated_doc.model_dump_json()

        row = await Database.fetch_one(
            """INSERT INTO public.cv_translation_variants (
                   user_id, tailored_cv_version_id, source_document_hash, translated_document_hash,
                   source_language, target_language, translation_version, translator_version,
                   status, operation_id, translated_document, translation_diagnostics
               )
               VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11::jsonb, $12::jsonb)
               RETURNING *""",
            user_id,
            version_id,
            src_hash,
            diag.translated_document_hash,
            source_language,
            target_language,
            1,
            "v1_llm_constrained",
            "completed",
            op_id,
            doc_json,
            diag_json,
        )
        if not row:
            raise RuntimeError(
                "Database insert for translation variant returned no row"
            )
    except Exception as exc:
        _logger.error(
            "Translation operation or persistence failed; refunding credit: %s", exc
        )
        await refund_credits(
            user_id=user_id,
            amount=1,
            tx_type="cv_translation_refund",
            description="Refund for failed CV translation",
        )
        raise

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
        translated_document=translated_doc,
        diagnostics=diag,
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )
