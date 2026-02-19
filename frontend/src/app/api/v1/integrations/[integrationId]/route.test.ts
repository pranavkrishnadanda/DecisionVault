import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { DELETE, PATCH } from "./route";

const fetchMock = vi.fn<typeof fetch>();

describe("integration detail api route", () => {
  beforeEach(() => {
    vi.stubGlobal("fetch", fetchMock);
  });

  afterEach(() => {
    vi.unstubAllGlobals();
    fetchMock.mockReset();
  });

  it("proxies PATCH requests to backend integration detail endpoint", async () => {
    fetchMock.mockResolvedValueOnce(
      new Response(JSON.stringify({ id: "int-1" }), {
        status: 200,
        headers: {
          "content-type": "application/json",
          "X-Request-ID": "req-1",
        },
      }),
    );

    const requestBody = JSON.stringify({ is_active: false });
    const request = {
      headers: new Headers({ authorization: "Bearer token" }),
      text: vi.fn().mockResolvedValue(requestBody),
    } as unknown as Parameters<typeof PATCH>[0];

    const response = await PATCH(request, {
      params: Promise.resolve({ integrationId: "int-1" }),
    });

    expect(fetchMock).toHaveBeenCalledWith(
      "http://localhost:8000/api/v1/integrations/int-1/",
      {
        method: "PATCH",
        headers: {
          "Content-Type": "application/json",
          Authorization: "Bearer token",
        },
        body: requestBody,
        cache: "no-store",
      },
    );
    expect(response.status).toBe(200);
  });

  it("proxies DELETE requests to backend integration detail endpoint", async () => {
    fetchMock.mockResolvedValueOnce(
      new Response(null, {
        status: 204,
        headers: {
          "X-Request-ID": "req-2",
        },
      }),
    );

    const request = {
      headers: new Headers({ authorization: "Bearer token" }),
    } as unknown as Parameters<typeof DELETE>[0];

    const response = await DELETE(request, {
      params: Promise.resolve({ integrationId: "int-1" }),
    });

    expect(fetchMock).toHaveBeenCalledWith(
      "http://localhost:8000/api/v1/integrations/int-1/",
      {
        method: "DELETE",
        headers: {
          "Content-Type": "application/json",
          Authorization: "Bearer token",
        },
        cache: "no-store",
      },
    );
    expect(response.status).toBe(204);
  });

  it("handles 204 without constructing a response body", async () => {
    fetchMock.mockResolvedValueOnce(
      new Response(null, {
        status: 204,
      }),
    );

    const request = {
      headers: new Headers({ authorization: "Bearer token" }),
    } as unknown as Parameters<typeof DELETE>[0];

    const response = await DELETE(request, {
      params: Promise.resolve({ integrationId: "int-1" }),
    });

    expect(response.status).toBe(204);
    expect(await response.text()).toBe("");
  });
});
