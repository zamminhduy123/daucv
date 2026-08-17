"use client";

import React, { createContext, useContext, useState, useEffect, useCallback, useRef } from "react";
import type { CVPipelineAnalysis, LayoutLine } from "@/types";
import { useAuth } from "./AuthContext";
import { deleteRawExtractionAPI, uploadUserCVAPI, updateActiveCVTextAPI, deactivateUserCVAPI } from "@/lib/api";
import {
  acceptRawExtractionReference,
  completeRawExtractionCleanup,
  invalidateRawExtraction,
  normalizeRawExtractionLifecycle,
  queueRawExtractionCleanup,
  type RawExtractionLifecycleState,
} from "@/lib/raw-extraction-lifecycle";

// ── Cache types ──────────────────────────────────────────────────────────────

interface WriterResult {
  subject_line: string;
  content: string;
  tips: string[];
}

interface WorkspaceCache {
  analyzerResult: CVPipelineAnalysis | null;
  interviewState: unknown;
  writerResults: Record<string, WriterResult>;
}

const EMPTY_CACHE: WorkspaceCache = {
  analyzerResult: null,
  interviewState: null,
  writerResults: {},
};

// ── Core state ───────────────────────────────────────────────────────────────

interface WorkspaceState extends RawExtractionLifecycleState {
  cvText: string;
  cvFileName: string;
  jdText: string;
  layoutData: LayoutLine[] | null;
}

interface WorkspaceContextType extends WorkspaceState {
  isLoaded: boolean;
  setCvText: (text: string) => void;
  setCvFileName: (name: string) => void;
  setJdText: (text: string) => void;
  setLayoutData: (data: LayoutLine[] | null) => void;
  updateWorkspace: (data: Partial<WorkspaceState>) => void;
  queueRawExtractionCleanupIds: (ids: string[]) => void;
  uploadFileCV: (text: string, filename: string) => Promise<void>;
  deleteActiveCV: () => Promise<void>;
  hasData: boolean;

  // Feedback modal triggers
  isFeedbackOpen: boolean;
  setFeedbackOpen: (open: boolean) => void;

  // Cache accessors
  cache: WorkspaceCache;
  setCachedAnalysis: (result: CVPipelineAnalysis) => void;
  setCachedInterview: (state: unknown) => void;
  setCachedWriter: (key: string, result: WriterResult) => void;
  clearCache: () => void;
}

const WorkspaceContext = createContext<WorkspaceContextType | null>(null);

const STORAGE_KEY = "dau_workspace";
const CACHE_KEY = "dau_workspace_cache";
const DEFAULT_CV_FILENAME = "CV của tôi";

function isPipelineAnalysis(value: unknown): value is CVPipelineAnalysis {
  if (!value || typeof value !== "object") return false;
  const candidate = value as Partial<CVPipelineAnalysis>;
  return Boolean(
    candidate.canonical_cv
      && candidate.source_document_v2
      && !candidate.source_document_v2.requires_reprocessing
      && candidate.source_ticket
      && candidate.evaluation,
  );
}

