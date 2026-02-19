import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { GET } from "./route";

const fetchMock = vi.fn<typeof fetch>();

describe("integration slack install-url route", () => {
  const originalRedirectUri = process.env.NEXT_PUBLIC_SLACK_REDIRECT_URI;

  beforeEach(() => {
    vi.stubGlobal("fetch", fetchMock);
    if (originalRedirectUri === undefined) {
      delete process.env.NEXT_PUBLIC_SLACK_REDIRECT_URI;
    } else {
      process.env.NEXT_PUBLIC_SLACK_REDIRECT_URI = originalRedirectUri;
    }
  });

  afterEach(() => {
    vi.unstubAllGlobals();
    fetchMock.mockReset();
    if (originalRedirectUri === undefined) {
      delete process.env.NEXT_PUBLIC_SLACK_REDIRECT_URI;
    } else {
      process.env.NEXT_PUBLIC_SLACK_REDIRECT_URI = originalRedirectUri;
    }
  });

  it("overrides localhost redirect_uri with configured HTTPS callback", async () => {
    process.env.NEXT_PUBLIC_SLACK_REDIRECT_URI =
      "https://decisionvault.ngrok-free.app/oauth/slack/callback";
    fetchMock.mockResolvedValueOnce(
      new Response(JSON.stringify({ install_url: "https://slack.com/oauth" }), {
        status: 200,
        headers: {
          "content-type": "application/json",
        },
      }),
    );

    const request = {
      headers: new Headers({ authorization: "Bearer token" }),
      nextUrl: new URL(
        "http://localhost:3000/api/v1/integrations/int-1/slack/install-url?redirect_uri=http%3A%2F%2Flocalhost%3A3000%2Foauth%2Fslack%2Fcallback",
      ),
    } as unknown as Parameters<typeof GET>[0];

    await GET(request, { params: Promise.resolve({ integrationId: "int-1" }) });

    const [calledUrl, calledInit] = fetchMock.mock.calls[0] ?? [];
    expect(String(calledUrl)).toBe(
      "http://localhost:8000/api/v1/integrations/int-1/slack/install-url/?redirect_uri=https%3A%2F%2Fdecisionvault.ngrok-free.app%2Foauth%2Fslack%2Fcallback",
    );
    expect(calledInit).toMatchObject({ method: "GET" });
  });
});
