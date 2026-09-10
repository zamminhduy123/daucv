-- Migration 010: Remember each source CV's raw extraction reference so
-- reselecting a CV restores layout-aware parsing instead of text fallback.

ALTER TABLE public.user_cvs
    ADD COLUMN IF NOT EXISTS raw_extraction_ref TEXT NULL;
