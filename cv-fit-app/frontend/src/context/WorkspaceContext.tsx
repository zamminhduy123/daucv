"use client";

import { createContext, useContext, useState, useEffect, useCallback } from "react";
import type { CVAnalysisResponse } from "@/types";

// ── Cache types ──────────────────────────────────────────────────────────────

interface WriterResult {
  subject_line: string;
  content: string;
  tips: string[];
}

interface WorkspaceCache {
  analyzerResult: CVAnalysisResponse | null;
  interviewState: any;
  writerResults: Record<string, WriterResult>; // keyed by "type:tone" for multi-variant caching
}

const EMPTY_CACHE: WorkspaceCache = {
  analyzerResult: null,
  interviewState: null,
  writerResults: {},
};

// ── Core state ───────────────────────────────────────────────────────────────

interface WorkspaceState {
  cvText: string;
  cvFileName: string;
  jdText: string;
}

interface WorkspaceContextType extends WorkspaceState {
  isLoaded: boolean;
  setCvText: (text: string) => void;
  setCvFileName: (name: string) => void;
  setJdText: (text: string) => void;
  updateWorkspace: (data: Partial<WorkspaceState>) => void;
  hasData: boolean;

  // Cache accessors
  cache: WorkspaceCache;
  setCachedAnalysis: (result: CVAnalysisResponse) => void;
  setCachedInterview: (state: any) => void;
  setCachedWriter: (key: string, result: WriterResult) => void;
  clearCache: () => void;
}

const WorkspaceContext = createContext<WorkspaceContextType | null>(null);

const STORAGE_KEY = "dau_workspace";
const CACHE_KEY = "dau_workspace_cache";

export function WorkspaceProvider({ children }: { children: React.ReactNode }) {
  const [state, setState] = useState<WorkspaceState>({ cvText: "", cvFileName: "CV của tôi", jdText: "" });
  const [cache, setCache] = useState<WorkspaceCache>({ ...EMPTY_CACHE });
  const [isLoaded, setIsLoaded] = useState(false);

  // Sync state from sessionStorage on mount
  useEffect(() => {
    const rawState = sessionStorage.getItem(STORAGE_KEY);
    if (rawState) {
      try {
        setState(JSON.parse(rawState));
      } catch {}
    }

    const rawCache = sessionStorage.getItem(CACHE_KEY);
    if (rawCache) {
      try {
        setCache(JSON.parse(rawCache));
      } catch {}
    }

    setIsLoaded(true);
  }, []);

  // Sync workspace to sessionStorage
  useEffect(() => {
    if (!isLoaded) return;
    sessionStorage.setItem(STORAGE_KEY, JSON.stringify(state));
  }, [state, isLoaded]);

  // Sync cache to sessionStorage
  useEffect(() => {
    if (!isLoaded) return;
    sessionStorage.setItem(CACHE_KEY, JSON.stringify(cache));
  }, [cache, isLoaded]);

  const setCvText = useCallback((cvText: string) => setState((s) => ({ ...s, cvText })), []);
  const setCvFileName = useCallback((cvFileName: string) => setState((s) => ({ ...s, cvFileName })), []);
  const setJdText = useCallback((jdText: string) => setState((s) => ({ ...s, jdText })), []);

  const clearCache = useCallback(() => setCache({ ...EMPTY_CACHE }), []);

  const updateWorkspace = useCallback((data: Partial<WorkspaceState>) => {
    setState((s) => {
      const next = { ...s, ...data };
      // If CV or JD content changed, invalidate all cached results
      if (next.cvText !== s.cvText || next.jdText !== s.jdText) {
        setCache({ ...EMPTY_CACHE });
      }
      return next;
    });
  }, []);

  const setCachedAnalysis = useCallback(
    (result: CVAnalysisResponse) => setCache((c) => ({ ...c, analyzerResult: result })),
    []
  );
  const setCachedInterview = useCallback(
    (interviewState: any) => setCache((c) => ({ ...c, interviewState })),
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
        updateWorkspace,
        hasData,
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
