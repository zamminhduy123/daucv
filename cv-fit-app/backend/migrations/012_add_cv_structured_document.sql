-- Migration 012: Wizard-edited structured CV JSON per source CV row.
-- The review wizard saves the user-corrected CVDocumentV2 here so
-- evaluate/tailor can consume it without re-parsing (no LLM1 call).

ALTER TABLE public.user_cvs
    ADD COLUMN IF NOT EXISTS structured_document JSONB NULL;

ALTER TABLE public.user_cvs
    ADD COLUMN IF NOT EXISTS structured_updated_at TIMESTAMPTZ NULL;
