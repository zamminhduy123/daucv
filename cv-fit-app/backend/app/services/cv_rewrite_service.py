"""Dedicated Evidence-Constrained CV Rewrite Service (Phase 5)."""

import hashlib
import json
import logging
import re
from typing import Any, Literal
from uuid import UUID

from fastapi import HTTPException
from pydantic import BaseModel, Field

from app.models.cv_document_v2 import (
    ContentOrigin,
    CVBlockType,
    CVDocumentV2,
    CVEntryBlock,
    CVParagraphBlock,
    CVRewriteDecision,
    CVRewriteOperation,
    CVSkillGroupBlock,
    CVTailoringDiagnostics,
    CVTailoringResult,
)
from app.models.cv_raw_extraction import RawExtraction
from app.prompts.system_prompts import build_cv_rewrite_prompt
from app.services.ai_service import call_llm_with_fallback
from app.services.cv_reconstruction_service import validate_reconstruction_gate
from app.services.cv_tailoring_service import (
    hash_field_value,
    validate_block_rewrite_deterministic,
    validate_tailored_document_gate,
    verify_block_rewrite_semantics_with_validator,
)
from app.services.tailored_cv_metadata import (
    canonical_source_document_hash,
    issue_tailoring_entitlement_v3,
    verify_tailoring_entitlement_v3,
)

_logger = logging.getLogger(__name__)


class CVRewriteEvidenceBundle(BaseModel):
    """Authoritative local evidence bundle for a single mutable block field."""

    block_id: str
    field: Literal["text", "bullets", "skills"]
    original_value: str | list[str]
    original_value_hash: str
    cited_raw_block_ids: list[str] = Field(default_factory=list)
    ordered_raw_evidence: list[str] = Field(default_factory=list)
    protected_facts: list[str] = Field(default_factory=list)
    source_language: str = "vi"


class CVRewriteOperationsPayload(BaseModel):
    """Payload format returned by the rewrite LLM."""

    operations: list[CVRewriteOperation] = Field(default_factory=list)


def extract_protected_facts(text: str) -> list[str]:
    """Extract numbers, percentages, currencies, dates, proper nouns, tech tokens, and acronyms."""
    facts: set[str] = set()

    # Numbers, percentages, metrics
    for m in re.finditer(r"\b\d+(?:[.,]\d+)?%?", text):
        facts.add(m.group(0).casefold())

    # Words, tech tokens, acronyms
    for m in re.finditer(r"\b[a-zA-Z0-9_.+#-]{2,}\b", text):
        facts.add(m.group(0).casefold())

    return sorted(facts)


def build_evidence_bundle(
    source_document: CVDocumentV2,
    raw_extraction: RawExtraction,
    block: CVBlockType,
    field: Literal["text", "bullets", "skills"],
    source_language: str,
) -> CVRewriteEvidenceBundle | None:
    """Build a CVRewriteEvidenceBundle strictly from the block's cited RawBlocks."""
    ordered_raw_blocks = sorted(
        (
            (
                raw_block.page,
                raw_block.reading_order,
                page_index,
                block_index,
                raw_block,
            )
            for page_index, page in enumerate(raw_extraction.pages)
            for block_index, raw_block in enumerate(page.blocks)
        ),
        key=lambda item: item[:4],
    )
    raw_block_map = {item[4].block_id: item[4] for item in ordered_raw_blocks}
    cited_ids = list(dict.fromkeys(block.source_block_ids))
    if not cited_ids or any(block_id not in raw_block_map for block_id in cited_ids):
        return None
    cited_set = set(cited_ids)
    ordered_evidence = [
        item[4].text for item in ordered_raw_blocks if item[4].block_id in cited_set
    ]
    combined_raw_text = "\n".join(ordered_evidence)

    if isinstance(block, CVParagraphBlock) and field == "text":
        orig_val = block.text
    elif isinstance(block, CVEntryBlock) and field == "bullets":
        orig_val = list(block.bullets)
    elif isinstance(block, CVSkillGroupBlock) and field == "skills":
        orig_val = list(block.skills)
    else:
        return None

    full_evidence_text = f"{orig_val}\n{combined_raw_text}"
    protected_facts = extract_protected_facts(full_evidence_text)

    return CVRewriteEvidenceBundle(
        block_id=block.block_id,
        field=field,
        original_value=orig_val,
        original_value_hash=hash_field_value(orig_val),
        cited_raw_block_ids=[
            item[4].block_id
            for item in ordered_raw_blocks
            if item[4].block_id in cited_set
        ],
        ordered_raw_evidence=ordered_evidence,
        protected_facts=protected_facts,
        source_language=source_language,
    )


