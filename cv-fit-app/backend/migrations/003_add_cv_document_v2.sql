-- Migration 003: Add CVDocumentV2 schema-version support
-- Adds nullable columns for the typed CV document (V2) and schema metadata.
-- Existing records keep their V1 JSON; document_v2 is filled by the pipeline.

ALTER TABLE public.tailored_cv_versions
    ADD COLUMN IF NOT EXISTS document_schema_version INTEGER DEFAULT 1,
    ADD COLUMN IF NOT EXISTS reconstruction_version INTEGER DEFAULT 1,
    ADD COLUMN IF NOT EXISTS source_hash TEXT,
    ADD COLUMN IF NOT EXISTS jd_hash TEXT,
    ADD COLUMN IF NOT EXISTS document_v2 JSONB DEFAULT 'null'::jsonb,
    ADD COLUMN IF NOT EXISTS reconstruction_warnings TEXT[] DEFAULT ARRAY[]::TEXT[];
