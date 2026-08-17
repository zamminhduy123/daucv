ALTER TABLE public.tailored_cv_versions
ADD COLUMN IF NOT EXISTS tailoring_diagnostics JSONB;

COMMENT ON COLUMN public.tailored_cv_versions.tailoring_diagnostics IS
'Server-owned Phase 5 rewrite decisions bound into V3 tailoring entitlements.';
