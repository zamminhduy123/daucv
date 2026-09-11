"use client";

import React, { createContext, useContext, useState, useEffect, useCallback, useRef } from "react";
import type { CVPipelineAnalysis, LayoutLine, RawExtractionReference, UserCV } from "@/types";
import { useAuth } from "./AuthContext";
import { deleteRawExtractionAPI, uploadUserCVAPI, updateUserCVAPI, deleteUserCVAPI, listUserCVsAPI } from "@/lib/api";
import { apiErrorMessage, connectivityMessage, formatCaughtError } from "@/lib/errorMessages";
import {
  acceptRawExtractionReference,
  completeRawExtractionCleanup,
  invalidateRawExtraction,
  normalizeRawExtractionLifecycle,
  queueRawExtractionCleanup,
  type RawExtractionLifecycleState,
} from "@/lib/raw-extraction-lifecycle";
import { clearCachedStructuredDoc } from "@/lib/document-cache";

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
  jdFileName: string | null;
  layoutData: LayoutLine[] | null;
  // Explicitly selected source CV (multi-CV switcher). Null means none
  // selected — there is no implicit "active CV" anymore.
  selectedCvId: string | null;
}

interface WorkspaceContextType extends WorkspaceState {
  isLoaded: boolean;
  cvList: UserCV[];
  isCvListLoading: boolean;
  cvListError: string | null;
  setCvText: (text: string) => void;
  setCvFileName: (name: string) => void;
  setJdText: (text: string) => void;
  setLayoutData: (data: LayoutLine[] | null) => void;
  updateWorkspace: (data: Partial<WorkspaceState>) => void;
  queueRawExtractionCleanupIds: (ids: string[]) => void;
  refreshCvList: () => Promise<void>;
  selectCV: (id: string) => void;
  clearSelection: () => void;
  uploadFileCV: (text: string, filename: string, rawExtractionRef?: RawExtractionReference | null, pdfFileId?: string | null, thumbnailFileId?: string | null) => Promise<UserCV | null>;
  deleteCV: (id: string) => Promise<void>;
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
  const { refreshProfile, status, userId } = useAuth();
  const [state, setState] = useState<WorkspaceState>({ cvText: "", cvFileName: DEFAULT_CV_FILENAME, jdText: "", jdFileName: null, layoutData: null, rawExtractionRef: null, pendingRawExtractionCleanupIds: [], selectedCvId: null });
  const [cvList, setCvList] = useState<UserCV[]>([]);
  const [isCvListLoading, setIsCvListLoading] = useState(true);
  const [cvListError, setCvListError] = useState<string | null>(null);
  const [cache, setCache] = useState<WorkspaceCache>({ ...EMPTY_CACHE });
  const [isFeedbackOpen, setFeedbackOpen] = useState(false);
  const [isLoaded, setIsLoaded] = useState(false);
  const [loadedStorageKey, setLoadedStorageKey] = useState<string | null>(null);
  const cleanupInFlight = useRef(new Set<string>());
  const cvListRef = useRef<UserCV[]>([]);
  const stateRef = useRef(state);
  useEffect(() => {
    cvListRef.current = cvList;
  }, [cvList]);
  useEffect(() => {
    stateRef.current = state;
  }, [state]);
  const lastSavedCV = useRef<{ id?: string; text: string; filename: string } | null>(null);
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
    let nextState: WorkspaceState = { cvText: "", cvFileName: DEFAULT_CV_FILENAME, jdText: "", jdFileName: null, layoutData: null, rawExtractionRef: null, pendingRawExtractionCleanupIds: [], selectedCvId: null };
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

  const refreshCvList = useCallback(async () => {
    if (status !== "authenticated") {
      setCvList([]);
      setCvListError(null);
      return;
    }
    setIsCvListLoading(true);
    setCvListError(null);
    try {
      const res = await listUserCVsAPI();
      setCvList(res.cvs ?? []);
    } catch (err) {
      console.error("Failed to load CV list:", formatCaughtError(err));
      setCvList([]);
      setCvListError(apiErrorMessage(err));
    } finally {
      setIsCvListLoading(false);
    }
  }, [status]);

  // Load the CV list once authentication is ready. Nothing is auto-selected:
  // the user picks a CV explicitly (strict no-active rule).
  useEffect(() => {
    if (!isLoaded || loadedStorageKey !== stateStorageKey) return;
    if (status !== "authenticated") {
      queueMicrotask(() => {
        setCvList([]);
        setCvListError(null);
        setIsCvListLoading(false);
      });
      return;
    }
    listUserCVsAPI()
      .then((res) => {
        setCvList(res.cvs ?? []);
        setCvListError(null);
        setIsCvListLoading(false);
      })
      .catch((err) => {
        console.error("Failed to load CV list:", formatCaughtError(err));
        setCvList([]);
        setCvListError(apiErrorMessage(err));
        setIsCvListLoading(false);
      });
  }, [isLoaded, loadedStorageKey, stateStorageKey, status]);

  // Debounced save for text modifications (create-or-update the selected CV)
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

    // Prevent double-saving if local state has already been persisted.
    // A marker without id means an upload for exactly this content is in
    // flight (set synchronously by uploadFileCV) — the POST itself is the
    // save, so the timer must stand down regardless of selection.
    const saved = lastSavedCV.current;
    if (
      saved?.text === state.cvText &&
      saved?.filename === state.cvFileName &&
      (saved.id === undefined || saved.id === (state.selectedCvId ?? undefined))
    ) {
      return;
    }

