"use client";

import React, { createContext, useContext, useEffect, useState } from "react";
import { useSession } from "next-auth/react";
import type { Session } from "next-auth";
import { getUserProfileAPI } from "@/lib/api";

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

interface AuthContextType {
  user: Session["user"] | null;
  userId: string | null;
  status: "authenticated" | "unauthenticated" | "loading";
  credits: number | null;
  creditsLoading: boolean;
  activeCV: UserCV | null;
  refreshProfile: () => Promise<UserProfile | null>;
  refreshCredits: () => Promise<number | null>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const { data: session, status } = useSession();
  const [credits, setCredits] = useState<number | null>(null);
  const [activeCV, setActiveCV] = useState<UserCV | null>(null);
  const [creditsLoading, setCreditsLoading] = useState(false);

  const refreshProfile = async (): Promise<UserProfile | null> => {
    if (status !== "authenticated" || !(session as ExtendedSession)?.accessToken) {
      setCredits(null);
      setActiveCV(null);
      return null;
    }

    setCreditsLoading(true);
    try {
      const data = await getUserProfileAPI() as UserProfile;
      setCredits(data.credits);
      setActiveCV(data.active_cv);
      return data;
    } catch (err) {
      console.error("Failed to fetch user profile:", err);
      setCredits(null);
      setActiveCV(null);
      return null;
    } finally {
      setCreditsLoading(false);
    }
  };

  const refreshCredits = async (): Promise<number | null> => {
    const profile = await refreshProfile();
    return profile ? profile.credits : null;
  };

  useEffect(() => {
    if (status === "authenticated" && (session as ExtendedSession)?.accessToken) {
      // eslint-disable-next-line react-hooks/set-state-in-effect
      refreshProfile();
    } else if (status === "unauthenticated") {
      setCredits(null);
      setActiveCV(null);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [status, session]);

  return (
    <AuthContext.Provider
      value={{
        user: session?.user || null,
        userId: (session?.user as { id?: string } | undefined)?.id || null,
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
