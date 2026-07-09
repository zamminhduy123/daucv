# Uncommitted Changes Review

Date: 2026-07-08

Scope: staged, unstaged, and untracked files in `cv-fit-app`.

## Summary

The current uncommitted changes add authentication, user credits, billing routes, database access, structured logging, and new frontend auth/billing UI. The overall direction is clear, but three issues should be fixed before shipping because they affect payment integrity, authentication security, and user-facing credit accuracy.

## Findings

### 1. Mock payment endpoint can grant unlimited credits

Priority: P1

File: `backend/app/api/routes/billing.py`

The new `/api/billing/mock-confirm` endpoint is included in the normal backend router and only validates client-supplied package fields against hard-coded package definitions. Any authenticated user can call this endpoint repeatedly and receive credits without a real payment confirmation.

Why it matters:

- Users can add credits without paying.
- There is no payment provider verification.
- There is no order id, transaction id, or replay protection.

Recommended fix:

- Do not expose this route in production.
- Gate it behind an explicit local-development flag, or replace it with a real payment callback that verifies a provider transaction exactly once.
- Store payment/order records so successful confirmations cannot be replayed.

## 2. Backend accepts a hard-coded fallback JWT secret

Priority: P1

File: `backend/app/core/config.py`

`NEXTAUTH_SECRET` falls back to the public string `super-secret-nextauth-key-change-in-prod`. The backend verifies bearer tokens using this secret, so any deployment missing `NEXTAUTH_SECRET` could accept forged tokens signed with the known fallback.

Why it matters:

- Missing production configuration silently becomes an authentication bypass risk.
- The same fallback also appears in the NextAuth route, making forged client/backend tokens easier to reproduce.

Recommended fix:

- Make `NEXTAUTH_SECRET` required at startup.
- Fail fast if it is missing.
- Remove the fallback from both backend config and the frontend NextAuth route.

## 3. Frontend shows fake credits when the real credit API fails

Priority: P2

File: `frontend/src/context/AuthContext.tsx`

When fetching credits fails, the frontend sets the displayed balance to `5`. This happens for any failure, including auth errors, backend failures, and database outages.

Why it matters:

- Users may see credits they do not actually have.
- The UI can say a paid action is available while the backend still rejects it.
- Production failures become harder to diagnose because the UI hides the real error state.

Recommended fix:

- Do not invent a credit balance after API failure.
- Keep `credits` as `null`, show an error/loading state, and optionally retry.
- If mock credits are needed locally, gate them behind an explicit development-only flag.

## Additional Notes

There are untracked generated or artifact-like files that may not belong in the commit:

- `backend/notebooks/voice_work.ipynb` is about 9.1 MB.
- `backend/scripts/eval_results.txt` looks like generated evaluation output.
- Several untracked backend scripts appear unrelated to the auth/billing change.

Review these before committing so accidental artifacts do not land in the repo.

## Validation

Frontend lint command:

```bash
npm run lint -- --max-warnings=0
```

Result: failed.

Notes:

- The repo has many existing lint failures.
- The new auth/billing files also introduce lint errors, especially `no-explicit-any` and React effect-rule violations.

Backend test command:

```bash
python3 -m pytest
```

Result: blocked locally.

Error:

```text
ModuleNotFoundError: No module named 'asyncpg'
```

`asyncpg` was added to `backend/requirements.txt`, but it is not installed in the current local Python environment.

## Recommended Fix Order

1. Disable or production-gate `/api/billing/mock-confirm`.
2. Remove hard-coded auth secret fallbacks and fail fast when `NEXTAUTH_SECRET` is missing.
3. Stop displaying fake credits after failed credit fetches.
4. Decide whether the untracked notebook/eval artifacts should be committed.
5. Install backend dependencies and rerun backend tests.
6. Clean up new frontend lint errors in auth/billing files.
