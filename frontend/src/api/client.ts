import { useAuthStore } from "@/state/auth-store";

export class ApiError extends Error {
  status: number;
  requestId: string | null;

  constructor(message: string, status: number, requestId: string | null) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.requestId = requestId;
  }
}

export async function apiFetch<T>(
  path: string,
  init?: RequestInit,
): Promise<T> {
  const token = useAuthStore.getState().sessionToken;

  const response = await fetch(
    `${process.env.NEXT_PUBLIC_API_URL ?? ""}${path}`,
    {
      ...init,
      headers: {
        "Content-Type": "application/json",
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
        ...init?.headers,
      },
      credentials: "include",
    },
  );

  const requestId = response.headers.get("X-Request-ID");

  if (!response.ok) {
    throw new ApiError("API request failed", response.status, requestId);
  }

  return (await response.json()) as T;
}
