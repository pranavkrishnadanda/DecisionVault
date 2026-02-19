import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import * as apiClient from "@/api/client";
import {
  getWebhookMetrics,
  getWebhookTimeline,
  listWebhookDeliveries,
} from "@/api/webhook-ops";

describe("webhook ops api", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("maps webhook metrics payload", async () => {
    const apiFetchSpy = vi.spyOn(apiClient, "apiFetch").mockResolvedValue({
      delivery_success_rate: 97,
      retry_count: 5,
      dlq_count: 1,
      breaker_status: {
        open: 1,
        closed: 3,
      },
    });

    const result = await getWebhookMetrics();

    expect(apiFetchSpy).toHaveBeenCalledWith(
      "/api/v1/webhook-deliveries/metrics/",
    );
    expect(result).toEqual({
      deliverySuccessRate: 97,
      retryCount: 5,
      dlqCount: 1,
      breakerStatus: {
        open: 1,
        closed: 3,
      },
    });
  });

  it("maps webhook delivery list payload", async () => {
    const apiFetchSpy = vi.spyOn(apiClient, "apiFetch").mockResolvedValue({
      results: [
        {
          id: "d-1",
          event_type: "decision.updated",
          status: "failed",
          attempt_count: 2,
          max_attempts: 5,
          created_at: "2026-02-19T10:00:00.000Z",
          updated_at: "2026-02-19T10:01:00.000Z",
        },
      ],
    });

    const result = await listWebhookDeliveries(20);

    expect(apiFetchSpy).toHaveBeenCalledWith(
      "/api/v1/webhook-deliveries/?page_size=20",
    );
    expect(result).toEqual([
      {
        id: "d-1",
        eventType: "decision.updated",
        status: "failed",
        attemptCount: 2,
        maxAttempts: 5,
        createdAt: "2026-02-19T10:00:00.000Z",
        updatedAt: "2026-02-19T10:01:00.000Z",
      },
    ]);
  });

  it("does not call timeline endpoint when delivery id is invalid", async () => {
    const apiFetchSpy = vi.spyOn(apiClient, "apiFetch");
    const result = await getWebhookTimeline("null");

    expect(apiFetchSpy).not.toHaveBeenCalled();
    expect(result).toEqual({
      deliveryId: "",
      status: "idle",
      events: [],
    });
  });
});
