# Phase 7 — Safe LLM tailoring

**Status:** Completed and reviewed (uncommitted)  
**Implementation date:** 2026-07-16  
**Reference:** `audits/cv-extract-audits-07-12.md` Phase 7 (Steps 7.1–7.5)

## Outcome

Deterministic reconstruction now runs before the LLM. The LLM receives a typed,
stable-ID rewrite surface and may change only summary text, existing bullet text,
or skill order. Each proposed block rewrite is independently validated; an
invalid rewrite restores the original block and records a warning without
discarding the rest of the CV.

## Implemented behavior

- The prompt includes the authoritative typed source document after deterministic
  reconstruction.
- LLM rewrites reference existing `block_id` values.
- Duplicate, missing, and unknown IDs are detected.
- Identity, sections, block types, dates, organizations, institutions, entry
  counts, bullet counts, and skill membership are immutable.
- New numbers, technologies, named entities, and unsupported claim terms are
  rejected against the source CV.
- Successful edits retain both `original_values` and `tailored_values`.
- Save-time validation reconstructs the source on the server and does not trust a
  client-supplied source document or tailored structure.

## Validation

- Safe rewrite, unsupported fact, unsupported prose, structural mutation, and
  partial-recovery regressions pass.
- Persistence tests verify that client document overrides are ignored or restored.
- Full backend suite: **553 passed, 1 skipped**.
- Scoped Ruff and Python compilation pass.

## Acceptance criteria

- [x] Reconstruction and rewriting are separate stages.
- [x] Rewrites use stable block IDs and a restricted mutation surface.
- [x] Original and tailored values are retained.
- [x] Unsupported facts and structural changes restore the affected source block.
- [x] One rejected block does not prevent a usable tailored CV.

No commit was created.
