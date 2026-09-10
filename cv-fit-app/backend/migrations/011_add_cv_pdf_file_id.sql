-- Migration 011: Remember each source CV's uploaded PDF file so the library
-- can render first-page thumbnails and clean the PDF up on CV delete.

ALTER TABLE public.user_cvs
    ADD COLUMN IF NOT EXISTS pdf_file_id TEXT NULL;
