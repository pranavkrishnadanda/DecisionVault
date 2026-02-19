import { ApiError } from "@/api/client";

interface RefreshResponse {
  access: string;
}

export async function refreshSessionRequest(): Promise<string | null> {
  const response = await fetch(
    `${process.env.NEXT_PUBLIC_API_URL ?? ""}/api/v1/auth/refresh/`,
    {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      credentials: "include",
    },
  );

  if (response.status === 401) {
    return null;
  }

  const requestId = response.headers.get("X-Request-ID");
  if (!response.ok) {
    throw new ApiError("Session refresh failed", response.status, requestId);
  }

  const payload = (await response.json()) as RefreshResponse;
  if (!payload.access) {
    return null;
  }
  return payload.access;
}

export async function logoutSessionRequest(): Promise<void> {
  await fetch(`${process.env.NEXT_PUBLIC_API_URL ?? ""}/api/v1/auth/logout/`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    credentials: "include",
  });
}
