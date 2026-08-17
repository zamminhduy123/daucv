-- SQL schema for CVFit Monetization & Credit Wallet System
-- Execute this script in your Supabase SQL Editor.

-- Drop tables if they exist (for cleanup if needed, run carefully)
-- DROP TABLE IF EXISTS public.credit_transactions;
-- DROP TABLE IF EXISTS public.users;

-- Create users table to store profiles and credit balances
CREATE TABLE IF NOT EXISTS public.users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email TEXT UNIQUE NOT NULL,
    name TEXT,
    image TEXT, -- Avatar URL from Google
    credits INTEGER NOT NULL DEFAULT 20,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Index on email for fast user lookup
CREATE INDEX IF NOT EXISTS idx_users_email ON public.users(email);

-- Create credit transactions ledger for auditing credit additions/subtractions
CREATE TABLE IF NOT EXISTS public.credit_transactions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
    amount INTEGER NOT NULL, -- e.g., +10 (purchase), -1 (use)
    type TEXT NOT NULL,      -- 'signup_bonus', 'purchase', 'cv_analysis', 'mock_interview'
    description TEXT,        -- detail, e.g., "CV Analysis for resume.pdf" or "Bought Starter Pack"
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Index on user_id for faster transaction history lookups
CREATE INDEX IF NOT EXISTS idx_credit_transactions_user_id ON public.credit_transactions(user_id);

-- Create user_cvs table to store historical resume plain text uploads
CREATE TABLE IF NOT EXISTS public.user_cvs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
    cv_text TEXT NOT NULL,
    cv_filename VARCHAR(255) NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Index on user_id and is_active for faster lookups
CREATE INDEX IF NOT EXISTS idx_user_cvs_user_id ON public.user_cvs(user_id);
CREATE UNIQUE INDEX IF NOT EXISTS idx_user_cvs_active_unique ON public.user_cvs(user_id) WHERE is_active = TRUE;

CREATE TABLE IF NOT EXISTS public.tailored_cv_versions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
    source_cv_id UUID REFERENCES public.user_cvs(id) ON DELETE SET NULL,
    target_role TEXT,
    company_name TEXT,
    jd_text TEXT NOT NULL DEFAULT '',
    tailored_cv JSONB NOT NULL,
    analysis_key TEXT NOT NULL,
    selected_design TEXT NOT NULL DEFAULT 'classic_ats' CHECK (selected_design IN ('classic_ats', 'modern_professional', 'compact_one_page', 'compact')),
    document_schema_version INTEGER DEFAULT 1,
    reconstruction_version INTEGER DEFAULT 1,
    source_hash TEXT,
    jd_hash TEXT,
    document_v2 JSONB DEFAULT 'null'::jsonb,
    reconstruction_warnings TEXT[] DEFAULT ARRAY[]::TEXT[],
    source_document_v2 JSONB DEFAULT 'null'::jsonb,
    tailoring_diagnostics JSONB,
    template_id TEXT,
    template_version INTEGER,
    render_version INTEGER,
    last_render_diagnostics JSONB,
    source_pdf_reference TEXT,
    source_raw_text TEXT,
    source_normalized_text TEXT,
    tailoring_pipeline_version INTEGER NOT NULL DEFAULT 1,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_tailored_cv_versions_user_created ON public.tailored_cv_versions(user_id, created_at DESC);
CREATE UNIQUE INDEX IF NOT EXISTS idx_tailored_cv_versions_entitlement ON public.tailored_cv_versions(user_id, analysis_key);

-- Create files table to store provider-neutral metadata for user files
CREATE TABLE IF NOT EXISTS public.files (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
    bucket VARCHAR(255) NOT NULL,
    object_path TEXT NOT NULL,
    original_filename VARCHAR(255) NOT NULL,
    content_type VARCHAR(100) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_files_user_id ON public.files(user_id);
CREATE UNIQUE INDEX IF NOT EXISTS idx_files_bucket_path ON public.files(bucket, object_path);

-- Create cv_translation_variants table
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

