"""CV Reconstruction & Provenance Finalization Service."""

import logging
import re

from app.models.cv_document_v2 import (
    CURRENT_RECONSTRUCTION_VERSION,
    ContentOrigin,
    CVDocumentV2,
    CVReconstructionDiagnostics,
    CVUnmappedContent,
    LLMUnmappedReference,
    deterministic_unmapped_fragment_id,
)
from app.models.cv_raw_extraction import RawExtraction
from app.services.cv_source_grounding import collect_all_source_block_ids
from app.services.layout_extraction import ExtractedLine, normalize_line
from app.services.section_detector import classify_heading, detect_sections

_logger = logging.getLogger(__name__)


class InvalidSourceReferenceError(ValueError):
    """Raised when an LLM return references unknown source block IDs."""

    pass


def prune_placeholder_sections(document: CVDocumentV2) -> CVDocumentV2:
    """Filter out template placeholders and remove sections that contain no real candidate data."""
    placeholders = {
        "your strength",
        "explain how it benefits your work.",
        "explain how it benefits your work",
        "your achievement",
        "describe what you did and the impact it had.",
        "describe what you did and the impact it had",
        "company description",
    }
    clean_sections = []
    for section in document.sections:
        clean_blocks = []
        for block in section.blocks:
            if hasattr(block, "bullets") and isinstance(block.bullets, list):
                block.bullets = [
                    b for b in block.bullets if b.strip().lower() not in placeholders
                ]
            if (
                hasattr(block, "text")
                and isinstance(block.text, str)
                and block.text
                and block.text.strip().lower() in placeholders
            ):
                continue
            clean_blocks.append(block)
        section.blocks = clean_blocks
        if section.blocks or section.type == "summary":
            clean_sections.append(section)
    document.sections = clean_sections
    return document


def finalize_document_provenance(
    raw: RawExtraction,
    document: CVDocumentV2,
    llm_unmapped: list[LLMUnmappedReference] | None = None,
) -> CVDocumentV2:
    """Finalize provenance, populate server-side unmapped content, and ensure block coverage."""
    document = prune_placeholder_sections(document)
    valid_blocks = {
        block.block_id: block for page in raw.pages for block in page.blocks
    }

    referenced_ids = collect_all_source_block_ids(document)
    requested_unmapped = llm_unmapped or []
    requested_unmapped_ids = {item.block_id for item in requested_unmapped}

    unknown_ids = (referenced_ids | requested_unmapped_ids) - valid_blocks.keys()
    if unknown_ids:
        raise InvalidSourceReferenceError(
            f"Unknown source block IDs: {sorted(unknown_ids)}"
        )

    populated_unmapped: list[CVUnmappedContent] = []

    for item in requested_unmapped:
        source = valid_blocks[item.block_id]
        source_start = 0
        source_end = len(source.text)
        populated_unmapped.append(
            CVUnmappedContent(
                block_id=source.block_id,
                text=source.text,
                page=source.page,
                reason=item.reason,
                confidence=item.confidence,
                fragment_id=deterministic_unmapped_fragment_id(
                    source.block_id,
                    source_start,
                    source_end,
                ),
                source_start=source_start,
                source_end=source_end,
            )
        )

    covered_ids = referenced_ids | {item.block_id for item in populated_unmapped}

    for block_id, source in valid_blocks.items():
        if block_id not in covered_ids:
            reason = (
                "placeholder_content"
                if source.text.strip().lower()
                in {
                    "your strength",
                    "explain how it benefits your work.",
                    "explain how it benefits your work",
                    "your achievement",
                    "describe what you did and the impact it had.",
                    "describe what you did and the impact it had",
                    "company description",
                }
                else "parser_omission"
            )
            source_start = 0
            source_end = len(source.text)
            populated_unmapped.append(
                CVUnmappedContent(
                    block_id=block_id,
                    text=source.text,
                    page=source.page,
                    reason=reason,
                    confidence=None,
                    fragment_id=deterministic_unmapped_fragment_id(
                        block_id,
                        source_start,
                        source_end,
                    ),
                    source_start=source_start,
                    source_end=source_end,
                )
            )

    document.unmapped_content = populated_unmapped
    document.extraction_version = raw.extraction_version

    # Phase 4: Span-level source conservation audit
    from app.services.cv_provenance_service import audit_source_conservation

    conservation = audit_source_conservation(raw, document, llm_unmapped)
    document = conservation.document
    conservation_warnings = []
    for issue in conservation.diagnostics.issues:
        if issue.code not in {w for w in conservation_warnings}:
            conservation_warnings.append(issue.code)
    if not conservation.is_valid:
        conservation_warnings.append("source_coverage_incomplete")
    document.reconstruction_warnings = list(
        dict.fromkeys([*document.reconstruction_warnings, *conservation_warnings])
    )

    backfill_source_block_citations(document, raw)

    return document


