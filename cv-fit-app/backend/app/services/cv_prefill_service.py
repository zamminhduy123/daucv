"""Deterministic prefill service for the /app/review wizard (edit stage only).

LLM-free: resolves the authoritative source text, runs layout extraction +
rule reconstruction, and stamps provenance. Routers stay HTTP-only and call
:func:`build_prefill_document`.
"""

from __future__ import annotations

from app.models.cv_document_v2 import CVDocumentV2
from app.services.cv_reconstruction_service import (
    canonical_cv_hash,
    finalize_document_provenance,
    reconstruct_from_lines,
)
from app.services.cv_structuring_service import resolve_authoritative_source
from app.services.files import FileService
from app.services.layout_extraction import raw_extraction_to_layout_lines


async def build_prefill_document(
    cv_text: str,
    raw_extraction_ref_id: str | None,
    user_id: str,
    file_service: FileService,
) -> tuple[CVDocumentV2, list[str]]:
    """Build the wizard prefill document from source text (no LLM, no credits)."""
    raw, source_text = await resolve_authoritative_source(
        cv_text=cv_text,
        raw_extraction_ref_id=raw_extraction_ref_id,
        user_id=user_id,
        file_service=file_service,
    )
    document = reconstruct_from_lines(raw_extraction_to_layout_lines(raw))
    document.parser_version = "deterministic-prefill-1.0"
    document.source_hash = canonical_cv_hash(source_text)
    document = finalize_document_provenance(raw, document)
    return document, list(document.reconstruction_warnings)
