import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { POST } from "./route";

const fetchMock = vi.fn<typeof fetch>();

describe("integrations api route", () => {
  beforeEach(() => {
    vi.stubGlobal("fetch", fetchMock);
  });

  afterEach(() => {
    vi.unstubAllGlobals();
    fetchMock.mockReset();
  });

  it("proxies POST requests to backend integrations endpoint", async () => {
    fetchMock.mockResolvedValueOnce(
      new Response(JSON.stringify({ id: "int-1" }), {
        status: 201,
        headers: {
          "content-type": "application/json",
          "X-Request-ID": "req-1",
        },
      }),
    );

    const requestBody = JSON.stringify({
      name: "Fraud Alerts",
      connector_type: "slack",
    });
    const request = {
      headers: new Headers({ authorization: "Bearer token" }),
      text: vi.fn().mockResolvedValue(requestBody),
    } as unknown as Parameters<typeof POST>[0];

    const response = await POST(request);

    expect(fetchMock).toHaveBeenCalledWith(
      "http://localhost:8000/api/v1/integrations/",
      {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: "Bearer token",
        },
        body: requestBody,
        cache: "no-store",
      },
    );
    expect(response.status).toBe(201);
    expect(await response.json()).toEqual({ id: "int-1" });
  });
});
