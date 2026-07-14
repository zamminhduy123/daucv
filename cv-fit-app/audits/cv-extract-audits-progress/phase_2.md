# Phase 2 — Backward Compatibility — Implementation Summary

**Status: Complete** (2026-07-14)

## Objective

Ensure existing V1 CVs (with `sections[].items: string[]`) continue rendering correctly alongside new V2 CVs (with typed blocks), without auto-migrating database records.

---

## Deliverables

### 1. Backend V1→V2 Adapter
**File:** `backend/app/services/cv_v1_adapter.py`

Deterministic adapter that converts `TailoredCV` → `CVDocumentV2`:
- Section classification (English + Vietnamese headings)
- Entry detection via role tokens, year patterns, dash-separated patterns
- Skill group detection (e.g. "AI/ML Research: PyTorch, ...")
- Wrapped bullet line joining
- Publication, education, and general section parsers
- Content preservation guarantee — never discards, never invents

### 2. Service Layer Integration
**File:** `backend/app/services/tailored_cv_service.py`

Added `normalize_version()`:
- V2 documents pass through unchanged
- V1 documents get V2 from adapter on-the-fly
- `document_schema_version` preserved from database
- `_tailored_version()` helper routes through normalization

### 3. Backend PDF Rendering (V2 Support)
**File:** `backend/app/services/tailored_cv_pdf.py`

Split into two rendering paths:
- `_render_v2_html()` — consumes `CVDocumentV2`, renders typed blocks (entry, bullet, paragraph, skill_group, publication, education, unknown)
- `_render_v1_html()` — original V1 rendering (positional highlighting preserved for backward compat)
- `render_tailored_cv_html()` — public entry, prefers V2, falls back to V1
- `generate_tailored_cv_pdf()` — now accepts optional `document_v2`

### 4. Frontend V1→V2 Adapter
**File:** `frontend/src/lib/cv-v1-to-v2-adapter.ts`

Mirrors backend adapter logic in TypeScript for consistent frontend rendering.

### 5. Frontend Preview (V2 Support)
**File:** `frontend/src/components/workspace/TailoredCVPreview.tsx`

- Accepts new `document_v2` prop
- When present → renders via V2 typed-block iframe renderer
- When absent → adapts V1→V2 and renders via same V2 pipeline
- V1 templates preserved but no longer used as default rendering path

### 6. History Page Update
**File:** `frontend/src/app/app/history/page.tsx`

Passes `document_v2` from the version to the preview component.

### 7. Route Fix
**File:** `backend/app/api/routes/tailored_cv.py`

PDF download route now passes `document_v2` to the renderer.

---

## Test Coverage

| File | Tests | Scope |
|------|-------|-------|
| `test_cv_v1_adapter.py` | 31 | Identity mapping, section classification, skill parsing, entry detection, conservative education parsing, deterministic IDs, wrapped bullets, summary handling, legacy field fallback, safety |
| `test_cv_version_normalization.py` | 9 | V2 passthrough, V1 adaptation and precedence, future-version rejection, empty edge cases |
| `test_routes.py` | 1 updated | PDF download mock updated with `document_v2` |
| `test_tailored_cv_pdf_v2.py` | 2 | Modeled-field preservation and explicit source-language rendering |
| `test_tailored_cv_service.py` | 2 updated/added | Full row preservation and future-version rejection |

**Verified total: 283 backend tests passing, 1 skipped**. Frontend TypeScript and scoped ESLint also pass.

---

## Design Decisions

1. **No auto-migration** — Database records are never rewritten. Adapter runs on-the-fly during rendering.
2. **`document_schema_version` preserved** — Stored version stays as-is (1 or 2); adapter provides normalized V2 view.
3. **Consistent rendering** — Both V1 and V2 use the same V2 rendering pipeline for preview and PDF.
4. **Content never discarded** — Every item from V1 sections appears in V2 output, even if classified conservatively.
5. **Backend-first adaptation** — Backend `normalize_version()` is the single source of truth; frontend adapter mirrors it for preview parity.
6. **Controlled future-version failure** — Unsupported schema versions return HTTP 409 instead of being silently interpreted as V1.
7. **Conservative education parsing** — Only institution-name-shaped legacy lines are highlighted; prose remains regular detail text.

---

## Files Changed

| File | Action |
|------|--------|
| `backend/app/services/cv_v1_adapter.py` | **Created** |
| `backend/app/services/tailored_cv_service.py` | Modified |
| `backend/app/services/tailored_cv_pdf.py` | Modified |
| `backend/app/api/routes/tailored_cv.py` | Modified |
| `backend/tests/test_cv_v1_adapter.py` | **Created** |
| `backend/tests/test_cv_version_normalization.py` | **Created** |
| `backend/tests/test_routes.py` | Modified |
| `frontend/src/lib/cv-v1-to-v2-adapter.ts` | **Created** |
| `frontend/src/components/workspace/TailoredCVPreview.tsx` | Modified |
| `frontend/src/app/app/history/page.tsx` | Modified |

---

## Next Steps

Phase 3 (Layout-aware extraction) and Phase 4 (Section detection) remain to be implemented to produce native V2 documents from PDF extraction.
