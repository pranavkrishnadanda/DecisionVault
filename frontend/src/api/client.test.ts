import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { ApiError, apiFetch } from "@/api/client";
import { useAuthStore } from "@/state/auth-store";

const fetchMock = vi.fn<typeof fetch>();

beforeEach(() => {
  vi.stubGlobal("fetch", fetchMock);
  useAuthStore.setState({
    sessionToken: "initial-access-token",
    accessContext: { role: "operator", organizationId: "org-1" },
    isAccessHydrating: false,
  });
});

afterEach(() => {
  vi.unstubAllGlobals();
  fetchMock.mockReset();
});

describe("apiFetch auth refresh behavior", () => {
  it("retries once after 401 by refreshing session", async () => {
    const refreshSession = vi.fn().mockResolvedValue("new-access-token");
    useAuthStore.setState({ refreshSession });

    fetchMock
      .mockResolvedValueOnce(
        new Response(JSON.stringify({ detail: "Unauthorized" }), {
          status: 401,
          headers: { "Content-Type": "application/json" },
        }),
      )
      .mockResolvedValueOnce(
        new Response(JSON.stringify({ ok: true }), {
          status: 200,
          headers: { "Content-Type": "application/json" },
        }),
      );

    const result = await apiFetch<{ ok: boolean }>("/api/v1/decisions/");

    expect(refreshSession).toHaveBeenCalledTimes(1);
    expect(fetchMock).toHaveBeenCalledTimes(2);
    expect(result).toEqual({ ok: true });
  });

  it("clears session and throws when refresh fails after 401", async () => {
    const refreshSession = vi.fn().mockResolvedValue(null);
    useAuthStore.setState({ refreshSession });

    fetchMock.mockResolvedValueOnce(
      new Response(JSON.stringify({ detail: "Unauthorized" }), {
        status: 401,
        headers: { "Content-Type": "application/json" },
      }),
    );

    await expect(apiFetch("/api/v1/decisions/")).rejects.toBeInstanceOf(
      ApiError,
    );
    expect(refreshSession).toHaveBeenCalledTimes(1);
    expect(useAuthStore.getState().sessionToken).toBeNull();
  });
});
