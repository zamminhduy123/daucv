# Phase 1 — Introduce a versioned typed CV model

**Status:** Complete  
**Date:** 2026-07-12  
**Reference:** `audits/cv-extract-audits-07-12.md` Phase 1 (Steps 1.1–1.4)

---

## Objective

Introduce a `schema_version: 2` CV document model with typed blocks, replacing the legacy `section.items: string[]` pattern with a discriminated-union block structure. All new fields are optional — existing V1 records continue to work unchanged.

---

## New files created

| File | Purpose |
|------|---------|
| `backend/app/models/cv_document_v2.py` | Pydantic domain models for `CVDocumentV2` |
| `frontend/src/types/cv-document-v2.ts` | TypeScript types (mirrored) |
| `backend/migrations/003_add_cv_document_v2.sql` | DB migration for schema-version columns |

## Files modified

| File | Change |
|------|--------|
| `backend/app/models/responses.py` | Added `document_v2: CVDocumentV2 \| None` to `CVAnalysisLLMResponse` |
| `backend/app/schemas/tailored_cv.py` | Added `document_v2`, `document_schema_version`, `reconstruction_version`, `source_hash`, `jd_hash`, `reconstruction_warnings` to create/response schemas |
| `backend/app/services/tailored_cv_service.py` | Extended `VERSION_COLUMNS` with all new DB columns |
| `frontend/src/types/index.ts` | Re-exported all V2 types; added `document_v2` field to `TailoredCVVersion` |

---

## Schema definition

### CVDocumentV2

```ts
type CVDocumentV2 = {
  schema_version: 2;
  identity: CVIdentity;
  sections: CVSection[];
};
```

### Section types

```ts
type CVSectionType =
  | "summary"
  | "experience"
  | "projects"
  | "skills"
  | "education"
  | "publications"
  | "certifications"
  | "languages"
  | "awards"
  | "activities"
  | "custom";
```

### Typed blocks (discriminated union via `type` tag)

| Block | `type` value | Key fields |
|-------|-------------|------------|
| `CVEntryBlock` | `"entry"` | `title`, `subtitle`, `organization`, `location`, `date`, `bullets[]` |
| `CVBulletBlock` | `"bullet"` | `text` |
| `CVParagraphBlock` | `"paragraph"` | `text` |
| `CVSkillGroupBlock` | `"skill_group"` | `label`, `skills[]` |
| `CVPublicationBlock` | `"publication"` | `title`, `authors`, `venue`, `date`, `status` |
| `CVEducationBlock` | `"education"` | `institution`, `degree`, `field`, `location`, `date`, `details[]` |
| `CVUnknownBlock` | `"unknown"` | `lines[]`, `confidence` (0.0–1.0) |

Every block carries a stable `block_id` (8-char hex UUID) for LLM rewriting and validation tracking.

### Section

```ts
type CVSection = {
  id: string;
  type: CVSectionType;
  title: string;
  blocks: CVBlock[];
};
```

### Identity

```ts
type CVIdentity = {
  name: string;
  headline: string;
  contact_lines: string[];
};
```

---

## Database changes

Migration `003_add_cv_document_v2.sql` adds 6 nullable columns:

```sql
ALTER TABLE public.tailored_cv_versions
    ADD COLUMN IF NOT EXISTS document_schema_version INTEGER DEFAULT 1,
    ADD COLUMN IF NOT EXISTS reconstruction_version INTEGER DEFAULT 1,
    ADD COLUMN IF NOT EXISTS source_hash TEXT,
    ADD COLUMN IF NOT EXISTS jd_hash TEXT,
    ADD COLUMN IF NOT EXISTS document_v2 JSONB DEFAULT 'null'::jsonb,
    ADD COLUMN IF NOT EXISTS reconstruction_warnings TEXT[] DEFAULT ARRAY[]::TEXT[];
```

---

## Backward compatibility

- `document_v2` is `null` by default — legacy records render through the existing `tailored_cv` V1 path
- `document_schema_version` defaults to `1` — version-aware loading in Phase 2 will detect and adapt
- All new API fields are optional with defaults — no breaking changes to existing consumers
- `TailoredCVVersionCreate` accepts `document_v2` as optional — the pipeline backfills it; the LLM does not produce it

---

## Acceptance criteria met

- [x] Backend Pydantic models can serialize and validate `CVDocumentV2`
- [x] Frontend TypeScript types match backend schema
- [x] API request/response schemas support V2 documents
- [x] Database migration covers all new fields
- [x] TypeScript compilation passes (`npx tsc --noEmit` clean)
- [x] LLM response model includes `document_v2` field
- [x] No breaking changes to existing V1 flow

---

## Post-review fixes (2026-07-12)

The review of Phase 1 found the following issues that were fixed:

| # | Category | Issue | Files |
|---|----------|-------|-------|
| 1 | Spec | Missing `summary?: CVParagraphBlock` on `CVDocumentV2` | `cv_document_v2.py`, `cv-document-v2.ts` |
| 2 | Spec | Missing `"interests"` from `CVSectionType` | `cv_document_v2.py`, `cv-document-v2.ts` |
| 3 | Spec | Frontend `CVIdentity.name` / `headline` required, but spec says optional | `cv-document-v2.ts` |
| 4 | Standards | `CVBlock` naming inconsistent with `CVSectionType` (no `Type` suffix) | `cv_document_v2.py`, `cv-document-v2.ts`, `index.ts` |
| 5 | Standards | `TailoredCVVersion` missing 5 backend fields | `index.ts` |
| 6 | Standards | Frontend `CVAnalysisResponse` had `tailoring_entitlement` not on backend | `index.ts` |

## Next: Phase 2 — Preserve backward compatibility

- Build V1 → V2 legacy adapter
- Add version-aware loading in API and frontend
- Implement `document_schema_version` detection
- Add database schema versioning fields to API responses