    const timer = setTimeout(() => {
      const textToSave = state.cvText;
      const fileToSave = state.cvFileName;
      const selectedId = state.selectedCvId;
      const rawRefId = state.rawExtractionRef?.id;
      const save = selectedId
        // Update the explicitly selected CV in place
        ? updateUserCVAPI(selectedId, textToSave, fileToSave, rawRefId)
        // No selection yet: first save creates the row and selects it
        : uploadUserCVAPI(textToSave, fileToSave, rawRefId);
      save
        .then((row) => {
          lastSavedCV.current = { id: row.id, text: textToSave, filename: fileToSave };
          setState((s) => ({ ...s, selectedCvId: row.id }));
          return refreshProfile(true);
        })
        .then(() => refreshCvList())
        .catch((err) => {
          // Surfaces quota/cap rejections (e.g. 10-CV limit) on the picker.
          console.error("Failed to auto-save CV draft:", formatCaughtError(err));
          setCvListError(connectivityMessage(err));
        });
    }, 1500); // 1.5-second debounce

    return () => clearTimeout(timer);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [state.cvText, state.cvFileName, state.selectedCvId, status, isLoaded, userId, loadedStorageKey, stateStorageKey]);

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

  const selectCV = useCallback((id: string) => {
    const row = cvListRef.current.find((cv) => cv.id === id);
    setCache({ ...EMPTY_CACHE });
    if (!row) {
      setState((s) => ({ ...s, selectedCvId: id }));
      return;
    }
    lastSavedCV.current = { id: row.id, text: row.cv_text, filename: row.cv_filename };
    setState((s) => ({
      ...s,
      selectedCvId: row.id,
      cvText: row.cv_text,
      cvFileName: row.cv_filename,
      layoutData: null,
      // Restore the stored raw extraction when present so reselected CVs
      // keep layout-aware parsing; version/method are server-authoritative.
      rawExtractionRef: row.raw_extraction_ref
        ? { id: row.raw_extraction_ref, extraction_version: "2.0", method: "native_blocks" }
        : invalidateRawExtraction(s).rawExtractionRef,
      pendingRawExtractionCleanupIds: s.pendingRawExtractionCleanupIds,
    }));
  }, []);

  // Drop the current selection without touching stored rows (strict
  // no-active rule). Used for starting a brand-new CV: subsequent typing
  // or upload creates a fresh row instead of overwriting another CV.
  const clearSelection = useCallback(() => {
    lastSavedCV.current = null;
    setState((s) => {
      const invalidated = invalidateRawExtraction(s);
      return {
        ...s,
        ...invalidated,
        cvText: "",
        cvFileName: DEFAULT_CV_FILENAME,
        layoutData: null,
        selectedCvId: null,
      };
    });
    setCache({ ...EMPTY_CACHE });
  }, []);

  // Explicit new file upload save (creates a new row and auto-selects it)
  const uploadFileCV = useCallback(async (
    text: string,
    filename: string,
    rawExtractionRef?: RawExtractionReference | null,
    pdfFileId?: string | null,
    thumbnailFileId?: string | null,
  ): Promise<UserCV | null> => {
    // Optimistic marker FIRST (synchronously): the debounced auto-save must
    // see this upload as already persisted, otherwise its 1.5s timer can
    // fire mid-POST and create a second row for the same CV.
    lastSavedCV.current = { text, filename };
    setState((s) => ({
      ...s,
      cvText: text,
      cvFileName: filename,
      layoutData: s.layoutData,
      ...(rawExtractionRef ? acceptRawExtractionReference(s, rawExtractionRef) : {}),
    }));
    setCache({ ...EMPTY_CACHE });
    if (status === "authenticated" && text.trim()) {
      try {
        const row = await uploadUserCVAPI(
          text,
          filename,
          rawExtractionRef?.id,
          pdfFileId ?? undefined,
          thumbnailFileId ?? undefined,
        );
        lastSavedCV.current = { id: row.id, text, filename };
        setState((s) => ({ ...s, selectedCvId: row.id }));
        // Refresh (instead of prepending) so the row carries its minted
        // pdf_url and thumbnail_file_id for the card thumbnail.
        await refreshCvList();
        await refreshProfile(true);
        return row;
      } catch (err) {
        console.error("Failed to save uploaded CV file:", formatCaughtError(err));
        setCvListError(connectivityMessage(err));
        // Release the optimistic marker so a later save can retry.
        lastSavedCV.current = null;
        throw err;
      }
    }
    return null;
  }, [status, refreshProfile, refreshCvList]);

  const deleteCV = useCallback(async (id: string) => {
    clearCachedStructuredDoc(id, userId);
    const isSelected = stateRef.current.selectedCvId === id;
    if (isSelected) {
      // Total, immediate clear: no fallback selection (strict no-active rule).
      // Text must never linger as ghost state after its source row is gone.
      lastSavedCV.current = null;
      setState((s) => {
        const invalidated = invalidateRawExtraction(s);
        return {
          ...s,
          ...invalidated,
          cvText: "",
          cvFileName: DEFAULT_CV_FILENAME,
          layoutData: null,
          selectedCvId: null,
        };
      });
      setCache({ ...EMPTY_CACHE });
    }
    setCvList((prev) => prev.filter((cv) => cv.id !== id));

    if (status === "authenticated") {
      try {
        await deleteUserCVAPI(id);
        await refreshProfile(true);
      } catch (err) {
        console.error("Failed to delete CV:", formatCaughtError(err));
        await refreshCvList();
      }
    }
  }, [status, refreshProfile, refreshCvList, userId]);

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
        isCvListLoading,
        cvList,
        cvListError,
        setCvText,
        setCvFileName,
        setJdText,
        setLayoutData,
        updateWorkspace,
        queueRawExtractionCleanupIds,
        refreshCvList,
        selectCV,
        clearSelection,
        uploadFileCV,
        deleteCV,
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
