<!-- BEGIN:nextjs-agent-rules -->
# This is NOT the Next.js you know

This version has breaking changes — APIs, conventions, and file structure may all differ from your training data. Read the relevant guide in `node_modules/next/dist/docs/` before writing any code. Heed deprecation notices.
<!-- END:nextjs-agent-rules -->

## Authentication & User Session (NextAuth)

- **Authentication System:** The frontend manages authentication using **NextAuth (Auth.js)** with the Google OAuth provider.
- **Token Sharing (HS256):** Session JWT tokens are symmetrically signed using HS256 with the shared `NEXTAUTH_SECRET` inside `src/app/api/auth/[...nextauth]/route.ts`. The resulting `accessToken` is appended directly to the session object so the client can access it.
- **Route Guarding:** Access to `/app/*` (the dashboard routes) is guarded inside `src/app/app/layout.tsx`. If the user session status is `unauthenticated`, they are immediately redirected to `/login`.
- **API Fetch Helper:** All outgoing fetch calls to the Python backend MUST use the `fetchWithAuth()` wrapper from `src/lib/api.ts`. This wrapper automatically fetches the current NextAuth session and appends the `Authorization: Bearer <accessToken>` header to the request.
- **Wallet & Credits Management:** The current user's profile and credit balance are tracked dynamically inside `src/context/AuthContext.tsx`. Use the `useAuth()` hook to read `credits`, check if `creditsLoading` is active, or trigger `refreshCredits()` to update the balance.

## CV Review Workspace & Rendering Architecture

- **CV Review Route (`src/app/app/review/page.tsx`):** Workspace editor where users curate their structured CV document before analysis. Features per-section and global draft saving, unified section dropdown, and typography controls.
- **Client-Side Live Preview (`LocalCVPreview.tsx` & `cv-render-html.ts`):** Renders HTML via an isolated iframe. The iframe MUST include `sandbox="allow-scripts allow-same-origin"` so that DOM measurement (`applyPageBreaks()`) can run. Avoid inner iframe scrolling (`overflow: hidden`, `scrolling="no"`).
- **Proportional Typography & Spacing:** `buildCVHtml()` accepts `CVTypographyConfig`. Font scaling MUST use `baseFontSize` (pt) to proportionally scale H1, H2, and body without flattening hierarchy. Spacing attributes (`sectionSpacing`, `itemSpacing`, `lineHeight`, `pageMargin`) support minimum values down to `0` for precise 1-page fit.
- **Fast Document Hydration (`src/lib/document-cache.ts`):** Whenever a CV is prefilled or saved, cache its `CVDocumentV2` in `sessionStorage` via `setCachedStructuredDoc`. On entering `/app/review`, hydrate from cache first (0ms), fallback to database (`getStructuredDocumentAPI`), and only re-run prefill when missing. During loading, render `<ReviewSkeleton />` rather than raw spinners.


