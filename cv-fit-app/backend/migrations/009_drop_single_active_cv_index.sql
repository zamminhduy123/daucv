-- Migration 009: Retire the single-active-CV contract for the multi-CV switcher.
--
-- New uploads coexist as plain rows (is_active = FALSE) instead of
-- deactivating priors, and selection is client-side per request. The legacy
-- active row keeps working for old clients until they migrate.
--
-- NOTE: plain DROP INDEX (not CONCURRENTLY): the migration runner applies
-- each file inside a transaction block, where CONCURRENTLY is forbidden.
-- Dropping an unused partial unique index only needs a brief lock.

DROP INDEX IF EXISTS public.idx_user_cvs_active_unique;
