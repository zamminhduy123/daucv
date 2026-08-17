ALTER TABLE public.tailored_cv_versions
DROP CONSTRAINT IF EXISTS tailored_cv_versions_selected_design_check;

ALTER TABLE public.tailored_cv_versions
ADD CONSTRAINT tailored_cv_versions_selected_design_check
CHECK (selected_design IN ('classic_ats', 'modern_professional', 'compact_one_page', 'compact'));

ALTER TABLE public.tailored_cv_versions
ADD COLUMN IF NOT EXISTS template_id TEXT,
ADD COLUMN IF NOT EXISTS template_version INTEGER,
ADD COLUMN IF NOT EXISTS render_version INTEGER,
ADD COLUMN IF NOT EXISTS last_render_diagnostics JSONB;

COMMENT ON COLUMN public.tailored_cv_versions.template_id IS 'Selected template identifier (e.g. classic_ats, modern_professional, compact)';
COMMENT ON COLUMN public.tailored_cv_versions.template_version IS 'Pinned immutable template version number at render time';
COMMENT ON COLUMN public.tailored_cv_versions.render_version IS 'Phase 6 renderer engine version';
COMMENT ON COLUMN public.tailored_cv_versions.last_render_diagnostics IS 'Server-generated Phase 6 render diagnostics and validation audit log';

-- Historical backfill for Phase 6 template columns
UPDATE public.tailored_cv_versions
SET template_id = CASE
    WHEN selected_design = 'modern_professional' THEN 'modern_professional'
    WHEN selected_design = 'compact_one_page' THEN 'compact'
    WHEN selected_design = 'compact' THEN 'compact'
    ELSE 'classic_ats'
END,
template_version = 1,
render_version = 1
WHERE template_id IS NULL;
