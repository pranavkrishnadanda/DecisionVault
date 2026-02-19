import { create } from "zustand";
import type {
  AccessContext,
  OrganizationRole,
  SessionToken,
} from "@/domain/auth";

interface AuthStore {
  sessionToken: SessionToken | null;
  accessContext: AccessContext | null;
  isAccessHydrating: boolean;
  setSessionToken: (sessionToken: SessionToken) => void;
  setAccessHydrating: (isAccessHydrating: boolean) => void;
  clearSessionToken: () => void;
}

interface JwtPayload {
  organization_id?: string;
  org_id?: string;
  organization?: string;
  role?: string;
  org_role?: string;
}

function decodeJwtPayload(token: string): JwtPayload | null {
  const tokenParts = token.split(".");
  if (tokenParts.length < 2) {
    return null;
  }

  const payloadPart = tokenParts[1];
  if (!payloadPart) {
    return null;
  }

  const normalized = payloadPart.replace(/-/g, "+").replace(/_/g, "/");
  const padded = normalized + "=".repeat((4 - (normalized.length % 4)) % 4);

  try {
    const json = atob(padded);
    const parsed = JSON.parse(json);
    if (!parsed || typeof parsed !== "object") {
      return null;
    }
    return parsed as JwtPayload;
  } catch {
    return null;
  }
}

function parseRole(value: string | undefined): OrganizationRole | null {
  if (value === "admin" || value === "operator" || value === "viewer") {
    return value;
  }
  return null;
}

function resolveAccessContext(token: string): AccessContext {
  const payload = decodeJwtPayload(token);
  if (!payload) {
    return {
      organizationId: null,
      role: null,
    };
  }

  return {
    organizationId:
      payload.organization_id ?? payload.org_id ?? payload.organization ?? null,
    role: parseRole(payload.org_role ?? payload.role),
  };
}

export const useAuthStore = create<AuthStore>((set) => ({
  sessionToken: null,
  accessContext: null,
  isAccessHydrating: false,
  setSessionToken: (sessionToken) => {
    set({
      sessionToken,
      accessContext: resolveAccessContext(sessionToken),
      isAccessHydrating: false,
    });
  },
  setAccessHydrating: (isAccessHydrating) => {
    set({ isAccessHydrating });
  },
  clearSessionToken: () => {
    set({
      sessionToken: null,
      accessContext: null,
      isAccessHydrating: false,
    });
  },
}));

export const selectSessionToken = (state: AuthStore) => state.sessionToken;
export const selectAccessContext = (state: AuthStore) => state.accessContext;
export const selectIsAccessHydrating = (state: AuthStore) =>
  state.isAccessHydrating;
