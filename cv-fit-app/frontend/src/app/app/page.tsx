import { redirect } from "next/navigation";

/**
 * Redirect /app → /app/setup by default.
 */
export default function AppRootPage() {
  redirect("/app/setup");
}
