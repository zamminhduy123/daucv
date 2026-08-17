"""Validation gate for Phase 7 Evidence-Constrained CV Translation Variants."""

import hashlib
import json
import logging
import re
from collections import Counter

from app.models.cv_document_v2 import CVDocumentV2
from app.models.cv_translation import (
    CVTranslationDiagnostics,
)
from app.services.cv_language import detect_cv_language
from app.services.cv_source_grounding import iter_semantic_text_leaves

_logger = logging.getLogger(__name__)


class TranslationValidationError(ValueError):
    """Raised when a translation variant fails translation validation gate."""

    def __init__(self, diagnostics: CVTranslationDiagnostics, reason: str) -> None:
        super().__init__(f"CV Translation Gate Failed: {reason}")
        self.diagnostics = diagnostics


def _hash_val(val: object) -> str:
    s = val if isinstance(val, str) else json.dumps(val, ensure_ascii=False)
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def extract_translation_protected_facts(text: str) -> list[str]:
    """Extract invariant protected facts (numbers, dates, URLs, emails, tech tokens) for translation validation."""
    facts: list[str] = []

    # Numbers, percentages, metrics (e.g. 10,000, 40%, 5, 2020)
    for m in re.finditer(r"\b\d+(?:[.,]\d+)?%?\b", text):
        facts.append(m.group(0).casefold())

    # URLs and emails
    for m in re.finditer(r"https?://\S+|[\w.-]+@[\w.-]+", text):
        facts.append(m.group(0).casefold())

    # Known technology tokens / acronyms
    for m in re.finditer(
        r"\b(FastAPI|PostgreSQL|Python|Java|React|Next\.js|Docker|Kubernetes|AWS|GCP|SQL|NoSQL|Git)\b",
        text,
        re.IGNORECASE,
    ):
        facts.append(m.group(0).casefold())

    return sorted(facts)


def validate_translation_variant(
    source_document: CVDocumentV2,
    translated_document: CVDocumentV2,
    diagnostics: CVTranslationDiagnostics,
) -> None:
    """Validate that a translated CV document maintains exact structure, field coverage, and factual integrity.

    Raises TranslationValidationError if any check fails.
    """
    # 1. Identity Verification
    if source_document.identity != translated_document.identity:
        diagnostics.is_valid = False
        raise TranslationValidationError(
            diagnostics, "Identity details were improperly modified during translation."
        )

    # 2. Structural Equality Check
    if len(source_document.sections) != len(translated_document.sections):
        diagnostics.is_valid = False
        raise TranslationValidationError(
            diagnostics, "Section count changed during translation."
        )

    for s_idx, (src_sec, trans_sec) in enumerate(
        zip(source_document.sections, translated_document.sections, strict=True)
    ):
        if src_sec.type != trans_sec.type:
            diagnostics.is_valid = False
            raise TranslationValidationError(
                diagnostics, f"Section {s_idx} type changed."
            )
        if len(src_sec.blocks) != len(trans_sec.blocks):
            diagnostics.is_valid = False
            raise TranslationValidationError(
                diagnostics, f"Section {s_idx} block count changed."
            )
        for b_idx, (src_b, trans_b) in enumerate(
            zip(src_sec.blocks, trans_sec.blocks, strict=True)
        ):
            if src_b.block_id != trans_b.block_id or src_b.type != trans_b.type:
                diagnostics.is_valid = False
                raise TranslationValidationError(
                    diagnostics, f"Block {b_idx} ID or type changed."
                )

    # 3. Complete Field Leaf Set & Value Extraction
    src_leaves = {
        leaf.field_path: leaf.value
        for leaf in iter_semantic_text_leaves(source_document)
    }
    trans_leaves = {
        leaf.field_path: leaf.value
        for leaf in iter_semantic_text_leaves(translated_document)
    }

    missing_fields = set(src_leaves.keys()) - set(trans_leaves.keys())
    if missing_fields:
        diagnostics.is_valid = False
        raise TranslationValidationError(
            diagnostics,
            f"Missing fields in translated document: {sorted(missing_fields)}",
        )

    extra_fields = set(trans_leaves.keys()) - set(src_leaves.keys())
    if extra_fields:
        diagnostics.is_valid = False
        raise TranslationValidationError(
            diagnostics,
            f"Extra invented fields in translated document: {sorted(extra_fields)}",
        )

    # 4. Decision Coverage & Cryptographic Hash Verification
    decision_map = {}
    for d in diagnostics.decisions:
        if d.field_id in decision_map:
            diagnostics.is_valid = False
            raise TranslationValidationError(
                diagnostics, f"Duplicate decision recorded for field: {d.field_id}"
            )
        decision_map[d.field_id] = d

    missing_decisions = set(src_leaves.keys()) - set(decision_map.keys())
    if missing_decisions:
        diagnostics.is_valid = False
        raise TranslationValidationError(
            diagnostics, f"Missing decision for fields: {sorted(missing_decisions)}"
        )

    unknown_decisions = set(decision_map.keys()) - set(src_leaves.keys())
    if unknown_decisions:
        diagnostics.is_valid = False
        raise TranslationValidationError(
            diagnostics, f"Unknown decision field IDs: {sorted(unknown_decisions)}"
        )

    # Hash verification per decision
    for field_path, src_val in src_leaves.items():
        trans_val = trans_leaves[field_path]
        dec = decision_map[field_path]

        expected_src_hash = _hash_val(src_val)
        expected_trans_hash = _hash_val(trans_val)

        if dec.source_value_hash != expected_src_hash:
            diagnostics.is_valid = False
            raise TranslationValidationError(
                diagnostics, f"Source value hash mismatch for field: {field_path}"
            )
        if dec.translated_value_hash != expected_trans_hash:
            diagnostics.is_valid = False
            raise TranslationValidationError(
                diagnostics, f"Translated value hash mismatch for field: {field_path}"
            )

    # 5. Field-Local Protected Fact Multiset Equality
    mismatched_fact_fields: list[str] = []
    for field_path, src_val in src_leaves.items():
        trans_val = trans_leaves[field_path]
        src_text = src_val if isinstance(src_val, str) else " ".join(src_val)
        trans_text = trans_val if isinstance(trans_val, str) else " ".join(trans_val)

        src_facts = extract_translation_protected_facts(src_text)
        trans_facts = extract_translation_protected_facts(trans_text)

        if Counter(src_facts) != Counter(trans_facts):
            mismatched_fact_fields.append(field_path)

    if mismatched_fact_fields:
        diagnostics.is_valid = False
        raise TranslationValidationError(
            diagnostics, f"Protected facts mutated in fields: {mismatched_fact_fields}"
        )

    # 6. Aggregate Language Verification
    translatable_prose: list[str] = []
    for path, val in trans_leaves.items():
        if "identity" in path or "organization" in path or "institution" in path:
            continue
        text_str = val if isinstance(val, str) else " ".join(val)
        if text_str.strip():
            translatable_prose.append(text_str)

    aggregate_prose = "\n".join(translatable_prose)
    if aggregate_prose.strip() and len(aggregate_prose) > 50:
        detected_lang = detect_cv_language(aggregate_prose)
        if detected_lang != diagnostics.target_language:
            diagnostics.is_valid = False
            raise TranslationValidationError(
                diagnostics,
                f"Target language mismatch: expected {diagnostics.target_language}, detected {detected_lang}",
            )

    diagnostics.is_valid = True
