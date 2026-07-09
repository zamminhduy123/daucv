# Active CV Persistence Review

Date: 2026-07-08

Scope: current working-tree changes for active CV persistence, including backend user CV endpoints, frontend API wrappers, `AuthContext`, `WorkspaceContext`, setup UI integration, and related tests.

Fixed point: `HEAD` for the working tree.

Spec source: user-provided implementation summary:

- `GET /api/user/profile`: fetch detailed profile statistics including the currently active CV.
- `GET /api/user/cvs`: list all historical uploads ordered by date.
- `POST /api/user/cv`: persist a new active CV, deactivating previous ones transactionally.
- `DELETE /api/user/cv/{cv_id}`: set `is_active = FALSE` to clear it from the active workspace but preserve historical text.
- Frontend auto-loads the database CV, auto-saves new file uploads or text changes, exposes `deleteActiveCV()`, and setup UI immediately deactivates cleared CV profiles.

## Standards

### Finding 1: New route handlers contain business/database logic directly

Priority: P2

Files:

- `backend/app/api/routes/user.py`
- `backend/AGENTS.md`

`backend/AGENTS.md` says: "Routers handle HTTP only. Services handle logic. Keep them separate." The new active-CV handlers perform raw SQL queries, transaction orchestration, row mapping, and persistence decisions directly inside `user.py`.

Why it matters:

- The router is now harder to test without broad database mocks.
- The active-CV persistence rules are coupled to HTTP handlers instead of a focused service.
- Future code paths that need active-CV behavior will likely duplicate SQL or bypass rules.

Recommended fix:

- Move active-CV operations into a user/profile service module, for example `app/services/user_cv_service.py`.
- Keep route handlers thin: validate auth/input, call the service, return schemas.

### Finding 2: New backend functions lack explicit return type annotations

Priority: P3

File: `backend/app/api/routes/user.py`

`backend/AGENTS.md` says: "Type hints required on every function." The new handlers `get_user_credits`, `get_user_profile`, `list_user_cvs`, `upload_user_cv`, and `deactivate_user_cv` do not declare return types.

Recommended fix:

- Add explicit return annotations, such as `-> UserProfileResponse`, `-> CVListResponse`, `-> CVResponse`, and a small response schema for delete success.

### Validation Notes

`git diff --check` fails on the new active-CV hunks because of trailing whitespace in `backend/app/api/routes/user.py` and a final blank line issue in `backend/tests/test_routes.py`.

Focused frontend lint also fails on the touched active-CV files because of `any` types and React effect-rule violations. TypeScript compilation does pass.

## Spec

### Finding 1: Concurrent CV saves can leave multiple active CVs

Priority: P1

Files:

- `backend/app/api/routes/user.py`
- `backend/schema.sql`

The `POST /api/user/cv` handler deactivates previous rows and inserts a new active row inside a transaction. However, the schema only adds a non-unique partial index on active rows:

- `CREATE INDEX IF NOT EXISTS idx_user_cvs_active ON public.user_cvs(user_id) WHERE is_active = TRUE;`

Two concurrent saves for the same user can both run the "deactivate all" update and then both insert active rows, leaving more than one `is_active = TRUE` CV. This breaks the requirement that the endpoint persists "a new active CV" while deactivating previous ones.

Recommended fix:

- Add a partial unique index: `CREATE UNIQUE INDEX ... ON public.user_cvs(user_id) WHERE is_active = TRUE`.
- Or lock the user's row before deactivating/inserting.
- Keep the unique index anyway as the final database invariant.

### Finding 2: Text auto-save creates a new historical row for every edit

Priority: P2

Files:

- `frontend/src/context/WorkspaceContext.tsx`
- `frontend/src/components/workspace/InputSection.tsx`
- `backend/app/api/routes/user.py`

The CV textarea calls `onChange({ cvText: e.target.value })` on every keystroke. `WorkspaceContext.updateWorkspace()` calls `uploadUserCVAPI()` whenever `data.cvText` is present. The backend endpoint always deactivates old CV rows and inserts a new active row.

Result: typing or pasting edits can produce many "historical uploads" that are not real uploads. That makes `GET /api/user/cvs` noisy and can also increase database writes sharply.

Recommended fix:

- Debounce text auto-save and update the current active CV row instead of inserting a new historical upload each time.
- Reserve new historical rows for explicit new file uploads or explicit save events.
- Consider separate `PATCH /api/user/cv/{id}` for draft/text updates.

### Finding 3: Profile endpoint does not return detailed profile statistics

Priority: P3

File: `backend/app/api/routes/user.py`

The spec says `GET /api/user/profile` fetches "detailed profile statistics including the user's currently active CV." The current response includes identity fields, credits, and `active_cv`, but no profile statistics such as CV count, active CV age, total analyses, or total credits used.

Recommended fix:

- Either add the intended stats to `UserProfileResponse`, or narrow the requirement/endpoint name to "profile with active CV" if stats are intentionally out of scope.

## Verification

Commands run:

```bash
python3 -m pytest
```

Result: blocked locally.

```text
ModuleNotFoundError: No module named 'asyncpg'
```

```bash
npx tsc --noEmit --pretty false
```

Result: passed.

```bash
npm run lint -- --max-warnings=0 src/context/AuthContext.tsx src/context/WorkspaceContext.tsx src/app/app/setup/page.tsx src/lib/api.ts
```

Result: failed with 14 errors and 2 warnings.

```bash
git diff --check -- backend/app/api/routes/user.py backend/app/schemas/user.py backend/tests/test_routes.py backend/tests/conftest.py frontend/src/lib/api.ts frontend/src/context/AuthContext.tsx frontend/src/context/WorkspaceContext.tsx frontend/src/app/app/setup/page.tsx
```

Result: failed due to whitespace in `backend/app/api/routes/user.py` and `backend/tests/test_routes.py`.

## Summary

Standards findings: 2. Worst standards issue: active-CV persistence logic lives directly in route handlers despite the repo rule to keep routers HTTP-only.

Spec findings: 3. Worst spec issue: concurrent saves can leave multiple active CV rows because the database does not enforce one active CV per user.
