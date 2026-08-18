"use client";

import React from "react";
import { SessionProvider } from "next-auth/react";
import { AuthProvider } from "./AuthContext";

export function Providers({ children }: { children: React.ReactNode }) {
  return (
    <SessionProvider refetchOnWindowFocus={false}>
      <AuthProvider>{children}</AuthProvider>
    </SessionProvider>
  );
}
