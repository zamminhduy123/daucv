ALTER TABLE public.tailored_cv_versions
    ADD COLUMN IF NOT EXISTS analysis_key TEXT;

CREATE UNIQUE INDEX IF NOT EXISTS idx_tailored_cv_versions_entitlement
    ON public.tailored_cv_versions(user_id, analysis_key)
    WHERE analysis_key IS NOT NULL;
