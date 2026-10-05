# CVFit Security Audit — Fix Plan

> Created: 2026-07-07
> Status: In Progress

## Summary

| Severity | Count |
|----------|-------|
| 🔴 Critical | 10 |
| 🟠 High | 7 |
| 🟡 Medium | 8 |

## Fix Tracker

| # | Issue | Severity | Status |
|---|-------|----------|--------|
| 1 | No `.gitignore` — API keys at risk | 🔴 | Done |
| 2 | CORS wildcard + credentials | 🔴 | Done |
| 3 | No rate limiting — LLM cost DoS | 🔴 | Done |
| 4 | No PDF size limit — OOM DoS | 🔴 | Done |
| 5 | PII in logs — data leak risk | 🔴 | Done |
| 6 | SSRF in crawler | 🔴 | Done (was not exploitable; allowlist added as defense in depth) |
| 7 | Unused `self_clone` flag in TTS | 🟠 | Pending |
| 8 | Blind proxy — no input validation | 🟠 | Pending |
| 9 | No CSRF protection (future-proof) | 🟠 | Pending |
| 10 | `dangerouslySetInnerHTML` pattern risk | 🟠 | Pending |
| 11 | No CSP headers | 🟡 | Pending |
| 12 | Admin metrics without auth | 🟡 | Done |
| 13 | Open redirect (theoretical) | 🟡 | Pending |
| 14 | Content-Type spoofing on upload | 🟡 | Pending |
| 15 | GA privacy concern | 🟡 | Pending |
| 16 | LLM/TTS endpoints without auth (`/api/interview/finish`, `/api/writer/generate`, `/api/interview/tts`) | 🔴 | Done |
| 17 | Unauthenticated debug endpoints leak tracebacks + DB host (`/api/billing/debug-imports`, `/debug-db`) | 🔴 | Done |
| 18 | Mock billing on by default; billing `ImportError` fallbacks define a fake `get_current_user` | 🔴 | Done |
| 19 | Unauthenticated `/api/billing/test-request` with hardcoded real identity | 🔴 | Done |
| 20 | Manual-payment approval double-credit race (dedup and credit in separate transactions) | 🟠 | Done |
| 21 | Approval links signed with `NEXTAUTH_SECRET`; unescaped values / exception text in approval HTML | 🟠 | Done |
| 22 | Raw exception text returned in 5xx responses (DB sync error, LLM errors, translation) | 🟡 | Done |
| 23 | Full CV prompts (emails, phones) written unsanitized to `logs/*-llm-inputs.jsonl` and `logs/prompts/` | 🟠 | Done |
| 24 | TTS temp files never deleted (disk fill) and unbounded TTS text | 🟡 | Done |
| 25 | Blocking sync `httpx.Client` call inside async billing route | 🟡 | Done |

## Changelog

### 2026-10-05 — Second review: remaining error/log leaks, JWT exp, render isolation

- **`backend/app/services/ai_service.py`**: when every provider fails, the 503 shown to users is generic ("All AI providers are currently overloaded. Please try again later."); it no longer appends `last_error`, which could contain the Remote-Qwen endpoint (host/IP/port) or model output. Failures are recorded via `describe_exception()` in logs and in the JSONL metrics `error_message`.
- **`backend/app/services/llm_provider.py`**: JSON-validation errors log type + raw length only; output snippets are logged (DEBUG) only with `LOG_LLM_INPUTS=true`.
- **`backend/app/services/cv_range_plan_service.py`**: `_log_section_to_file` (raw CV sections → `logs/cv_range_plan_sections.log`, range_v3 mapper only) now follows `LOG_LLM_INPUTS` and is PII-sanitized.
- **`backend/app/dependencies.py`**: backend JWTs must carry `exp` (frontend `signBackendAccessToken` already sets it).
- **`backend/app/utils/pii_sanitizer.py`**: Vietnamese phones matched in any grouping (`0912 345 678`, `091 234 5678`, `0912.345.678`, `+84 912 345 678`, 11-digit landlines).
- **`backend/app/utils/render_isolation.py`** (new) + **`cv_export_service.py`**, **`cv_render_validation.py`**: Playwright now aborts every request except `data:`/`about:` (was: only `http*`), and WYSIWYG HTML gets a `default-src 'none'` CSP meta tag so `file://` and other schemes cannot load.
- Tests: new cases in `tests/test_security_hardening.py`; `tests/test_ai_service_progress.py::test_remote_qwen_queue_has_a_deadline` now checks the timeout reason in logs instead of the 503 detail. Full suite: 978 passed, 25 failed (same pre-existing 25), 2 skipped; ruff clean.
- Patch: `audits/security-fix-2026-10-05-review2.patch`.