def backfill_source_block_citations(document: CVDocumentV2, raw: RawExtraction) -> int:
    """Cite raw blocks for document blocks whose line ids resolve to them.

    The deterministic reconstruct path assigns ``source_line_ids`` (which, in
    practice, are raw block ids like ``p1-b10``) but never populates
    ``source_block_ids`` — only the LLM plan path does. Without citations,
    evidence bundles cannot be built and tailor-and-save rejects every
    rewrite. This fills citations exactly (no text fuzz): a line id is cited
    only if a raw block with that id exists. Blocks with no resolvable lines
    (e.g. candidate-added blocks with no PDF source) are left untouched;
    persistence skips their rewrites with an explicit reason instead.

    Returns the number of blocks that gained citations.
    """
    valid_ids = {block.block_id for page in raw.pages for block in page.blocks}
    targets = [block for section in document.sections for block in section.blocks]
    if document.summary is not None:
        targets.append(document.summary)
    filled = 0
    for block in targets:
        if block.source_block_ids:
            continue
        cited = list(
            dict.fromkeys(
                line_id
                for line_id in (block.source_line_ids or [])
                if line_id in valid_ids
            )
        )
        if cited:
            block.source_block_ids = cited
            filled += 1
    if filled:
        _logger.info("Backfilled raw-block citations for %d blocks.", filled)
    return filled


def audit_semantic_omissions(
    raw: RawExtraction,
    document: CVDocumentV2,
) -> list[str]:
    """Audit for high-value semantic content present in raw extraction but omitted from document."""
    warnings: list[str] = []
    raw_text = "\n".join(b.text for p in raw.pages for b in p.blocks)

    # Check email
    email_match = re.search(r"[\w\.-]+@[\w\.-]+\.\w+", raw_text)
    if email_match:
        found_email = email_match.group(0)
        doc_email = document.identity.email or ""
        if not doc_email:
            warnings.append(
                f"Email '{found_email}' present in raw extraction but missing from candidate identity."
            )

    # Check phone
    phone_match = re.search(
        r"(?:\+?\d{1,3}[-.\s]?)?\(?\d{2,4}\)?[-.\s]?\d{3,4}[-.\s]?\d{3,4}", raw_text
    )
    if phone_match:
        found_phone = phone_match.group(0)
        doc_phone = document.identity.phone or ""
        if not doc_phone and len(found_phone) >= 8:
            warnings.append(
                f"Phone '{found_phone}' present in raw extraction but missing from candidate identity."
            )

    return warnings


def reconstruct_cv_text(cv_text: str) -> CVDocumentV2:
    """Reconstruct plain extracted CV text into a typed V2 document."""
    return detect_sections(_plain_text_lines(cv_text))


def reconstruct_from_lines(lines: list[ExtractedLine]) -> CVDocumentV2:
    """Reconstruct a typed V2 document from real layout-aware lines."""
    return detect_sections(lines)


def canonical_cv_hash(cv_text: str) -> str:
    """Return a deterministic SHA-256 hash for CV text content."""
    from hashlib import sha256

    normalized = "\n".join(
        line.strip() for line in cv_text.splitlines() if line.strip()
    )
    return sha256(normalized.encode("utf-8")).hexdigest()


