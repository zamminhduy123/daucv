"""Persist an LLM #3 canonical-CV delta as a verified Tailored CV Version."""

from __future__ import annotations

import hashlib
import logging
import re
from collections.abc import Iterable
from typing import Literal
from uuid import UUID

from app.models.cv_document_v2 import (
    ContentOrigin,
    CVBlockType,
    CVBulletBlock,
    CVDocumentV2,
    CVEntryBlock,
    CVParagraphBlock,
    CVRewriteDecision,
    CVSkillGroupBlock,
    CVTailoringDiagnostics,
)
from app.models.cv_raw_extraction import RawExtraction
from app.models.cv_tailoring import TailoredCVResponse
from app.models.domain import TailoredCV
from app.schemas.tailored_cv import (
    CVDesign,
    TailoredCVVersionCreate,
    TailoredCVVersionResponse,
)
from app.services.cv_language import detect_cv_language
from app.services.cv_reconstruction_service import validate_reconstruction_gate
from app.services.cv_rewrite_service import build_evidence_bundle
from app.services.cv_tailoring_service import (
    hash_field_value,
    validate_block_rewrite_deterministic,
    validate_tailored_document_gate,
    verify_block_rewrite_semantics_with_validator,
)
from app.services.tailored_cv_metadata import (
    canonical_source_document_hash,
    issue_tailoring_entitlement_v3,
)
from app.services.tailored_cv_service import create_version

_logger = logging.getLogger(__name__)

_BULLET_PATH_RE = re.compile(
    r"^(experience|research_experience|projects)\[(\d+)\]\.bullets\[(\d+)\](?:\.text)?$"
)


def _decision_id(
    block_id: str,
    field: str,
    original_hash: str,
    proposed_hash: str,
) -> str:
    return hashlib.sha256(
        f"{block_id}:{field}:{original_hash}:{proposed_hash}".encode()
    ).hexdigest()[:8]


def _mutable_fields(
    document: CVDocumentV2,
) -> Iterable[tuple[CVBlockType, Literal["text", "bullets", "skills"]]]:
    if document.summary is not None:
        yield document.summary, "text"
    for section in document.sections:
        for block in section.blocks:
            if isinstance(block, CVParagraphBlock):
                yield block, "text"
            elif isinstance(block, CVEntryBlock) and block.bullets:
                yield block, "bullets"
            elif isinstance(block, CVSkillGroupBlock) and block.skills:
                yield block, "skills"


def _canonical_entry_blocks(
    document: CVDocumentV2,
) -> dict[str, list[CVBlockType]]:
    """Mirror ``to_canonical_dict`` entry ordering for LLM #3's allowed paths."""
    entries: dict[str, list[CVBlockType]] = {
        "experience": [],
        "research_experience": [],
        "projects": [],
    }
    for section in document.sections:
        section_type = (
            section.type.lower() if isinstance(section.type, str) else section.type
        )
        if section_type not in {
            "experience",
            "projects",
            "research_experience",
            "research",
        }:
            continue
        title = (section.title or "").lower()
        if "research" in section_type or "research" in title:
            target = "research_experience"
        elif "project" in section_type or "project" in title:
            target = "projects"
        else:
            target = "experience"
        for block in section.blocks:
            if isinstance(block, (CVEntryBlock, CVBulletBlock, CVParagraphBlock)):
                entries[target].append(block)
    return entries


def _legacy_tailored_cv(document: CVDocumentV2) -> TailoredCV:
    """Populate compatibility JSON; rendering/export uses verified V2 document."""
    identity = document.to_canonical_dict()["identity"]
    contact_lines = [
        value
        for value in (
            identity.get("email"),
            identity.get("phone"),
            identity.get("location"),
        )
        if isinstance(value, str) and value.strip()
    ]
    return TailoredCV(
        name=identity.get("name") or "",
        headline=identity.get("headline") or "",
        contact_lines=contact_lines,
        summary=document.summary.text if document.summary else "",
    )