def collect_mutable_bundles(
    source_document: CVDocumentV2,
    raw_extraction: RawExtraction,
    source_language: str,
) -> list[CVRewriteEvidenceBundle]:
    """Collect evidence bundles for all mutable fields in source_document."""
    bundles: list[CVRewriteEvidenceBundle] = []

    if source_document.summary:
        b = build_evidence_bundle(
            source_document,
            raw_extraction,
            source_document.summary,
            "text",
            source_language,
        )
        if b:
            bundles.append(b)

    for section in source_document.sections:
        for block in section.blocks:
            if isinstance(block, CVParagraphBlock):
                b = build_evidence_bundle(
                    source_document, raw_extraction, block, "text", source_language
                )
                if b:
                    bundles.append(b)
            elif isinstance(block, CVEntryBlock) and block.bullets:
                b = build_evidence_bundle(
                    source_document, raw_extraction, block, "bullets", source_language
                )
                if b:
                    bundles.append(b)
            elif isinstance(block, CVSkillGroupBlock) and block.skills:
                b = build_evidence_bundle(
                    source_document, raw_extraction, block, "skills", source_language
                )
                if b:
                    bundles.append(b)

    return bundles


async def rewrite_cv(
    *,
    source_document: CVDocumentV2,
    source_raw_extraction: RawExtraction,
    jd_text: str,
    source_language: str,
    background_tasks: Any | None = None,
) -> CVTailoringResult:
    """Entry point for Phase 5 evidence-constrained CV rewriting.

    Requires a validated Phase 4 source document. Produces a tailored CVDocumentV2 deep copy
    and server-owned CVTailoringDiagnostics.
    """
    # 1. Require Phase 4 quality gate
    validate_reconstruction_gate(source_document)

    source_doc_hash = canonical_source_document_hash(source_document)
    jd_hash = hashlib.sha256(jd_text.encode("utf-8")).hexdigest() if jd_text else ""

    # 2. Collect evidence bundles
    bundles = collect_mutable_bundles(
        source_document, source_raw_extraction, source_language
    )
    bundle_map = {(b.block_id, b.field): b for b in bundles}

    tailored_document = source_document.model_copy(deep=True)
    decisions: list[CVRewriteDecision] = []
    used_fallback = False

    all_mutable: list[tuple[CVBlockType, Literal["text", "bullets", "skills"]]] = []
    candidate_blocks: list[CVBlockType] = []
    if source_document.summary:
        candidate_blocks.append(source_document.summary)
    candidate_blocks.extend(
        block for section in source_document.sections for block in section.blocks
    )
    for block in candidate_blocks:
        if isinstance(block, CVParagraphBlock):
            all_mutable.append((block, "text"))
        elif isinstance(block, CVEntryBlock) and block.bullets:
            all_mutable.append((block, "bullets"))
        elif isinstance(block, CVSkillGroupBlock) and block.skills:
            all_mutable.append((block, "skills"))

    valid_bundle_keys = set(bundle_map)
    missing_evidence = [
        (block, field)
        for block, field in all_mutable
        if (block.block_id, field) not in valid_bundle_keys
    ]
    for block, field in missing_evidence:
        original_value = getattr(block, field)
        original_hash = hash_field_value(original_value)
        decisions.append(
            CVRewriteDecision(
                operation_id=_decision_id(
                    block.block_id, field, original_hash, original_hash
                ),
                block_id=block.block_id,
                field=field,
                status="preserved",
                reason_codes=["missing_authoritative_raw_provenance"],
                original_value_hash=original_hash,
                proposed_value_hash=original_hash,
            )
        )

    if not bundles:
        _logger.info(
            "No rewriteable evidence bundles found; returning exact source document."
        )
        diagnostics = CVTailoringDiagnostics(
            rewrite_version=1,
            source_document_hash=source_doc_hash,
            jd_hash=jd_hash,
            accepted_count=0,
            rejected_count=0,
            preserved_count=len(decisions),
            used_fallback=False,
            decisions=decisions,
        )
        validate_tailored_document_gate(source_document, tailored_document, diagnostics)
        return CVTailoringResult(
            source_document=source_document,
            tailored_document=tailored_document,
            diagnostics=diagnostics,
            tailoring_entitlement="",
        )

    # 3. Build LLM rewrite prompt payload
    prompt_system = build_cv_rewrite_prompt(source_language)
    user_payload = {
        "jd_context": jd_text,
        "source_language": source_language,
        "evidence_bundles": [b.model_dump(mode="json") for b in bundles],
    }
    user_content = json.dumps(user_payload, ensure_ascii=False)

    proposed_ops: list[CVRewriteOperation] = []
    try:
        generated = await call_llm_with_fallback(
            prompt_system,
            user_content,
            CVRewriteOperationsPayload,
            feature_name="cv_rewriter",
            prompt_version="1.0.0",
            background_tasks=background_tasks,
            max_retries=1,
        )
        proposed_ops = generated.operations
    except HTTPException as exc:
        _logger.warning(
            "LLM rewrite call failed or timed out: error_type=%s; failing closed to fallback",
            type(exc).__name__,
        )
        used_fallback = True

    # 4. Process proposed operations against bundles in stable bundle order
    ops_map: dict[tuple[str, str], CVRewriteOperation] = {}
    seen_keys: set[tuple[str, str]] = set()
    duplicate_keys: set[tuple[str, str]] = set()

    for op in proposed_ops:
        key = (op.block_id, op.field)
        if key in seen_keys:
            duplicate_keys.add(key)
        else:
            seen_keys.add(key)
            ops_map[key] = op

    tailored_block_map: dict[str, CVBlockType] = {}
    if tailored_document.summary:
        tailored_block_map[tailored_document.summary.block_id] = (
            tailored_document.summary
        )
    for sec in tailored_document.sections:
        for b in sec.blocks:
            tailored_block_map[b.block_id] = b

    accepted_count = 0
    rejected_count = 0
    preserved_count = len(decisions)

    for bundle in bundles:
        key = (bundle.block_id, bundle.field)
        orig_hash = bundle.original_value_hash

        if used_fallback or key not in ops_map:
            # Preserved (no operation proposed or fallback used)
            op_id = hashlib.sha256(
                f"{bundle.block_id}:{bundle.field}:{orig_hash}:{orig_hash}".encode()
            ).hexdigest()[:8]
            decisions.append(
                CVRewriteDecision(
                    operation_id=op_id,
                    block_id=bundle.block_id,
                    field=bundle.field,
                    status="preserved",
                    reason_codes=["unmodified_by_llm"]
                    if not used_fallback
                    else ["llm_fallback_preserved"],
                    original_value_hash=orig_hash,
                    proposed_value_hash=orig_hash,
                )
            )
            preserved_count += 1
            continue

        if key in duplicate_keys:
            # Duplicate operation proposed
            op = ops_map[key]
            prop_hash = hash_field_value(op.proposed_value)
            op_id = hashlib.sha256(
                f"{bundle.block_id}:{bundle.field}:{orig_hash}:{prop_hash}".encode()
            ).hexdigest()[:8]
            decisions.append(
                CVRewriteDecision(
                    operation_id=op_id,
                    block_id=bundle.block_id,
                    field=bundle.field,
                    status="rejected",
                    reason_codes=["duplicate_block_operation"],
                    original_value_hash=orig_hash,
                    proposed_value_hash=prop_hash,
                )
            )
            rejected_count += 1
            continue

        op = ops_map[key]
        prop_hash = hash_field_value(op.proposed_value)
        op_id = hashlib.sha256(
            f"{bundle.block_id}:{bundle.field}:{orig_hash}:{prop_hash}".encode()
        ).hexdigest()[:8]

        # Step A: Deterministic validation
        det_ok, det_reasons = validate_block_rewrite_deterministic(bundle, op)
        if not det_ok:
            decisions.append(
                CVRewriteDecision(
                    operation_id=op_id,
                    block_id=bundle.block_id,
                    field=bundle.field,
                    status="rejected",
                    reason_codes=det_reasons,
                    original_value_hash=orig_hash,
                    proposed_value_hash=prop_hash,
                )
            )
            rejected_count += 1
            continue

        # Step B: Semantic validation (fails closed)
        sem_ok, sem_reasons = await verify_block_rewrite_semantics_with_validator(
            bundle,
            op,
            background_tasks=background_tasks,
        )
        if not sem_ok:
            decisions.append(
                CVRewriteDecision(
                    operation_id=op_id,
                    block_id=bundle.block_id,
                    field=bundle.field,
                    status="rejected",
                    reason_codes=sem_reasons,
                    original_value_hash=orig_hash,
                    proposed_value_hash=prop_hash,
                )
            )
            rejected_count += 1
            continue

        # Accepted operation: update tailored_document deep copy
        target_block = tailored_block_map.get(bundle.block_id)
        if target_block:
            if (
                isinstance(target_block, CVParagraphBlock)
                and op.field == "text"
                and isinstance(op.proposed_value, str)
            ):
                target_block.original_values["text"] = target_block.text
                target_block.text = op.proposed_value
                target_block.tailored_values["text"] = op.proposed_value
                target_block.origin = ContentOrigin.LLM_REWRITE
            elif (
                isinstance(target_block, CVEntryBlock)
                and op.field == "bullets"
                and isinstance(op.proposed_value, list)
            ):
                target_block.original_values["bullets"] = list(target_block.bullets)
                target_block.bullets = list(op.proposed_value)
                target_block.tailored_values["bullets"] = list(op.proposed_value)
                target_block.origin = ContentOrigin.LLM_REWRITE
            elif (
                isinstance(target_block, CVSkillGroupBlock)
                and op.field == "skills"
                and isinstance(op.proposed_value, list)
            ):
                target_block.original_values["skills"] = list(target_block.skills)
                target_block.skills = list(op.proposed_value)
                target_block.tailored_values["skills"] = list(op.proposed_value)
                target_block.origin = ContentOrigin.LLM_REWRITE

        decisions.append(
            CVRewriteDecision(
                operation_id=op_id,
                block_id=bundle.block_id,
                field=bundle.field,
                status="accepted",
                reason_codes=[],
                original_value_hash=orig_hash,
                proposed_value_hash=prop_hash,
            )
        )
        accepted_count += 1

    diagnostics = CVTailoringDiagnostics(
        rewrite_version=1,
        source_document_hash=source_doc_hash,
        jd_hash=jd_hash,
        accepted_count=accepted_count,
        rejected_count=rejected_count,
        preserved_count=preserved_count,
        used_fallback=used_fallback,
        decisions=decisions,
    )

    # 5. Validate tailored document gate
    validate_tailored_document_gate(source_document, tailored_document, diagnostics)

    return CVTailoringResult(
        source_document=source_document,
        tailored_document=tailored_document,
        diagnostics=diagnostics,
        tailoring_entitlement="",
    )