def _missing_provenance_is_machine_owned(doc: CVDocumentV2) -> bool:
    """Check whether a `missing_line_provenance` warning is still machine-owned.

    The warning is a block-level provenance gap lifted onto the document by
    `_finalize_diagnostics`. It stops being the machine's responsibility when:

    - no live block still carries it (the offending block was deleted or
      replaced in the review wizard — a stale doc-level lift),
    - every carrying block has `origin == USER_EDIT` (the candidate added or
      rewrote the block in review, so the candidate — not the extractor — is
      the authority for its content), or
    - the document carries any `USER_EDIT` block at all (evidence the
      candidate reviewed this exact document in the wizard and approved its
      rendered content on screen, which is the human attestation the review
      flow exists to capture).

    Returns True only for a never-reviewed document with an untouched
    (`extracted`) block still lacking provenance, which remains a genuine
    reconstruction gap. The warning itself always stays on record for audit,
    and tailoring still validates every `original_text` against live block
    content before applying a rewrite.
    """
    blocks = [block for section in doc.sections for block in section.blocks]
    if doc.summary is not None:
        blocks.append(doc.summary)
    carriers = [
        block
        for block in blocks
        if "missing_line_provenance" in (block.reconstruction_warnings or [])
    ]
    if not carriers:
        return False
    if all(block.origin == ContentOrigin.USER_EDIT for block in carriers):
        return False
    return not any(block.origin == ContentOrigin.USER_EDIT for block in blocks)


def validate_reconstruction_gate(doc: CVDocumentV2) -> None:
    """Validate that a reconstructed CV document passes structural quality gates."""
    _logger.info(
        "Evaluating CV reconstruction quality gate: sections=%d, warnings=%s",
        len(doc.sections),
        sorted(doc.reconstruction_warnings),
    )
    if doc.requires_reprocessing:
        raise ValueError(
            "CV reconstruction gate failed: document requires reprocessing."
        )
    if "semantic_parser_fallback" in set(doc.reconstruction_warnings):
        raise ValueError(
            "CV reconstruction gate failed: semantic parser fallback was used."
        )

    if doc.reconstruction_version < CURRENT_RECONSTRUCTION_VERSION:
        raise ValueError(
            "CV reconstruction gate failed: legacy reconstruction is stale and requires reprocessing."
        )

    substantive_unmapped_reasons = {
        "parser_omission",
        "unknown_section",
        "ambiguous_content",
    }
    substantive_unmapped = [
        item
        for item in doc.unmapped_content
        if item.reason in substantive_unmapped_reasons
        and any(character.isalnum() for character in item.text)
    ]
    if substantive_unmapped:
        _logger.warning(
            "CV reconstruction gate warning: substantive unmapped source content remains. Allowed to proceed."
        )

    if "unmatched_semantic_leaf" in set(doc.reconstruction_warnings):
        _logger.warning(
            "CV reconstruction gate warning: unmatched_semantic_leaf detected. Allowed to proceed."
        )

    critical_warnings = {
        "single_unknown_section_fallback",
        "duplicate_line_ownership",
        "missing_line_provenance",
        "ambiguous_entry_boundary",
        # Phase 4: source conservation warnings
        "duplicate_semantic_ownership",
        "ambiguous_source_match",
        "unknown_source_reference",
    }
    found_warnings = set(doc.reconstruction_warnings) & critical_warnings
    if "missing_line_provenance" in found_warnings and (
        doc.review_attested or not _missing_provenance_is_machine_owned(doc)
    ):
        # Provenance gap covered by human attestation: either the review
        # wizard explicitly attested this document (the candidate saw the
        # full render and clicked through), or the carrying blocks are
        # user-owned/stale (see helper). Allow passage; the warning stays
        # on record for audit.
        _logger.info(
            "CV reconstruction gate: missing_line_provenance covered by "
            "review_attested=%s; allowing.",
            doc.review_attested,
        )
        found_warnings = found_warnings - {"missing_line_provenance"}
    if found_warnings:
        _logger.warning(
            "CV reconstruction gate rejected: critical warnings %s",
            sorted(found_warnings),
        )
        raise ValueError(
            f"CV reconstruction gate failed: critical warnings detected: {sorted(found_warnings)}"
        )

    warnings_set = set(doc.reconstruction_warnings)
    if (
        "summary_ownership_excessive" in warnings_set
        and "summary_contains_embedded_headings" in warnings_set
    ):
        raise ValueError(
            "CV reconstruction gate failed: excessive summary ownership co-occurring with embedded section headings."
        )

    if (
        "summary_ownership_excessive" in warnings_set
        and "identity_candidate_unparsed" in warnings_set
    ):
        raise ValueError(
            "CV reconstruction gate failed: excessive summary ownership co-occurring with unparsed identity candidate."
        )

    if (
        "possible_unjoined_line_wrap" in warnings_set
        and "classified_section_collapse" in warnings_set
    ):
        raise ValueError(
            "CV reconstruction gate failed: line wrap issue co-occurring with section collapse."
        )

    if "column_order_mismatch" in warnings_set or "embedded_headings" in warnings_set:
        raise ValueError(
            "CV reconstruction gate failed: severe layout degradation detected (column order mismatch or embedded headings)."
        )

    coverage = (
        doc.reconstruction_diagnostics.source_coverage
        if doc.reconstruction_diagnostics
        else None
    )
    if coverage is None:
        raise ValueError(
            "CV reconstruction gate failed: source coverage diagnostics are missing."
        )
    if coverage.substantive_unmapped_character_count > 0:
        _logger.warning(
            f"CV reconstruction gate warning: {coverage.substantive_unmapped_character_count} substantive characters unmapped. Allowed to proceed."
        )
    if coverage.issues:
        if any(i.code == "unmatched_semantic_leaf" for i in coverage.issues):
            _logger.warning(
                "CV reconstruction gate warning: unmatched_semantic_leaf issue detected. Allowed to proceed."
            )
        critical_codes = {
            "duplicate_semantic_ownership",
            "ambiguous_source_match",
            "unknown_source_reference",
        }
        found_issue_codes = {i.code for i in coverage.issues} & critical_codes
        if found_issue_codes:
            raise ValueError(
                f"CV reconstruction gate failed: source coverage issues detected: {sorted(found_issue_codes)}"
            )

    if not doc.sections and not doc.unmapped_content:
        raise ValueError(
            "CV reconstruction gate failed: document contains no classified sections or unmapped content."
        )


