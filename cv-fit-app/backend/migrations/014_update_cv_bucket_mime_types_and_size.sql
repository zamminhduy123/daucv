-- Allow image/jpeg and image/webp for pre-rendered thumbnails and increase file_size_limit to 10MB (matching PDF_MAX_SIZE)
UPDATE storage.buckets
SET file_size_limit = 10485760,
    allowed_mime_types = ARRAY['application/pdf', 'image/jpeg', 'image/webp', 'application/vnd.daucv.raw-extraction+json']
WHERE id = 'cv';
