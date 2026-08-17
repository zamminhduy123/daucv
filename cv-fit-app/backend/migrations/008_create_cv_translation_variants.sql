-- Migration 008: Add tailoring_pipeline_version column and create cv_translation_variants table

ALTER TABLE public.tailored_cv_versions
    ADD COLUMN IF NOT EXISTS tailoring_pipeline_version INTEGER NOT NULL DEFAULT 1;

UPDATE public.tailored_cv_versions
SET tailoring_pipeline_version = 3
WHERE document_v2 IS NOT NULL
  AND source_document_v2 IS NOT NULL
  AND tailoring_diagnostics IS NOT NULL
  AND tailoring_pipeline_version < 3;

CREATE TABLE IF NOT EXISTS public.cv_translation_variants (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
    tailored_cv_version_id UUID NOT NULL REFERENCES public.tailored_cv_versions(id) ON DELETE CASCADE,
    source_document_hash TEXT NOT NULL,
    translated_document_hash TEXT NOT NULL,
    source_language VARCHAR(10) NOT NULL,
    target_language VARCHAR(10) NOT NULL,
    translation_version INTEGER NOT NULL DEFAULT 1,
    translator_version VARCHAR(50) NOT NULL DEFAULT 'v1_llm_constrained',
    status VARCHAR(20) NOT NULL DEFAULT 'pending',
    operation_id VARCHAR(64) NOT NULL,
    translated_document JSONB NOT NULL,
    translation_diagnostics JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_translation_variant UNIQUE (user_id, tailored_cv_version_id, source_document_hash, target_language, translation_version)
);

CREATE INDEX IF NOT EXISTS idx_translation_variants_version ON public.cv_translation_variants(tailored_cv_version_id);
CREATE INDEX IF NOT EXISTS idx_translation_variants_op ON public.cv_translation_variants(operation_id);