export function WorkspaceProvider({ children }: { children: React.ReactNode }) {
  const { activeCV, refreshProfile, status, userId } = useAuth();
  const [state, setState] = useState<WorkspaceState>({ cvText: "", cvFileName: DEFAULT_CV_FILENAME, jdText: "", layoutData: null, rawExtractionRef: null, pendingRawExtractionCleanupIds: [] });
  const [cache, setCache] = useState<WorkspaceCache>({ ...EMPTY_CACHE });
  const [isFeedbackOpen, setFeedbackOpen] = useState(false);
  const [isLoaded, setIsLoaded] = useState(false);
  const [loadedStorageKey, setLoadedStorageKey] = useState<string | null>(null);
  const cleanupInFlight = useRef(new Set<string>());
  const scopedStorageSuffix = userId || "anonymous";
  const stateStorageKey = `${STORAGE_KEY}:${scopedStorageSuffix}`;
  const cacheStorageKey = `${CACHE_KEY}:${scopedStorageSuffix}`;

  // Sync state from user-scoped sessionStorage when auth identity is known.
  useEffect(() => {
    if (status === "loading") {
      queueMicrotask(() => {
        setIsLoaded(false);
        setLoadedStorageKey(null);
      });
      return;
    }

    const rawState = sessionStorage.getItem(stateStorageKey);
    let nextState: WorkspaceState = { cvText: "", cvFileName: DEFAULT_CV_FILENAME, jdText: "", layoutData: null, rawExtractionRef: null, pendingRawExtractionCleanupIds: [] };
    if (rawState) {
      try {
        const parsed = JSON.parse(rawState) as Partial<WorkspaceState>;
        nextState = {
          ...nextState,
          ...parsed,
          ...normalizeRawExtractionLifecycle(parsed),
        };
      } catch {}
    }

    const rawCache = sessionStorage.getItem(cacheStorageKey);
    let nextCache: WorkspaceCache = { ...EMPTY_CACHE };
    if (rawCache) {
      try {
        const parsed = JSON.parse(rawCache) as Partial<WorkspaceCache>;
        nextCache = {
          ...nextCache,
          ...parsed,
          analyzerResult: isPipelineAnalysis(parsed.analyzerResult)
            ? parsed.analyzerResult
            : null,
        };
      } catch {}
    }

    queueMicrotask(() => {
      setState(nextState);
      setCache(nextCache);
      setIsLoaded(true);
      setLoadedStorageKey(stateStorageKey);
    });
  }, [cacheStorageKey, stateStorageKey, status]);

  // Sync workspace to sessionStorage
  useEffect(() => {
    if (!isLoaded || loadedStorageKey !== stateStorageKey) return;
    sessionStorage.setItem(stateStorageKey, JSON.stringify(state));
  }, [state, isLoaded, loadedStorageKey, stateStorageKey]);

  // Process one persisted cleanup at a time. A failure leaves the ID in
  // sessionStorage so a reload can retry without making stale raw data usable.
  useEffect(() => {
    if (!isLoaded || loadedStorageKey !== stateStorageKey) return;
    const pendingId = state.pendingRawExtractionCleanupIds[0];
    if (!pendingId) return;
    const requestKey = `${stateStorageKey}:${pendingId}`;
    if (cleanupInFlight.current.has(requestKey)) return;
    cleanupInFlight.current.add(requestKey);

    deleteRawExtractionAPI(pendingId)
      .then(() => {
        setState((current) => ({
          ...current,
          ...completeRawExtractionCleanup(current, pendingId),
        }));
      })
      .catch((cleanupError) => {
        console.error("Failed to clean up raw extraction; retry is queued:", cleanupError);
      })
      .finally(() => {
        cleanupInFlight.current.delete(requestKey);
      });
  }, [
    isLoaded,
    loadedStorageKey,
    state.pendingRawExtractionCleanupIds,
    stateStorageKey,
  ]);

  // Sync cache to sessionStorage
  useEffect(() => {
    if (!isLoaded || loadedStorageKey !== stateStorageKey) return;
    sessionStorage.setItem(cacheStorageKey, JSON.stringify(cache));
  }, [cache, isLoaded, loadedStorageKey, stateStorageKey, cacheStorageKey]);

  // Trigger feedback modal if redirect query parameter is present in URL
  useEffect(() => {
    if (typeof window !== "undefined") {
      const params = new URLSearchParams(window.location.search);
      if (params.get("feedback") === "true") {
        queueMicrotask(() => {
          setFeedbackOpen(true);
        });
        // Clean URL search parameters
        window.history.replaceState(null, "", window.location.pathname);
      }
    }
  }, []);

  // Auto-load CV from database on authentication load if local workspace is empty
  useEffect(() => {
    if (isLoaded && loadedStorageKey === stateStorageKey && status === "authenticated" && activeCV) {
      if (!state.cvText.trim()) {
        // eslint-disable-next-line react-hooks/set-state-in-effect
        setState((s) => {
          const invalidated = invalidateRawExtraction(s);
          return {
            ...s,
            ...invalidated,
            cvText: activeCV.cv_text,
            cvFileName: activeCV.cv_filename,
            layoutData: null,
          };
        });
      }
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [activeCV, isLoaded, loadedStorageKey, stateStorageKey, status]);

  // Debounced auto-save for text modifications (updates active CV in place)
  useEffect(() => {
    if (
      status !== "authenticated" ||
      !userId ||
      !isLoaded ||
      loadedStorageKey !== stateStorageKey ||
      !state.cvText.trim()
    ) {
      return;
    }

    // Prevent double-saving if local state matches the DB active CV
    if (
      activeCV &&
      state.cvText === activeCV.cv_text &&
      state.cvFileName === activeCV.cv_filename
    ) {
      return;
    }

    const timer = setTimeout(() => {
      if (activeCV) {
        // Update active CV in place
        updateActiveCVTextAPI(state.cvText, state.cvFileName)
          .then(() => refreshProfile())
          .catch((err) => console.error("Failed to auto-save active CV draft:", err));
      } else {
        // Create new active CV
        uploadUserCVAPI(state.cvText, state.cvFileName)
          .then(() => refreshProfile())
          .catch((err) => console.error("Failed to auto-save new CV:", err));
      }
    }, 1000); // 1-second debounce

    return () => clearTimeout(timer);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [state.cvText, state.cvFileName, activeCV, status, isLoaded, userId, loadedStorageKey, stateStorageKey]);

  const setCvText = useCallback((cvText: string) => {
    setState((s) => ({ ...s, cvText }));
  }, []);

  const setCvFileName = useCallback((cvFileName: string) => {
    setState((s) => ({ ...s, cvFileName }));
  }, []);

  const setJdText = useCallback((jdText: string) => setState((s) => ({ ...s, jdText })), []);

  const setLayoutData = useCallback((layoutData: LayoutLine[] | null) => {
    setState((s) => ({ ...s, layoutData }));
    setCache({ ...EMPTY_CACHE });
  }, []);

  const clearCache = useCallback(() => setCache({ ...EMPTY_CACHE }), []);

  const updateWorkspace = useCallback((data: Partial<WorkspaceState>) => {
    setState((s) => {
      let next = { ...s, ...data };
      if (data.rawExtractionRef === null) {
        next = { ...next, ...invalidateRawExtraction(s) };
      } else if (data.rawExtractionRef) {
        next = {
          ...next,
          ...acceptRawExtractionReference(s, data.rawExtractionRef),
        };
      }
      if (
        next.cvText !== s.cvText ||
        next.jdText !== s.jdText ||
        next.layoutData !== s.layoutData ||
        next.rawExtractionRef !== s.rawExtractionRef
      ) {
        setCache({ ...EMPTY_CACHE });
      }
      return next;
    });
  }, []);

  const queueRawExtractionCleanupIds = useCallback((ids: string[]) => {
    if (ids.length === 0) return;
    setState((s) => ({
      ...s,
      ...queueRawExtractionCleanup(s, ids),
    }));
  }, []);

  // Explicit new file upload save (creates a new historical row)
  const uploadFileCV = useCallback(async (text: string, filename: string) => {
    setState((s) => ({ ...s, cvText: text, cvFileName: filename }));
    if (status === "authenticated" && text.trim()) {
      try {
        await uploadUserCVAPI(text, filename);
        await refreshProfile();
      } catch (err) {
        console.error("Failed to save uploaded CV file:", err);
      }
    }
  }, [status, refreshProfile]);

  const deleteActiveCV = useCallback(async () => {
    // Invalidate immediately. The centralized queue owns deletion/retry and
    // retains the ID until the server confirms deletion or reports 404.
    setState((s) => {
      const invalidated = invalidateRawExtraction(s);
      return {
        ...s,
        ...invalidated,
        cvText: "",
        cvFileName: DEFAULT_CV_FILENAME,
        layoutData: null,
      };
    });
    setCache({ ...EMPTY_CACHE });

    if (status === "authenticated" && activeCV) {
      try {
        await deactivateUserCVAPI(activeCV.id);
        await refreshProfile();
      } catch (err) {
        console.error("Failed to delete active CV:", err);
      }
    }
  }, [status, activeCV, refreshProfile]);

  const setCachedAnalysis = useCallback(
    (result: CVPipelineAnalysis) => setCache((c) => ({ ...c, analyzerResult: result })),
    []
  );
  const setCachedInterview = useCallback(
    (interviewState: unknown) => setCache((c) => ({ ...c, interviewState })),
    []
  );
  const setCachedWriter = useCallback(
    (key: string, result: WriterResult) =>
      setCache((c) => ({ ...c, writerResults: { ...c.writerResults, [key]: result } })),
    []
  );

  const hasData = !!state.cvText.trim();

  return (
    <WorkspaceContext.Provider
      value={{
        ...state,
        isLoaded,
        setCvText,
        setCvFileName,
        setJdText,
        setLayoutData,
        updateWorkspace,
        queueRawExtractionCleanupIds,
        uploadFileCV,
        deleteActiveCV,
        hasData,
        isFeedbackOpen,
        setFeedbackOpen,
        cache,
        setCachedAnalysis,
        setCachedInterview,
        setCachedWriter,
        clearCache,
      }}
    >
      {children}
    </WorkspaceContext.Provider>
  );
}

export function useWorkspace() {
  const ctx = useContext(WorkspaceContext);
  if (!ctx) throw new Error("useWorkspace must be used within <WorkspaceProvider>");
  return ctx;
}
