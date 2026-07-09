# Agent Guidelines — FastAPI MVP

> Read this before every task. Follow exactly.

## Folder Structure

```
app/
├── main.py          # FastAPI app, route registration
├── config.py        # Settings via pydantic-settings (reads .env)
├── dependencies.py  # Shared Depends() functions
├── schemas/         # Pydantic request/response models (one file per domain)
├── services/        # Business logic + LLM calls (one file per domain)
└── api/             # Routers (one file per domain)
    └── v1/
tests/
.env                 # Never commit
.env.example         # Commit this instead
```

## Rules

- **New domain** (e.g. `summary`) → always create `schemas/summary.py`, `services/summary_service.py`, `api/routes/summary.py`. Never partial.
- **Database Integration:** Connect to Supabase PostgreSQL using `app.core.db.Database` async pool. All transactions affecting credits MUST be run transactionally (`async with conn.transaction()`) to prevent race conditions or double deductions.
- **Authentication & Security:** Secure all user endpoints using `Depends(get_current_user)` or `Depends(verify_credits(N))`.
- **JWT Handling:** Symmetrically verify frontend NextAuth JWT sessions using `pyjwt` with the shared `NEXTAUTH_SECRET` (HS256).
- All LLM calls live in `services/` only — never in routers.
- Use environment variables (via `os.getenv` or pydantic config) for settings — never hardcode secrets.
- Type hints required on every function. No `print()` — use `logging`.
- Routers handle HTTP only. Services handle logic. Keep them separate.