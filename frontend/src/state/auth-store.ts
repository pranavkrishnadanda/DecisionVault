import { create } from "zustand";
import type { SessionToken } from "@/domain/auth";

interface AuthStore {
  sessionToken: SessionToken | null;
  setSessionToken: (sessionToken: SessionToken) => void;
  clearSessionToken: () => void;
}

export const useAuthStore = create<AuthStore>((set) => ({
  sessionToken: null,
  setSessionToken: (sessionToken) => {
    set({ sessionToken });
  },
  clearSessionToken: () => {
    set({ sessionToken: null });
  },
}));

export const selectSessionToken = (state: AuthStore) => state.sessionToken;
