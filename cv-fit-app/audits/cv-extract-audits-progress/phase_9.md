# Phase 9 — API and persistence

**Status:** Completed and reviewed (uncommitted)  
**Implementation date:** 2026-07-16  
**Reference:** `audits/cv-extract-audits-07-12.md` Phase 9 (Steps 9.1–9.4)

## Outcome

The analysis endpoint now returns an explicit envelope separating analysis,
typed tailored content, typed source content, diagnostics, legacy compatibility,
and the one-time persistence entitlement. New saved versions retain the complete
reconstruction inputs and metadata required for reproducible rendering.

## Implemented behavior

- `/api/analyze-cv` returns `analysis`, typed `tailored_cv`,
  `source_document_v2`, `reconstruction_diagnostics`, `legacy_tailored_cv`, and
  `tailoring_entitlement` as distinct fields.
- The frontend API adapter normalizes the envelope for the existing analyzer UI.
- Migration `004_preserve_cv_reconstruction_sources.sql` adds the original PDF
  reference, raw text, normalized text, and typed source document.
- Saved V2 versions retain schema/reconstruction versions, typed source and
  tailored documents, source/JD hashes, warnings, selected design, and timestamps.
- New V2 saves fail explicitly with HTTP 503 when required migrations are absent;
  they never silently drop reconstruction metadata. Historical V1 reads retain a
  compatibility adapter.
- Design updates modify only `selected_design` and do not rerun reconstruction or
  tailoring.
- Persistence assembly uses a typed record boundary rather than an unlabelled
  positional argument tuple.

## Validation

- API schema contract and route validation tests pass.
- Persistence tests cover V2 artifacts, client-document distrust, replayed
  entitlements, legacy reads, missing migrations, and content-neutral design
  switching.
- Scoped Ruff, Python compilation, frontend TypeScript, and ESLint pass.
- Full backend suite: **553 passed, 1 skipped**.
- Production Next.js build completes successfully.

## Acceptance criteria

- [x] Analysis and typed content are separate response fields.
- [x] Reconstruction metadata and complete source material are retained.
- [x] Missing migrations cannot silently produce incomplete V2 records.
- [x] Historical V1 records remain readable through version-aware normalization.
- [x] Design switching changes presentation only.

No commit was created.
