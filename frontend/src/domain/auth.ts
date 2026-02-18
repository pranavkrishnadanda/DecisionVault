export type SessionToken = string;

export interface AuthState {
  sessionToken: SessionToken | null;
}
