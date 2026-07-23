"""Deterministic typed CV reconstruction and diagnostics."""

from app.models.cv_document_v2 import (
    CVDocumentV2,
    CVReconstructionDiagnostics,
)
from app.services.layout_extraction import ExtractedLine, normalize_line
from app.services.section_detector import detect_sections


def reconstruct_cv_text(cv_text: str) -> CVDocumentV2:
    """Reconstruct plain extracted CV text into a typed V2 document.

    Creates synthetic layout metadata (page=0, default coordinates).
    Use ``reconstruct_from_lines`` when real layout data is available
    to preserve page numbers, column IDs, fonts, and source provenance.
    """
    return detect_sections(_plain_text_lines(cv_text))


def reconstruct_from_lines(lines: list[ExtractedLine]) -> CVDocumentV2:
    """Reconstruct a typed V2 document from real layout-aware lines.

    Preserves the full ``ExtractedLine`` metadata (page, coordinates,
    font info, column IDs, source_line_id) produced by Phase 3's
    layout-aware extraction pipeline.
    """
    return detect_sections(lines)


def canonical_cv_hash(cv_text: str) -> str:
    """Return a deterministic SHA-256 hash for CV text content.

    Strips whitespace and empty lines so raw PDF text and plain text
    extractions produce identical hashes.
    """
    from hashlib import sha256

    normalized = "\n".join(
        line.strip() for line in cv_text.splitlines() if line.strip()
    )
    return sha256(normalized.encode("utf-8")).hexdigest()


def validate_reconstruction_gate(doc: CVDocumentV2) -> None:
    """Validate that a reconstructed CV document passes structural quality gates.

    Reused in both analysis orchestration and persistence creation.
    Raises ValueError if structural defects, orphaned content, missing provenance,
    or low-confidence fallback blocks are detected.
    """
    critical_warnings = {
        "single_unknown_section_fallback",
        "duplicate_line_ownership",
        "missing_line_provenance",
        "ambiguous_entry_boundary",
    }
    found_warnings = set(doc.reconstruction_warnings) & critical_warnings
    if found_warnings:
        raise ValueError(
            f"CV reconstruction gate failed: critical warnings detected: {sorted(found_warnings)}"
        )

    if not doc.sections or all(s.type in ("custom", "unknown") for s in doc.sections):
        raise ValueError(
            "CV reconstruction gate failed: document contains no classified sections."
        )

    for section in doc.sections:
        for block in section.blocks:
            if (
                getattr(block, "type", "") in ("unknown", "custom")
                and (getattr(block, "confidence", 1.0) or 0.0) < 0.5
            ):
                raise ValueError(
                    f"CV reconstruction gate failed: low confidence unknown block in section '{section.title}'"
                )


def normalize_cv_text(cv_text: str) -> str:
    """Return the normalized source text retained with a saved version."""
    return "\n".join(
        line.normalized_text
        for line in _plain_text_lines(cv_text)
        if line.normalized_text
    )


def _plain_text_lines(cv_text: str) -> list[ExtractedLine]:
    lines: list[ExtractedLine] = []
    for index, text in enumerate(cv_text.splitlines()):
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
    return CVReconstructionDiagnostics(
        reconstruction_version=document.reconstruction_version,
        warnings=document.reconstruction_warnings,
        block_confidence=confidence,
    )
