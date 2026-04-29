import { redirect } from "next/navigation";

/**
 * Redirect /app → /app/analyzer by default.
 */
export default function AppRootPage() {
  redirect("/app/analyzer");
}