async def persist_pipeline_tailoring(
    *,
    user_id: UUID,
    source_text: str,
    raw_extraction: RawExtraction,
    source_document: CVDocumentV2,
    job_description: str | None,
    tailoring: TailoredCVResponse,
    selected_design: CVDesign = "classic_ats",
    analysis_key: str,
) -> TailoredCVVersionResponse:
    """Map bounded canonical bullet edits onto V2, validate, then persist once.

    The browser-supplied full canonical CV is deliberately ignored. Only the
    server-derived original text and the narrow LLM #3 operation log can alter
    the source document.
    """
    from app.services.cv_source_grounding import normalize_grounding_text

    validate_reconstruction_gate(source_document)
    jd_text = (
        job_description.strip() if job_description and job_description.strip() else ""
    )
    entry_blocks = _canonical_entry_blocks(source_document)
    tailored_document = source_document.model_copy(deep=True)
    tailored_blocks = {
        block.block_id: block for block, _ in _mutable_fields(tailored_document)
    }
    changed_bullets: dict[str, list[str]] = {}

    for change in tailoring.change_log:
        match = _BULLET_PATH_RE.fullmatch(change.path)
        if not match:
            _logger.warning(
                "Unsupported export tailoring path: %s. Skipping.", change.path
            )
            continue
        section, entry_index_raw, bullet_index_raw = match.groups()
        target_blocks = entry_blocks.get(section, [])
        entry_idx = int(entry_index_raw)
        if entry_idx >= len(target_blocks):
            _logger.warning(
                "Export tailoring entry index out of range: %s (len=%d). Skipping.",
                change.path,
                len(target_blocks),
            )
            continue
        block = target_blocks[entry_idx]
        if not isinstance(block, CVEntryBlock):
            _logger.warning(
                "Export path block is not a CVEntryBlock: %s. Skipping.", change.path
            )
            continue
        bullet_index = int(bullet_index_raw)

        orig_clean = change.original_text.strip()
        if (
            bullet_index >= len(block.bullets)
            or block.bullets[bullet_index].strip() != orig_clean
        ):
            matched_idx = None
            for idx, b in enumerate(block.bullets):
                if b.strip() == orig_clean or normalize_grounding_text(
                    b
                ) == normalize_grounding_text(orig_clean):
                    matched_idx = idx
                    break
            if matched_idx is not None:
                bullet_index = matched_idx
            elif bullet_index >= len(block.bullets):
                _logger.warning(
                    "Tailoring bullet index out of bounds: %s. Skipping.", change.path
                )
                continue

        proposed = changed_bullets.setdefault(block.block_id, list(block.bullets))
        if bullet_index < len(proposed):
            proposed[bullet_index] = change.proposed_text

    language = detect_cv_language(source_text)
    decisions: list[CVRewriteDecision] = []
    accepted_count = 0
    preserved_count = 0
    for block, field in _mutable_fields(source_document):
        original_value = getattr(block, field)
        original_hash = hash_field_value(original_value)
        proposed_value = changed_bullets.get(block.block_id)
        if proposed_value is None:
            decisions.append(
                CVRewriteDecision(
                    operation_id=_decision_id(
                        block.block_id, field, original_hash, original_hash
                    ),
                    block_id=block.block_id,
                    field=field,
                    status="preserved",
                    reason_codes=["unmodified_by_llm3"],
                    original_value_hash=original_hash,
                    proposed_value_hash=original_hash,
                )
            )
            preserved_count += 1
            continue
        if field != "bullets" or not isinstance(proposed_value, list):
            raise ValueError("LLM #3 attempted an unsupported export field.")

        bundle = build_evidence_bundle(
            source_document,
            raw_extraction,
            block,
            "bullets",
            language,
        )
        if bundle is None:
            raise ValueError(
                "Cannot export a rewrite without authoritative raw evidence."
            )

        from app.models.cv_document_v2 import CVRewriteOperation

        operation = CVRewriteOperation(
            block_id=block.block_id,
            field="bullets",
            original_value_hash=original_hash,
            proposed_value=proposed_value,
        )
        deterministic_ok, deterministic_reasons = validate_block_rewrite_deterministic(
            bundle,
            operation,
        )
        if not deterministic_ok:
            proposed_hash = hash_field_value(proposed_value)
            decisions.append(
                CVRewriteDecision(
                    operation_id=_decision_id(
                        block.block_id, field, original_hash, proposed_hash
                    ),
                    block_id=block.block_id,
                    field=field,
                    status="rejected",
                    reason_codes=deterministic_reasons,
                    original_value_hash=original_hash,
                    proposed_value_hash=proposed_hash,
                )
            )
            continue

        (
            semantic_ok,
            semantic_reasons,
        ) = await verify_block_rewrite_semantics_with_validator(
            bundle,
            operation,
        )
        if not semantic_ok:
            proposed_hash = hash_field_value(proposed_value)
            decisions.append(
                CVRewriteDecision(
                    operation_id=_decision_id(
                        block.block_id, field, original_hash, proposed_hash
                    ),
                    block_id=block.block_id,
                    field=field,
                    status="rejected",
                    reason_codes=semantic_reasons,
                    original_value_hash=original_hash,
                    proposed_value_hash=proposed_hash,
                )
            )
            continue

        target = tailored_blocks[block.block_id]
        assert isinstance(target, CVEntryBlock)
        target.original_values["bullets"] = list(target.bullets)
        target.bullets = list(proposed_value)
        target.tailored_values["bullets"] = list(proposed_value)
        target.origin = ContentOrigin.LLM_REWRITE
        proposed_hash = hash_field_value(proposed_value)
        decisions.append(
            CVRewriteDecision(
                operation_id=_decision_id(
                    block.block_id, field, original_hash, proposed_hash
                ),
                block_id=block.block_id,
                field=field,
                status="accepted",
                reason_codes=[],
                original_value_hash=original_hash,
                proposed_value_hash=proposed_hash,
            )
        )
        accepted_count += 1

    rejected_count = sum(1 for d in decisions if d.status == "rejected")
    diagnostics = CVTailoringDiagnostics(
        source_document_hash=canonical_source_document_hash(source_document),
        jd_hash=hashlib.sha256(jd_text.encode()).hexdigest() if jd_text else "",
        accepted_count=accepted_count,
        preserved_count=preserved_count,
        rejected_count=rejected_count,
        decisions=decisions,
    )
    validate_tailored_document_gate(source_document, tailored_document, diagnostics)
    entitlement = issue_tailoring_entitlement_v3(
        user_id,
        source_text,
        jd_text,
        source_document,
        tailored_document,
        diagnostics,
        analysis_key=analysis_key,
    )
    return await create_version(
        user_id,
        TailoredCVVersionCreate(
            tailored_cv=_legacy_tailored_cv(tailored_document),
            source_cv_text=source_text,
            suggested_edits=[],
            jd_text=jd_text,
            selected_design=selected_design,
            tailoring_entitlement=entitlement,
            document_v2=tailored_document,
            source_document_v2=source_document,
            tailoring_diagnostics=diagnostics,
        ),
    )
