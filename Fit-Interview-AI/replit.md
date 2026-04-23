# CV Fit & Interview AI

## Overview

An AI-powered job application assistant for the Vietnamese market. Users upload their CV (PDF) and a Job Description. The AI quantifies the CV-JD match, rewrites the CV into a tailored version, and conducts a mock interview.

## Stack

- **Monorepo tool**: pnpm workspaces
- **Node.js version**: 24
- **Package manager**: pnpm
- **TypeScript version**: 5.9
- **API framework**: Express 5
- **Database**: PostgreSQL + Drizzle ORM (available but not currently used — app is stateless)
- **AI**: OpenAI via Replit AI Integrations (gpt-5.2, no user API key needed)
- **Frontend**: React + Vite, Tailwind CSS, shadcn/ui, wouter routing
- **Validation**: Zod (`zod/v4`), `drizzle-zod`
- **API codegen**: Orval (from OpenAPI spec)
- **Build**: esbuild (CJS bundle)

## Artifacts

- **cv-fit** (`/`) — React + Vite frontend. Main user-facing app.
- **api-server** (`/api`) — Express 5 API server with OpenAI integration.

## Features

1. **Upload Page** (`/`) — Upload CV PDF + paste Job Description → Analyze Match
2. **Results Page** (`/results`) — Match score (0-100), missing skills, tailored CV with PDF export
3. **Interview Page** (`/interview`) — Mock interview chat with AI, speech-to-text (vi-VN/en-US), "Buy Me a Coffee" modal after 5 messages

## Key Commands

- `pnpm run typecheck` — full typecheck across all packages
- `pnpm run build` — typecheck + build all packages
- `pnpm --filter @workspace/api-spec run codegen` — regenerate API hooks and Zod schemas from OpenAPI spec
- `pnpm --filter @workspace/api-server run dev` — run API server locally

## API Endpoints

- `POST /api/cv/analyze` — body: `{ cv_text, jd_text }` → `{ match_score, missing_skills, tailored_cv }`
- `POST /api/interview/chat` — body: `{ jd_text, cv_text, chat_history }` → `{ message }`

## Data Flow

1. User uploads PDF → client extracts text with pdfjs-dist
2. `cv_text` + `jd_text` sent to `/api/cv/analyze`
3. Results stored in `sessionStorage` as `analysisResult`, `cv_text`, `jd_text`
4. Results page loads from sessionStorage
5. Interview page uses sessionStorage data for each chat turn

## Notes

- The `codegen` script in `lib/api-spec/package.json` overwrites `lib/api-zod/src/index.ts` after orval runs to fix a barrel conflict
- AI Integrations use env vars: `AI_INTEGRATIONS_OPENAI_BASE_URL`, `AI_INTEGRATIONS_OPENAI_API_KEY` (auto-configured)
- No database is required for the app to function — all state is ephemeral/sessionStorage
