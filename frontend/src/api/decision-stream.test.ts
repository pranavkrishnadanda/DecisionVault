import { waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { ApiError } from "@/api/client";
import { subscribeToDecisionEvents } from "@/api/decision-stream";

const fetchMock = vi.fn<typeof fetch>();

describe("subscribeToDecisionEvents", () => {
  beforeEach(() => {
    vi.stubGlobal("fetch", fetchMock);
  });

  afterEach(() => {
    vi.unstubAllGlobals();
    fetchMock.mockReset();
  });

  it("reports non-ok stream response via onError callback", async () => {
    fetchMock.mockResolvedValue(
      new Response("", {
        status: 503,
        headers: {
          "X-Request-ID": "req-1",
        },
      }),
    );

    const onError = vi.fn();
    const unsubscribe = subscribeToDecisionEvents({
      token: "jwt-token",
      onEvent: vi.fn(),
      onError,
    });

    await waitFor(() => {
      expect(onError).toHaveBeenCalledTimes(1);
    });

    const [error] = onError.mock.calls[0] as [Error];
    expect(error).toBeInstanceOf(ApiError);
    expect((error as ApiError).status).toBe(503);

    unsubscribe();
  });
});
