# Phase 6 — Confidence and diagnostics

**Status:** Completed and reviewed (uncommitted)  
**Implementation date:** 2026-07-16  
**Reference:** `audits/cv-extract-audits-07-12.md` Phase 6 (Steps 6.1–6.3)

## Outcome

Reconstruction decisions are now observable. Every typed block carries a stable
ID, confidence, source-line provenance, block-level warnings, and original versus
tailored values. The document separately aggregates reconstruction warnings and
the analysis API returns a typed diagnostics object.

## Implemented behavior

- `CVBlockBase` supplies `block_id`, `confidence`, `source_line_ids`,
  `reconstruction_warnings`, `original_values`, and `tailored_values`.
- Plain-text extraction assigns stable `pN-lN` source-line IDs.
- Block and section IDs are content-derived and deterministic.
- High-confidence blocks use full semantic rendering; medium-confidence inferred
  blocks render neutrally; low-confidence content remains a visible `unknown`
  block.
- Warnings cover unknown sections, incomplete reconstruction, possible line-wrap
  problems, and possible column-order problems.
- `CVReconstructionDiagnostics` keeps technical warnings and per-block confidence
  separate from the main analysis fields.

## Validation

- Reconstruction diagnostics and deterministic-ID unit tests pass.
- Full backend suite: **553 passed, 1 skipped**.
- Scoped Ruff and Python compilation pass.

## Acceptance criteria

- [x] Confidence and provenance are attached to inferred blocks.
- [x] Confidence changes formatting conservatively without hiding content.
- [x] Reconstruction warnings are retained and returned as diagnostics.
- [x] Failures are observable rather than expressed as unexplained bolding.

No commit was created.
