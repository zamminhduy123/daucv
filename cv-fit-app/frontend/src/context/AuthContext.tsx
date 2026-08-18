"use client";

import React, { createContext, useCallback, useContext, useEffect, useRef, useState } from "react";
import { useSession } from "next-auth/react";
import type { Session } from "next-auth";
import { clearAuthToken, getUserProfileAPI, setAuthToken } from "@/lib/api";

export interface UserCV {
  id: string;
  cv_filename: string;
  cv_text: string;
  is_active: boolean;
  created_at: string;
}

export interface UserProfile {
  id: string;
  email: string;
  name: string | null;
  image: string | null;
  credits: number;
  active_cv: UserCV | null;
  total_cvs: number;
  active_cv_age_days: number | null;
}

interface ExtendedSession extends Session {
  accessToken?: string;
}

interface CachedProfile {
  data: UserProfile;
  timestamp: number;
  userId: string;
}

const PROFILE_CACHE_TTL_MS = 30 * 60 * 1000; // 30 minutes TTL
const PROFILE_CACHE_PREFIX = "cv_fit_user_profile_";

function getCacheKey(userId: string): string {
  return `${PROFILE_CACHE_PREFIX}${userId}`;
}

function readCachedProfile(userId: string): CachedProfile | null {
  if (typeof window === "undefined") return null;
  try {
    const raw = localStorage.getItem(getCacheKey(userId));
    if (!raw) return null;
    const parsed: CachedProfile = JSON.parse(raw);
    if (parsed.userId === userId && parsed.data && typeof parsed.timestamp === "number") {
      return parsed;
    }
  } catch {
    // Ignore JSON parse or localStorage access errors
  }
  return null;
}

function writeCachedProfile(userId: string, data: UserProfile): void {
  if (typeof window === "undefined") return;
  try {
    const record: CachedProfile = {
      data,
      timestamp: Date.now(),
      userId,
    };
    localStorage.setItem(getCacheKey(userId), JSON.stringify(record));
  } catch {
    // Ignore quota or storage errors
  }
}

function clearCachedProfile(userId: string): void {
  if (typeof window === "undefined") return;
  try {
    localStorage.removeItem(getCacheKey(userId));
  } catch {
    // Ignore storage errors
  }
}

// In-flight request deduplication across simultaneous callers
let inFlightProfilePromise: Promise<UserProfile | null> | null = null;

interface AuthContextType {
  user: Session["user"] | null;
  userId: string | null;
  status: "authenticated" | "unauthenticated" | "loading";
  credits: number | null;
  creditsLoading: boolean;
  activeCV: UserCV | null;
  refreshProfile: (force?: boolean) => Promise<UserProfile | null>;
  refreshCredits: (force?: boolean) => Promise<number | null>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const { data: session, status } = useSession();
  const [credits, setCredits] = useState<number | null>(null);
  const [activeCV, setActiveCV] = useState<UserCV | null>(null);
  const [creditsLoading, setCreditsLoading] = useState(false);

  const isMountedRef = useRef(true);
  useEffect(() => {
    isMountedRef.current = true;
    return () => {
      isMountedRef.current = false;
    };
  }, []);

  const currentUserId = (session?.user as { id?: string } | undefined)?.id || null;
  const accessToken = (session as ExtendedSession)?.accessToken;

  const refreshProfile = useCallback(
    async (force: boolean = false): Promise<UserProfile | null> => {
      if (status !== "authenticated" || !accessToken || !currentUserId) {
        if (isMountedRef.current) {
          setCredits(null);
          setActiveCV(null);
        }
        return null;
      }

      // 1. If not forcing a refresh, return fresh cached data if still within TTL
      if (!force) {
        const cached = readCachedProfile(currentUserId);
        if (cached && Date.now() - cached.timestamp < PROFILE_CACHE_TTL_MS) {
          if (isMountedRef.current) {
            setCredits(cached.data.credits);
            setActiveCV(cached.data.active_cv);
          }
          return cached.data;
        }
      }

      // 2. Request deduplication: share active in-flight fetch
      if (inFlightProfilePromise) {
        return inFlightProfilePromise;
      }

      if (isMountedRef.current) {
        setCreditsLoading(true);
      }

      inFlightProfilePromise = (async () => {
        try {
          const data = (await getUserProfileAPI()) as UserProfile;
          writeCachedProfile(currentUserId, data);
          if (isMountedRef.current) {
            setCredits(data.credits);
            setActiveCV(data.active_cv);
          }
          return data;
        } catch (err) {
          console.error("Failed to fetch user profile:", err);
          // Fall back to stale cache if available on network failure
          const fallback = readCachedProfile(currentUserId);
          if (!fallback && isMountedRef.current) {
            setCredits(null);
            setActiveCV(null);
          }
          return fallback ? fallback.data : null;
        } finally {
          if (isMountedRef.current) {
            setCreditsLoading(false);
          }
          inFlightProfilePromise = null;
        }
      })();

      return inFlightProfilePromise;
    },
    [accessToken, currentUserId, status]
  );

  const refreshCredits = useCallback(
    async (force: boolean = true): Promise<number | null> => {
      const profile = await refreshProfile(force);
      return profile ? profile.credits : null;
    },
    [refreshProfile]
  );

  // Instant hydration from localStorage + background revalidation if expired
  useEffect(() => {
    if (status === "authenticated" && currentUserId && accessToken) {
      setAuthToken(accessToken);
      const cached = readCachedProfile(currentUserId);
      if (cached && isMountedRef.current) {
        setCredits(cached.data.credits);
        setActiveCV(cached.data.active_cv);
      }

      // Revalidate in background if cache is missing or older than TTL
      const isStale = !cached || Date.now() - cached.timestamp >= PROFILE_CACHE_TTL_MS;
      if (isStale) {
        refreshProfile(true);
      }
    } else if (status === "unauthenticated") {
      clearAuthToken();
      if (currentUserId) {
        clearCachedProfile(currentUserId);
      }
      if (isMountedRef.current) {
        setCredits(null);
        setActiveCV(null);
      }
    }
  }, [status, currentUserId, accessToken, refreshProfile]);

  // Cross-tab synchronization via storage events
  useEffect(() => {
    if (status !== "authenticated" || !currentUserId) return;

    const handleStorageChange = (event: StorageEvent) => {
      if (event.key === getCacheKey(currentUserId) && event.newValue) {
        try {
          const parsed: CachedProfile = JSON.parse(event.newValue);
          if (parsed.userId === currentUserId && parsed.data) {
            setCredits(parsed.data.credits);
            setActiveCV(parsed.data.active_cv);
          }
        } catch {
          // Ignore parse errors
        }
      }
    };

    window.addEventListener("storage", handleStorageChange);
    return () => window.removeEventListener("storage", handleStorageChange);
  }, [status, currentUserId]);

  return (
    <AuthContext.Provider
      value={{
        user: session?.user || null,
        userId: currentUserId,
        status,
        credits,
        creditsLoading,
        activeCV,
        refreshProfile,
        refreshCredits,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
}
