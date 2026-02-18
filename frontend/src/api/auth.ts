import { apiFetch } from "@/api/client";

interface TokenResponse {
  access: string;
  refresh: string;
}

interface LoginInput {
  username: string;
  password: string;
}

interface RegisterInput {
  username: string;
  email: string;
  password: string;
}

export async function loginWithPassword({
  username,
  password,
}: LoginInput): Promise<string> {
  const payload = await apiFetch<TokenResponse>("/api/v1/auth/token/", {
    method: "POST",
    body: JSON.stringify({ username, password }),
  });

  return payload.access;
}

export async function registerWithPassword({
  username,
  email,
  password,
}: RegisterInput): Promise<string> {
  const payload = await apiFetch<TokenResponse>("/api/v1/auth/register/", {
    method: "POST",
    body: JSON.stringify({ username, email, password }),
  });

  return payload.access;
}
