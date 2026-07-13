-- Apply once to the production database before enabling saved tailored CVs.
CREATE TABLE IF NOT EXISTS public.tailored_cv_versions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
    source_cv_id UUID REFERENCES public.user_cvs(id) ON DELETE SET NULL,
    target_role TEXT,
    company_name TEXT,
    jd_text TEXT NOT NULL DEFAULT '',
    tailored_cv JSONB NOT NULL,
    analysis_key TEXT NOT NULL,
    selected_design TEXT NOT NULL DEFAULT 'classic_ats'
        CHECK (selected_design IN ('classic_ats', 'modern_professional', 'compact_one_page')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_tailored_cv_versions_user_created
    ON public.tailored_cv_versions(user_id, created_at DESC);
CREATE UNIQUE INDEX IF NOT EXISTS idx_tailored_cv_versions_entitlement
    ON public.tailored_cv_versions(user_id, analysis_key);
