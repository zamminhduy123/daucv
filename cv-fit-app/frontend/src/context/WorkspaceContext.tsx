"use client";

import { createContext, useContext, useState, useEffect, useCallback } from "react";

interface WorkspaceState {
  cvText: string;
  cvFileName: string;
  jdText: string;
}

interface WorkspaceContextType extends WorkspaceState {
  setCvText: (text: string) => void;
  setCvFileName: (name: string) => void;
  setJdText: (text: string) => void;
  updateWorkspace: (data: Partial<WorkspaceState>) => void;
  hasData: boolean;
}

const WorkspaceContext = createContext<WorkspaceContextType | null>(null);

const STORAGE_KEY = "dau_workspace";

function loadFromStorage(): WorkspaceState {
  if (typeof window === "undefined") return { cvText: "", cvFileName: "CV của tôi", jdText: "" };
  try {
    const raw = sessionStorage.getItem(STORAGE_KEY);
    if (raw) return JSON.parse(raw);
  } catch { /* ignore parse errors */ }
  return { cvText: "", cvFileName: "CV của tôi", jdText: "" };
}

export function WorkspaceProvider({ children }: { children: React.ReactNode }) {
  const [state, setState] = useState<WorkspaceState>(loadFromStorage);

  // Sync to sessionStorage on every change
  useEffect(() => {
    sessionStorage.setItem(STORAGE_KEY, JSON.stringify(state));
  }, [state]);

  const setCvText = useCallback((cvText: string) => setState((s) => ({ ...s, cvText })), []);
  const setCvFileName = useCallback((cvFileName: string) => setState((s) => ({ ...s, cvFileName })), []);
  const setJdText = useCallback((jdText: string) => setState((s) => ({ ...s, jdText })), []);
  const updateWorkspace = useCallback((data: Partial<WorkspaceState>) => setState((s) => ({ ...s, ...data })), []);

  const hasData = !!(state.cvText.trim() && state.jdText.trim());

  return (
    <WorkspaceContext.Provider value={{ ...state, setCvText, setCvFileName, setJdText, updateWorkspace, hasData }}>
      {children}
    </WorkspaceContext.Provider>
  );
}

export function useWorkspace() {
  const ctx = useContext(WorkspaceContext);
  if (!ctx) throw new Error("useWorkspace must be used within <WorkspaceProvider>");
  return ctx;
}
