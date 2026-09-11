-- Migration 013: Store pre-rendered first-page JPEG thumbnail file ID
-- so library cards can render instantly via Next.js proxy without downloading full PDFs.

ALTER TABLE public.user_cvs
    ADD COLUMN IF NOT EXISTS thumbnail_file_id TEXT NULL;
