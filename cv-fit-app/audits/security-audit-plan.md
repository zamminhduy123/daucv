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
| 5 | PII in logs — data leak risk | 🔴 | Pending |
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
- Log sanitization masks PII fields
- CORS fix is environment-aware (dev vs prod)
