"use client";

import { useEffect } from "react";
import { useAuthStore } from "@/state/auth-store";

export function AuthBootstrap() {
  const refreshSession = useAuthStore((state) => state.refreshSession);

  useEffect(() => {
    void refreshSession();
  }, [refreshSession]);

  return null;
}