def _decision_id(
    block_id: str,
    field: str,
    original_hash: str,
    proposed_hash: str,
) -> str:
    payload = f"{block_id}:{field}:{original_hash}:{proposed_hash}"
    return hashlib.sha256(payload.encode()).hexdigest()[:8]


def verify_and_rebind_user_edit(
    *,
    user_id: UUID,
    source_cv_text: str,
    jd_text: str,
    source_document: CVDocumentV2,
    current_tailored_document: CVDocumentV2,
    edited_document: CVDocumentV2,
    diagnostics: CVTailoringDiagnostics,
    tailoring_entitlement: str,
) -> CVTailoringResult:
    """Verify the signed current result, then authorize only its user edit delta."""
    analysis_key = verify_tailoring_entitlement_v3(
        tailoring_entitlement,
        user_id,
        source_cv_text,
        jd_text,
        source_document,
        current_tailored_document,
        diagnostics,
    )
    validate_reconstruction_gate(source_document)
    validate_tailored_document_gate(
        source_document,
        current_tailored_document,
        diagnostics,
    )

    source_blocks = _ordered_document_blocks(source_document)
    current_blocks = _ordered_document_blocks(current_tailored_document)
    edited_copy = edited_document.model_copy(deep=True)
    edited_blocks = _ordered_document_blocks(edited_copy)
    if not (len(source_blocks) == len(current_blocks) == len(edited_blocks)):
        raise ValueError(
            "CV user edit verification failed: document structure changed."
        )

    current_decisions = {
        (decision.block_id, decision.field): decision
        for decision in diagnostics.decisions
    }
    updated_decisions: list[CVRewriteDecision] = []
    for source_block, current_block, edited_block in zip(
        source_blocks,
        current_blocks,
        edited_blocks,
        strict=True,
    ):
        if (
            source_block.block_id != current_block.block_id
            or source_block.block_id != edited_block.block_id
            or type(source_block) is not type(current_block)
            or type(source_block) is not type(edited_block)
        ):
            raise ValueError(
                "CV user edit verification failed: block structure changed."
            )
        field = _rewriteable_field(source_block)
        if field is None:
            continue
        source_value = getattr(source_block, field)
        current_value = getattr(current_block, field)
        edited_value = getattr(edited_block, field)
        source_hash = hash_field_value(source_value)
        edited_hash = hash_field_value(edited_value)

        if edited_value == source_value:
            edited_block.origin = source_block.origin
            edited_block.original_values = dict(source_block.original_values)
            edited_block.tailored_values = dict(source_block.tailored_values)
            updated_decisions.append(
                CVRewriteDecision(
                    operation_id=_decision_id(
                        source_block.block_id, field, source_hash, source_hash
                    ),
                    block_id=source_block.block_id,
                    field=field,
                    status="preserved",
                    reason_codes=["user_edit_restored_source"]
                    if current_value != source_value
                    else ["unmodified_by_user"],
                    original_value_hash=source_hash,
                    proposed_value_hash=source_hash,
                )
            )
            continue

        if edited_value == current_value:
            prior = current_decisions.get((source_block.block_id, field))
            if prior is None or prior.status != "accepted":
                raise ValueError(
                    "CV user edit verification failed: signed decision is missing."
                )
            edited_block.origin = current_block.origin
            edited_block.original_values = dict(current_block.original_values)
            edited_block.tailored_values = dict(current_block.tailored_values)
            updated_decisions.append(prior.model_copy(deep=True))
            continue

        edited_block.origin = ContentOrigin.USER_EDIT
        edited_block.original_values = {
            **source_block.original_values,
            field: source_value,
        }
        edited_block.tailored_values = {
            **source_block.tailored_values,
            field: edited_value,
        }
        updated_decisions.append(
            CVRewriteDecision(
                operation_id=_decision_id(
                    source_block.block_id, field, source_hash, edited_hash
                ),
                block_id=source_block.block_id,
                field=field,
                status="accepted",
                reason_codes=["user_edit"],
                original_value_hash=source_hash,
                proposed_value_hash=edited_hash,
            )
        )

    status_counts = {
        status: sum(decision.status == status for decision in updated_decisions)
        for status in ("accepted", "rejected", "preserved")
    }
    updated_diagnostics = CVTailoringDiagnostics(
        rewrite_version=diagnostics.rewrite_version,
        source_document_hash=canonical_source_document_hash(source_document),
        jd_hash=hashlib.sha256(jd_text.encode("utf-8")).hexdigest() if jd_text else "",
        accepted_count=status_counts["accepted"],
        rejected_count=status_counts["rejected"],
        preserved_count=status_counts["preserved"],
        used_fallback=diagnostics.used_fallback,
        decisions=updated_decisions,
    )
    validate_tailored_document_gate(source_document, edited_copy, updated_diagnostics)
    replacement_entitlement = issue_tailoring_entitlement_v3(
        user_id,
        source_cv_text,
        jd_text,
        source_document,
        edited_copy,
        updated_diagnostics,
        analysis_key=analysis_key,
    )
    return CVTailoringResult(
        source_document=source_document,
        tailored_document=edited_copy,
        diagnostics=updated_diagnostics,
        tailoring_entitlement=replacement_entitlement,
    )


def _ordered_document_blocks(document: CVDocumentV2) -> list[CVBlockType]:
    return [
        *([document.summary] if document.summary is not None else []),
        *(block for section in document.sections for block in section.blocks),
    ]


def _rewriteable_field(
    block: CVBlockType,
) -> Literal["text", "bullets", "skills"] | None:
    if isinstance(block, CVParagraphBlock):
        return "text"
    if isinstance(block, CVEntryBlock) and block.bullets:
        return "bullets"
    if isinstance(block, CVSkillGroupBlock) and block.skills:
        return "skills"
    return None
