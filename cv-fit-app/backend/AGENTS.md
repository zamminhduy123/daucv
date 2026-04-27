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

- **New domain** (e.g. `summary`) → always create `schemas/summary.py`, `services/summary_service.py`, `api/v1/summary.py`. Never partial.
- **No DB yet** — use in-memory state or pass data through request/response only. Design services so a repository layer can be slotted in later without rewriting business logic.
- All LLM calls live in `services/` only — never in routers.
- Use `pydantic-settings` for config — never read `os.environ` directly.
- Type hints required on every function. No `print()` — use `logging`.
- Routers handle HTTP only. Services handle logic. Keep them separate.