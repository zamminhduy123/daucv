# CVFit Security Audit — Fix Plan

> Created: 2026-07-07
> Status: In Progress

## Summary

| Severity | Count |
|----------|-------|
| 🔴 Critical | 6 |
| 🟠 High | 4 |
| 🟡 Medium | 5 |

## Fix Tracker

| # | Issue | Severity | Status |
|---|-------|----------|--------|
| 1 | No `.gitignore` — API keys at risk | 🔴 | Done |
| 2 | CORS wildcard + credentials | 🔴 | Done |
| 3 | No rate limiting — LLM cost DoS | 🔴 | Pending |
| 4 | No PDF size limit — OOM DoS | 🔴 | Done |
| 5 | PII in logs — data leak risk | 🔴 | Done |
| 6 | SSRF in crawler | 🔴 | Pending |
| 7 | Unused `self_clone` flag in TTS | 🟠 | Pending |
| 8 | Blind proxy — no input validation | 🟠 | Pending |
| 9 | No CSRF protection (future-proof) | 🟠 | Pending |
| 10 | `dangerouslySetInnerHTML` pattern risk | 🟠 | Pending |
| 11 | No CSP headers | 🟡 | Pending |
| 12 | Admin metrics without auth | 🟡 | Pending |
| 13 | Open redirect (theoretical) | 🟡 | Pending |
| 14 | Content-Type spoofing on upload | 🟡 | Pending |
| 15 | GA privacy concern | 🟡 | Pending |

## Changelog

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
- Rate limiting uses `slowapi` (lightweight, no external dependency)
- Log sanitization masks PII fields (email, phone, Vietnamese ID, IPv4)
- All logs are structured JSON (easy to ingest into log aggregators)
- Request IDs enable traceability across middleware and handlers
- CORS fix is environment-aware (dev vs prod)
