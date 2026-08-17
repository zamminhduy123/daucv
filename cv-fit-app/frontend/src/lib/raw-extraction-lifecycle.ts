import type { RawExtractionReference } from "../types/index.ts";

export interface RawExtractionLifecycleState {
  rawExtractionRef: RawExtractionReference | null;
  pendingRawExtractionCleanupIds: string[];
}

function uniqueIds(ids: unknown): string[] {
  if (!Array.isArray(ids)) return [];
  return Array.from(
    new Set(ids.filter((id): id is string => typeof id === "string" && id.length > 0)),
  );
}

/** Normalize persisted state, including sessions written before the cleanup queue existed. */
export function normalizeRawExtractionLifecycle(
  value: Partial<RawExtractionLifecycleState>,
): RawExtractionLifecycleState {
  const pendingRawExtractionCleanupIds = uniqueIds(
    value.pendingRawExtractionCleanupIds,
  );
  const rawExtractionRef = value.rawExtractionRef ?? null;

  // Pending cleanup is authoritative: an invalidated artifact must never become
  // analysis-eligible again because an inconsistent session snapshot was loaded.
  return {
    rawExtractionRef:
      rawExtractionRef && pendingRawExtractionCleanupIds.includes(rawExtractionRef.id)
        ? null
        : rawExtractionRef,
    pendingRawExtractionCleanupIds,
  };
}

/** Invalidate an artifact for analysis while retaining its opaque ID for cleanup. */
export function invalidateRawExtraction(
  state: RawExtractionLifecycleState,
): RawExtractionLifecycleState {
  const pendingRawExtractionCleanupIds = uniqueIds([
    ...state.pendingRawExtractionCleanupIds,
    ...(state.rawExtractionRef ? [state.rawExtractionRef.id] : []),
  ]);
  return {
    rawExtractionRef: null,
    pendingRawExtractionCleanupIds,
  };
}

/** Accept a new reference only after the server-managed replacement request succeeds. */
export function acceptRawExtractionReference(
  state: RawExtractionLifecycleState,
  rawExtractionRef: RawExtractionReference,
): RawExtractionLifecycleState {
  return {
    rawExtractionRef,
    pendingRawExtractionCleanupIds: state.pendingRawExtractionCleanupIds.filter(
      (id) => id !== rawExtractionRef.id,
    ),
  };
}

export function queueRawExtractionCleanup(
  state: RawExtractionLifecycleState,
  cleanupIds: string[],
): RawExtractionLifecycleState {
  const pendingRawExtractionCleanupIds = uniqueIds([
    ...state.pendingRawExtractionCleanupIds,
    ...cleanupIds,
  ]);
  return {
    rawExtractionRef:
      state.rawExtractionRef &&
      pendingRawExtractionCleanupIds.includes(state.rawExtractionRef.id)
        ? null
        : state.rawExtractionRef,
    pendingRawExtractionCleanupIds,
  };
}

export function completeRawExtractionCleanup(
  state: RawExtractionLifecycleState,
  deletedId: string,
): RawExtractionLifecycleState {
  return {
    ...state,
    pendingRawExtractionCleanupIds: state.pendingRawExtractionCleanupIds.filter(
      (id) => id !== deletedId,
    ),
  };
}

/**
 * Testable cleanup attempt: a rejected deletion leaves the durable queue intact;
 * successful deletion (including API-normalized 404) removes only that ID.
 */
export async function attemptNextRawExtractionCleanup(
  state: RawExtractionLifecycleState,
  deleteArtifact: (id: string) => Promise<void>,
): Promise<RawExtractionLifecycleState> {
  const pendingId = state.pendingRawExtractionCleanupIds[0];
  if (!pendingId) return state;
  await deleteArtifact(pendingId);
  return completeRawExtractionCleanup(state, pendingId);
}
