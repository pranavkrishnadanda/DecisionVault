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
  const isAuthEndpoint = path.startsWith("/api/v1/auth/");

  const performRequest = async () => {
    const token = useAuthStore.getState().sessionToken;
    return fetch(`${process.env.NEXT_PUBLIC_API_URL ?? ""}${path}`, {
      ...init,
      headers: {
        "Content-Type": "application/json",
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
        ...init?.headers,
      },
      credentials: "include",
    });
  };

  let response = await performRequest();

  if (response.status === 401 && !isAuthEndpoint) {
    const refreshedToken = await useAuthStore.getState().refreshSession();
    if (refreshedToken) {
      response = await performRequest();
    } else {
      useAuthStore.getState().clearSessionToken();
    }
  }

  const requestId = response.headers.get("X-Request-ID");

  if (!response.ok) {
    throw new ApiError("API request failed", response.status, requestId);
  }

  if (response.status === 204) {
    return undefined as T;
  }

  return (await response.json()) as T;
}