### 2026-10-05 — Review follow-ups to the 2026-10-04 hardening

- **`backend/app/core/config.py`**: `LOG_LLM_INPUTS` now defaults to off in every environment (an unset `ENV` counts as development, so it was on by accident in deployments without `ENV`).
- **`backend/app/utils/error_summary.py`** (new) + **`backend/app/api/routes/user.py`**: LLM/TTS failure logs use `describe_exception()` (type + ≤200-char message; pydantic `ValidationError` reported by field/type with no `input_value`). Tracebacks only at DEBUG level.
- **`backend/app/api/routes/billing.py`**: when Telegram delivery fails outside development, only `user_id`, `package_id` and `timestamp` are logged (ERROR), never the signed link. New `build_approval_url()`; **`backend/scripts/sign_approval_link.py`** (new) rebuilds the link from those three values on the server.
- **`backend/app/utils/upload_validation.py`**: accept `%PDF-` anywhere in the first 1024 bytes (as PDF readers do) instead of only at the start.
- **`backend/tests/test_security_hardening.py`**: tests updated/added for all four. Full suite: 956 passed, 25 failed (same 25 pre-existing failures), 2 skipped; ruff clean.
- Patch: `audits/security-fix-2026-10-05-followup.patch`.

### 2026-10-04 — Tasks #3, #6, #12, #14, #16–#25: Backend auth, billing and abuse hardening

- **`backend/app/api/routes/user.py`**: `/interview/finish`, `/writer/generate` and `/interview/tts` now require `Depends(get_current_user)` (401 without a valid NextAuth JWT). TTS audio is buffered in memory from `edge_tts.Communicate.stream()` instead of `NamedTemporaryFile(delete=False)`, so nothing is left on disk. LLM/TTS 5xx responses no longer echo exception text (logged server-side instead). `/upload-and-match` now does a bounded read (`PDF_MAX_SIZE + 1`) and both PDF upload routes verify the `%PDF-` header (HTTP 415 otherwise) before parsing or charging credits.
- **`backend/app/models/requests.py`**: `TTSRequest.text` capped at 3000 characters (422 above).
- **`backend/app/dependencies.py`**: New `require_admin` (authenticated user whose email is in `ADMIN_EMAILS`; empty means nobody). `get_current_user` returns a generic 500 on DB errors and logs the details. `add_credits(..., reference=...)` makes top-ups idempotent: user row lock, reference check, balance update and ledger insert happen in one transaction; a unique-index violation is mapped to `DuplicateCreditReferenceError`.
- **`backend/migrations/015_add_credit_transaction_reference.sql`** (new) + **`backend/schema.sql`**: Nullable `credit_transactions.reference` column with a unique index; backfills the earliest `Ref: INV_...` marker from existing manual approvals so old links cannot be replayed.
- **`backend/app/api/routes/billing.py`**: Removed every `ImportError` mock fallback (fake auth, fake `add_credits`, fake `Database`, fake schemas); removed `/test-request`, `/debug-imports`, `/debug-db`. Mock routes use one gate, `is_mock_billing_enabled()`. Approval verifies the HMAC, validates `user_id` as a UUID and credits via `add_credits(reference=...)`, so a double click credits once. Approval links are signed with `BILLING_APPROVAL_SECRET` (falls back to `NEXTAUTH_SECRET` with a one-time warning; link format unchanged). HTML pages and the Telegram message escape interpolated values and never include exception text. Telegram is called with `httpx.AsyncClient`; failures log only the error type (httpx errors contain the bot-token URL).
- **`backend/app/core/config.py`**: `is_mock_billing_enabled()` (needs `ALLOW_MOCK_BILLING=true` **and** `ENV=development`), `get_admin_emails()`, `BILLING_APPROVAL_SECRET`, `llm_input_logging_enabled()`, rate-limit settings.
- **`backend/app/api/routes/admin.py`**: Router-level `Depends(require_admin)` (401 anonymous, 403 non-admin).
- **`backend/app/main.py`**: Billing router imported directly (an import error no longer silently drops the billing routes).
- **`backend/app/core/rate_limit.py`** (new): In-process per-user sliding-window limiter, used as `dependencies=[Depends(rate_limit(group))]`. Groups: `llm` (upload-and-match, analyze-cv[/stream], jobs/parse-profile, interview/chat, interview/finish, writer/generate, cv/parse, cv/evaluate, cv/tailor, cv/tailor-and-save, translations POST, jobs/search), `pdf` (extract-pdf, tailored-cv `/pdf` and `/pdf-wysiwyg`), `tts`. Returns 429 with `Retry-After`. Counters are per process (N workers allow up to N× the limit).
- **`backend/app/utils/llm_logger.py`**: `log_llm_input` is a no-op unless `LOG_LLM_INPUTS` is enabled (default on only in development); when enabled, system prompt and user content go through `sanitize()` before being written.
- **`backend/app/utils/upload_validation.py`** (new): `looks_like_pdf` / `require_pdf_bytes` (allows only a BOM or whitespace before `%PDF-`).
- **`backend/app/services/job_crawler.py`**: Audit #6 finding: every fetch (Playwright `page.goto` and httpx for CareerViet/Ybox) uses a fixed `SEARCH_URLS` template; user and LLM text only lands in the query string, and scraped job and logo URLs are returned to the client, never fetched. `search_engine.py` only calls fixed Serper/Google hosts. Added `_is_allowed_fetch_url` (https plus a host allowlist derived from the templates), checked before every fetch, as defense in depth.
- **`backend/app/api/routes/cv_translation.py`**: 500 responses no longer include exception text.
- **`backend/tests/test_security_hardening.py`** (new) and **`backend/tests/test_manual_billing.py`** (updated for `AsyncClient`, `reference=` and the approval secret).
- **`backend/.env.example`**: Documented `ENV`, `ADMIN_EMAILS`, `BILLING_APPROVAL_SECRET`, `ALLOW_MOCK_BILLING`, `LOG_LLM_INPUTS`, `RATE_LIMIT_*`.

