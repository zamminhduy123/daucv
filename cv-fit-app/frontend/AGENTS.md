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

