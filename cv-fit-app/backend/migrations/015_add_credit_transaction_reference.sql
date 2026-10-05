-- Idempotency key for credit top-ups (e.g. one-click manual-payment approvals).
-- add_credits(..., reference=...) checks and inserts this inside the same
-- transaction as the balance update; the unique index is the final guard
-- against double-crediting when an approval link is clicked twice.
ALTER TABLE public.credit_transactions
    ADD COLUMN IF NOT EXISTS reference TEXT;

-- Backfill references for manual approvals recorded before this column
-- existed (their marker lives in the description as "Ref: INV_..."), so an
-- old approval link cannot be replayed after deploy. Only the earliest row per
-- marker is tagged, so historical duplicates cannot break the unique index.
WITH legacy AS (
    SELECT DISTINCT ON (ref) id, ref
    FROM (
        SELECT
            id,
            created_at,
            substring(description FROM 'Ref: (INV_[A-Za-z0-9_-]+)') AS ref
        FROM public.credit_transactions
        WHERE reference IS NULL
          AND description LIKE '%Ref: INV%'
    ) AS candidates
    WHERE ref IS NOT NULL
    ORDER BY ref, created_at, id
)
UPDATE public.credit_transactions AS t
SET reference = legacy.ref
FROM legacy
WHERE t.id = legacy.id
  AND NOT EXISTS (
      SELECT 1 FROM public.credit_transactions AS x WHERE x.reference = legacy.ref
  );

CREATE UNIQUE INDEX IF NOT EXISTS uq_credit_transactions_reference
    ON public.credit_transactions (reference);
