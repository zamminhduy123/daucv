import type { CanonicalCV, CVDesign, CVDocumentV2 } from "@/types";

/**
 * One-shot handoff from the /app/review wizard to /app/analyzer.
 *
 * The App Router's `router.push` only carries a URL string, so the
 * user-corrected document + minted source ticket travel through
 * sessionStorage (user-scoped key) instead of navigation state. The
 * analyzer validates the handoff against the currently selected CV and
 * clears it after a successful analysis so a stale handoff can never be
 * replayed for a different CV.
 */
export interface WizardHandoff {
  source_document_v2: CVDocumentV2;
  canonical_cv: CanonicalCV;
  source_ticket: string;
  source_cv_id: string;
  design: CVDesign;
}

const KEY_PREFIX = "dau_wizard_handoff:";

function keyFor(userId: string): string {
  return `${KEY_PREFIX}${userId}`;
}

export function storeWizardHandoff(userId: string | null, handoff: WizardHandoff): void {
  if (!userId || typeof window === "undefined") return;
  try {
    sessionStorage.setItem(keyFor(userId), JSON.stringify(handoff));
  } catch {
    // Storage full/blocked: the analyzer falls back to a fresh parse.
  }
}

export function readWizardHandoff(userId: string | null): WizardHandoff | null {
  if (!userId || typeof window === "undefined") return null;
  try {
    const raw = sessionStorage.getItem(keyFor(userId));
    if (!raw) return null;
    const parsed = JSON.parse(raw) as Partial<WizardHandoff>;
    if (
      !parsed.source_document_v2 ||
      !parsed.canonical_cv ||
      !parsed.source_ticket ||
      !parsed.source_cv_id
    ) {
      return null;
    }
    return {
      source_document_v2: parsed.source_document_v2,
      canonical_cv: parsed.canonical_cv,
      source_ticket: parsed.source_ticket,
      source_cv_id: parsed.source_cv_id,
      design: parsed.design ?? "classic_ats",
    };
  } catch {
    return null;
  }
}

export function clearWizardHandoff(userId: string | null): void {
  if (!userId || typeof window === "undefined") return;
  try {
    sessionStorage.removeItem(keyFor(userId));
  } catch {
    // Ignore storage errors; a stale handoff is revalidated by CV id.
  }
}
