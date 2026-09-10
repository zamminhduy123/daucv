import type { CVDocumentV2 } from "@/types";

const CACHE_PREFIX = "dau_doc_cache";

function getStorageKey(cvId: string, userId?: string | null): string {
  const scope = userId || "anonymous";
  return `${CACHE_PREFIX}:${scope}:${cvId}`;
}

/**
 * Retrieve a cached structured document for a specific CV ID from sessionStorage.
 * Synchronous and returns immediately (0ms).
 */
export function getCachedStructuredDoc(
  cvId: string | null | undefined,
  userId?: string | null,
): CVDocumentV2 | null {
  if (typeof window === "undefined" || !cvId) return null;
  try {
    const raw = sessionStorage.getItem(getStorageKey(cvId, userId));
    if (!raw) return null;
    const parsed = JSON.parse(raw) as Partial<CVDocumentV2>;
    if (!parsed || typeof parsed !== "object" || !Array.isArray(parsed.sections)) {
      return null;
    }
    return parsed as CVDocumentV2;
  } catch {
    return null;
  }
}

/**
 * Persist a structured document into sessionStorage for quick instant hydration.
 */
export function setCachedStructuredDoc(
  cvId: string | null | undefined,
  doc: CVDocumentV2 | null | undefined,
  userId?: string | null,
): void {
  if (typeof window === "undefined" || !cvId || !doc) return;
  try {
    sessionStorage.setItem(getStorageKey(cvId, userId), JSON.stringify(doc));
  } catch (err) {
    console.warn("Failed to set structured document in sessionStorage:", err);
  }
}

/**
 * Remove a cached document when a CV is deleted or explicitly reset.
 */
export function clearCachedStructuredDoc(
  cvId: string | null | undefined,
  userId?: string | null,
): void {
  if (typeof window === "undefined" || !cvId) return;
  try {
    sessionStorage.removeItem(getStorageKey(cvId, userId));
  } catch {}
}