def normalize_cv_text(cv_text: str) -> str:
    """Return the normalized source text retained with a saved version."""
    return "\n".join(
        line.normalized_text
        for line in _plain_text_lines(cv_text)
        if line.normalized_text
    )


def _plain_text_lines(cv_text: str) -> list[ExtractedLine]:
    raw_lines: list[str] = []
    for raw in cv_text.splitlines():
        if not raw.strip():
            continue

        parts = [p.strip() for p in re.split(r"\t+|\s{3,}", raw) if p.strip()]
        if len(parts) > 1 and any(classify_heading(p) is not None for p in parts):
            raw_lines.extend(parts)
        else:
            colon_match = re.match(
                r"^([A-Za-z\u00C0-\u024F\s]{3,35}):\s+(.+)$", raw.strip()
            )
            if colon_match:
                heading_candidate = colon_match.group(1).strip()
                rest_candidate = colon_match.group(2).strip()
                if classify_heading(heading_candidate) is not None:
                    raw_lines.append(heading_candidate)
                    raw_lines.append(rest_candidate)
                    continue
            raw_lines.append(raw)

    lines: list[ExtractedLine] = []
    for index, text in enumerate(raw_lines):
        line = ExtractedLine(
            text=text,
            page=0,
            x=72,
            y=float(800 - index * 14),
            width=max(len(text) * 6, 1),
            height=12,
            source_line_id=f"p1-l{index + 1}",
        )
        normalize_line(line)
        lines.append(line)
    return lines


def reconstruction_diagnostics(
    document: CVDocumentV2,
) -> CVReconstructionDiagnostics:
    confidence = {
        block.block_id: block.confidence
        for section in document.sections
        for block in section.blocks
    }
    if document.summary is not None:
        confidence[document.summary.block_id] = document.summary.confidence

    existing_diag = document.reconstruction_diagnostics
    source_coverage = existing_diag.source_coverage if existing_diag else None

    return CVReconstructionDiagnostics(
        reconstruction_version=document.reconstruction_version,
        warnings=document.reconstruction_warnings,
        block_confidence=confidence,
        source_coverage=source_coverage,
    )
