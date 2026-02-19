export type SessionToken = string;
export type OrganizationRole = "admin" | "operator" | "viewer";

export interface AccessContext {
  organizationId: string | null;
  role: OrganizationRole | null;
}

export interface AuthState {
  sessionToken: SessionToken | null;
  accessContext: AccessContext | null;
  isAccessHydrating: boolean;
}
