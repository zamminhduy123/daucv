# Phase 2 Code Review

**Review target:** uncommitted Phase 2 backward-compatibility work, compared with `HEAD` (`22a03e3`)

**Original verdict:** Not ready to merge. The initial implementation broke every saved tailored-CV response path and did not compile on the frontend.

**Resolution:** Fixed and re-reviewed on 2026-07-14. No remaining standards or Phase 2 spec findings.

## Standards

### [P0] Saved tailored-CV operations fail response validation

`backend/app/services/tailored_cv_service.py:85-96` passes only `tailored_cv`, `document_v2`, and `schema_version` into `normalize_version()`. It drops the rest of the database row, but `TailoredCVVersionResponse` requires `id`, `jd_text`, `selected_design`, `created_at`, and `updated_at`.

This breaks create, list, get/download, and update-design. The targeted backend run reproduced five failures with missing-field `ValidationError`s.

### [P0] The frontend does not compile

- `frontend/src/components/workspace/TailoredCVPreview.tsx:164` and `:169` omit the closing `)` for two `.map(...)` expressions.
- `frontend/src/lib/cv-v1-to-v2-adapter.ts:108` contains an invalid regular-expression literal.

Both TypeScript and file-scoped ESLint fail at these Phase 2 lines.

### [P1] V2 renderers silently omit modeled facts

`backend/app/services/tailored_cv_pdf.py:42-84` and `frontend/src/components/workspace/TailoredCVPreview.tsx:273-300` do not render:

- entry `organization`, `location`, or `date`;
- education `field`, `location`, or `date`;
- publication `date` or `status`.

Valid native V2 CVs can therefore lose employment dates, locations, and other facts in both preview and PDF. There are no renderer tests for these fields.

### [P2] The adapter is not deterministic and its frontend output does not satisfy the V2 types

The backend model creates random `block_id` values by default on every adaptation, while the frontend adapter creates blocks without required `block_id` values and derives section IDs from the first eight title characters. This contradicts the Phase 2 summary's deterministic-adapter claim and the stable-ID requirement inherited from Phase 1. Once the syntax errors are fixed, the missing IDs should surface as further TypeScript errors.

## Spec

### [P1] The adapters discard legacy content

The Phase 2 spec says the adapter must never discard content.

- Mixed skill sections lose every loose skill whenever at least one labeled group exists: `backend/app/services/cv_v1_adapter.py:319-338` and `frontend/src/lib/cv-v1-to-v2-adapter.ts:153-165`.
- Summary-section items are skipped wholesale at `backend/app/services/cv_v1_adapter.py:241-255` and `frontend/src/lib/cv-v1-to-v2-adapter.ts:245-253`; if the top-level summary is empty or different, those lines disappear.

The current tests cover only all-group skill data and use a pre-populated summary, so neither loss case is detected.

### [P1] Future schema versions are silently accepted

The spec requires unsupported future versions to return a controlled compatibility error. `normalize_version()` has no version guard: a non-null V2 payload is returned regardless of `document_schema_version`, while a future-version row without a payload is silently adapted as V1. No compatibility error or route mapping exists, and there is no future-version test.

### [P1] Uncertain legacy content can be highlighted

The spec permits entry blocks only for clearly recognized titles and requires uncertain text to remain unhighlighted. The backend education parser wraps any nonempty education lines in `CVEntryBlock` even when no headline heuristic matched (`backend/app/services/cv_v1_adapter.py:371-388`); the renderer then bolds it. The frontend heuristic is also broader than the backend one, which creates legacy preview/PDF semantic drift.

### [P1] Preview/PDF parity is not actually guaranteed

Preview and PDF duplicate their renderers and legacy adapters rather than sharing one rendering result. The implementations already disagree on orphan bullets and section classification. In addition, the modern frontend renderer embeds the header inside `body` but still emits the original header before `body` (`frontend/src/components/workspace/TailoredCVPreview.tsx:238-270`), so the modern preview duplicates the candidate header while the backend PDF does not.

## Validation

- `frontend: npx tsc --noEmit --pretty false` — **failed** with five syntax errors in Phase 2 files.
- Frontend file-scoped ESLint — **failed** with two parsing errors.
- Targeted backend suite using `backend/venv` — **63 passed, 5 failed**; all five code failures come from dropped row metadata.
- Full backend suite — **259 passed, 1 skipped, 8 failed**. Five are the same service regressions; three PDF runtime tests were blocked by Chromium sandbox permission (`MachPortRendezvousServer ... Permission denied`) rather than an assertion failure.
- `python -m py_compile` on touched backend production files — **passed**.
- `git diff --check` — **passed**.

## Summary

- Standards: 4 findings; worst issue is the P0 saved-version response regression (alongside a separate P0 frontend compile failure).
- Spec: 4 findings; worst issue is legacy data loss despite the explicit preservation guarantee.

## Resolution validation

- Frontend TypeScript: **passed**.
- Phase 2 file-scoped ESLint: **passed**.
- Targeted Phase 2 backend tests: **84 passed**.
- Full backend suite: **283 passed, 1 skipped**.
- Real Chromium PDF runtime tests: **3 passed** outside the sandbox.
- Backend syntax validation and `git diff --check`: **passed**.
- Independent standards re-review: **no findings**.
- Independent Phase 2 spec re-review: **no findings**.
