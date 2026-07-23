-- Phase 9: retain reproducible source artifacts for typed CV versions.
ALTER TABLE public.tailored_cv_versions
    ADD COLUMN IF NOT EXISTS source_document_v2 JSONB DEFAULT 'null'::jsonb,
    ADD COLUMN IF NOT EXISTS source_pdf_reference TEXT,
    ADD COLUMN IF NOT EXISTS source_raw_text TEXT,
    ADD COLUMN IF NOT EXISTS source_normalized_text TEXT;

COMMENT ON COLUMN public.tailored_cv_versions.source_pdf_reference IS
    'Original upload filename; source_cv_id remains the ownership-safe database reference.';
