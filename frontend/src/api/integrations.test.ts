import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import * as apiClient from "@/api/client";
import {
  completeSlackOAuth,
  createIntegration,
  getSlackInstallUrl,
  listIntegrations,
  listSlackChannels,
  runSlackTestDelivery,
  testIntegrationDelivery,
  updateIntegration,
} from "@/api/integrations";

describe("integrations api", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("maps integrations list payload", async () => {
    const apiFetchSpy = vi.spyOn(apiClient, "apiFetch").mockResolvedValue([
      {
        id: "int-1",
        name: "Primary Slack",
        connector_type: "slack",
        config: { channel_id: "COPS" },
        token_expires_at: "2026-02-20T00:00:00.000Z",
        is_active: true,
        last_error: "",
        triggers: [
          {
            id: "trig-1",
            event_type: "decision.completed",
            message_template: "Done",
            is_active: true,
            created_at: "2026-02-19T00:00:00.000Z",
            updated_at: "2026-02-19T00:00:00.000Z",
          },
        ],
        created_at: "2026-02-19T00:00:00.000Z",
        updated_at: "2026-02-19T00:00:00.000Z",
      },
    ]);

    const result = await listIntegrations();

    expect(apiFetchSpy).toHaveBeenCalledWith("/api/v1/integrations/");
    expect(result).toEqual([
      {
        id: "int-1",
        name: "Primary Slack",
        connectorType: "slack",
        config: { channel_id: "COPS" },
        tokenExpiresAt: "2026-02-20T00:00:00.000Z",
        isActive: true,
        lastError: "",
        triggers: [
          {
            id: "trig-1",
            eventType: "decision.completed",
            messageTemplate: "Done",
            isActive: true,
            createdAt: "2026-02-19T00:00:00.000Z",
            updatedAt: "2026-02-19T00:00:00.000Z",
          },
        ],
        createdAt: "2026-02-19T00:00:00.000Z",
        updatedAt: "2026-02-19T00:00:00.000Z",
      },
    ]);
  });

  it("patches integration active state", async () => {
    const apiFetchSpy = vi.spyOn(apiClient, "apiFetch").mockResolvedValue({
      id: "int-1",
      name: "Primary Slack",
      connector_type: "slack",
      config: { channel_id: "COPS" },
      token_expires_at: null,
      is_active: false,
      last_error: "",
      triggers: [],
      created_at: "2026-02-19T00:00:00.000Z",
      updated_at: "2026-02-19T00:00:00.000Z",
    });

    await updateIntegration("int-1", { isActive: false });

    expect(apiFetchSpy).toHaveBeenCalledWith("/api/v1/integrations/int-1/", {
      method: "PATCH",
      body: JSON.stringify({
        is_active: false,
      }),
    });
  });

  it("requests slack install URL", async () => {
    const apiFetchSpy = vi.spyOn(apiClient, "apiFetch").mockResolvedValue({
      install_url: "https://slack.com/oauth/v2/authorize?state=abc",
    });

    const installUrl = await getSlackInstallUrl(
      "int-1",
      "https://app.localhost/oauth/slack/callback",
    );

    expect(apiFetchSpy).toHaveBeenCalledWith(
      "/api/v1/integrations/int-1/slack/install-url/?redirect_uri=https%3A%2F%2Fapp.localhost%2Foauth%2Fslack%2Fcallback",
    );
    expect(installUrl).toBe("https://slack.com/oauth/v2/authorize?state=abc");
  });

  it("submits slack oauth callback", async () => {
    const apiFetchSpy = vi.spyOn(apiClient, "apiFetch").mockResolvedValue({
      id: "int-1",
      name: "Primary Slack",
      connector_type: "slack",
      config: { channel_id: "COPS" },
      token_expires_at: "2026-02-20T00:00:00.000Z",
      is_active: true,
      last_error: "",
      triggers: [],
      created_at: "2026-02-19T00:00:00.000Z",
      updated_at: "2026-02-19T00:00:00.000Z",
    });

    await completeSlackOAuth("int-1", {
      code: "oauth-code",
      redirectUri: "https://app.localhost/oauth/slack/callback",
    });

    expect(apiFetchSpy).toHaveBeenCalledWith(
      "/api/v1/integrations/int-1/slack/oauth-callback/",
      {
        method: "POST",
        body: JSON.stringify({
          code: "oauth-code",
          redirect_uri: "https://app.localhost/oauth/slack/callback",
        }),
      },
    );
  });

  it("creates integration with trigger payload mapping", async () => {
    const apiFetchSpy = vi.spyOn(apiClient, "apiFetch").mockResolvedValue({
      id: "int-1",
      name: "Fraud Alerts",
      connector_type: "slack",
      config: { channel_id: "CALERTS" },
      token_expires_at: null,
      is_active: true,
      last_error: "",
      triggers: [
        {
          id: "trig-1",
          event_type: "decision.completed",
          message_template: "",
          is_active: true,
          created_at: "2026-02-19T00:00:00.000Z",
          updated_at: "2026-02-19T00:00:00.000Z",
        },
      ],
      created_at: "2026-02-19T00:00:00.000Z",
      updated_at: "2026-02-19T00:00:00.000Z",
    });

    await createIntegration({
      name: "Fraud Alerts",
      connectorType: "slack",
      config: { channelId: "CALERTS" },
      triggers: [
        {
          eventType: "decision.completed",
          isActive: true,
        },
      ],
    });

    expect(apiFetchSpy).toHaveBeenCalledWith("/api/v1/integrations/", {
      method: "POST",
      body: JSON.stringify({
        name: "Fraud Alerts",
        connector_type: "slack",
        config: { channel_id: "CALERTS" },
        triggers: [
          {
            event_type: "decision.completed",
            message_template: "",
            is_active: true,
          },
        ],
      }),
    });
  });

  it("submits integration test-delivery request", async () => {
    const apiFetchSpy = vi.spyOn(apiClient, "apiFetch").mockResolvedValue({
      accepted: true,
      delivery_id: "delivery-2",
    });

    const result = await testIntegrationDelivery("int-2");

    expect(apiFetchSpy).toHaveBeenCalledWith(
      "/api/v1/integrations/int-2/test-delivery/",
      {
        method: "POST",
        body: JSON.stringify({}),
      },
    );
    expect(result).toEqual({
      accepted: true,
      deliveryId: "delivery-2",
    });
  });

  it("lists discoverable slack channels", async () => {
    const apiFetchSpy = vi.spyOn(apiClient, "apiFetch").mockResolvedValue({
      channels: [
        { id: "COPS", name: "ops-alerts" },
        { id: "CALERTS", name: "fraud-alerts" },
      ],
    });

    const result = await listSlackChannels("int-2");

    expect(apiFetchSpy).toHaveBeenCalledWith(
      "/api/v1/integrations/int-2/slack/channels/",
    );
    expect(result).toEqual([
      { id: "COPS", name: "ops-alerts" },
      { id: "CALERTS", name: "fraud-alerts" },
    ]);
  });

  it("submits real slack test delivery request", async () => {
    const apiFetchSpy = vi.spyOn(apiClient, "apiFetch").mockResolvedValue({
      accepted: true,
      delivery_id: "delivery-9",
    });

    const result = await runSlackTestDelivery("int-2", "COPS");

    expect(apiFetchSpy).toHaveBeenCalledWith(
      "/api/v1/integrations/int-2/slack/test/",
      {
        method: "POST",
        body: JSON.stringify({ channel_id: "COPS" }),
      },
    );
    expect(result).toEqual({
      accepted: true,
      deliveryId: "delivery-9",
    });
  });
});