### 2026-07-07 — Task #5: PII in logs — data leak risk

- **`backend/app/utils/pii_sanitizer.py`** (new): Masks email addresses, Vietnamese/international phone numbers, Vietnamese ID cards (CCCD/CMT), and IPv4 addresses using pre-compiled regex patterns. Provides ``sanitize(value) -> str`` used by all log formatters.
- **`backend/app/core/logging_config.py`** (new): Structured JSON logging with ``JSONFormatter`` that automatically runs PII sanitization on every log message. Includes console (stderr) and rotating file handlers (daily, 50 MB, 7 backups). Silences noisy third-party loggers.
- **`backend/app/core/config.py`**: Added ``LOG_LEVEL`` from env var (default ``INFO``).
- **`backend/app/middleware/request_logger.py`** (new): Adds ``X-Request-ID`` tracking and logs method/path/status/duration — never request/response bodies, cookies, or query params. Uses ``contextvar`` to inject request_id into every structured log line.
- **`backend/app/main.py`**: Calls ``setup_logging()`` and ``setup_request_logging()`` in ``create_app()``.
- **`backend/app/services/ai_service.py`**: Replaced ``logging.warning(...)`` with ``_logger.warning(..., sanitize(last_error))`` for PII-safe structured logging.
- **`backend/app/utils/llm_logger.py`**: Sanitizes ``error_message`` before writing to JSONL. Emits structured log lines via application logger with PII sanitization.
- **`backend/.env.example`**: Documented ``LOG_LEVEL`` variable.

### 2026-07-07 — Task #2: CORS wildcard + credentials

- **`backend/app/core/config.py`**: Added `CORS_ALLOWED_ORIGINS` from env var `CORS_ALLOWED_ORIGINS` (comma-separated list). Defaults to `http://127.0.0.1:3000`.
- **`backend/app/main.py`**: Replaced `allow_origins=["*"]` with `CORS_ALLOWED_ORIGINS`. Import done lazily inside `create_app()` to avoid circular imports.
- **`backend/.env.example`**: Documented the `CORS_ALLOWED_ORIGINS` variable with dev/prod examples.

### 2026-07-07 — Task #4: No PDF size limit — OOM DoS

- **`backend/app/core/config.py`**: Added `PDF_MAX_SIZE` from env var (default 10 MB).
- **`backend/app/api/routes/user.py`**: Both `/upload-and-match` and `/extract-pdf` now check `file.size > PDF_MAX_SIZE` before reading, returning HTTP 413 if exceeded.
- **`frontend/src/components/workspace/InputSection.tsx`**: Added 10 MB client-side check in `handleFile` — rejects oversized files before upload, shows Vietnamese error message.
- **`backend/.env.example`**: Documented `PDF_MAX_SIZE`.

## Notes

- All fixes are backwards-compatible where possible
- No breaking API changes
- Rate limiting is an in-process sliding window (`app/core/rate_limit.py`, no extra dependency); it is per worker, so move it to Redis if strict global quotas are needed
- Follow-ups found on 2026-10-04: fixed on 2026-10-05 (see the second 2026-10-05 entry)
- Log sanitization masks PII fields (email, phone, Vietnamese ID, IPv4)
- All logs are structured JSON (easy to ingest into log aggregators)
- Request IDs enable traceability across middleware and handlers
- CORS fix is environment-aware (dev vs prod)
