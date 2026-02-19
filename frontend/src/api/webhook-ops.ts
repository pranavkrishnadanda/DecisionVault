import { apiFetch } from "@/api/client";
import type {
  WebhookDeliverySummary,
  WebhookMetrics,
  WebhookTimeline,
} from "@/domain/webhook-ops";

interface MetricsApiResponse {
  delivery_success_rate: number;
  retry_count: number;
  dlq_count: number;
  breaker_status: {
    open: number;
    closed: number;
  };
}

interface DeliveryApiRecord {
  id: string;
  event_type: string;
  status: string;
  attempt_count: number;
  max_attempts: number;
  created_at: string;
  updated_at: string;
}

interface DeliveriesApiResponse {
  results: DeliveryApiRecord[];
}

interface TimelineApiRecord {
  type: string;
  timestamp: string;
  attempt_number?: number;
  status?: string;
  attempt_delay_seconds?: number | null;
  event?: string;
}

interface TimelineApiResponse {
  delivery_id: string;
  status: string;
  events: TimelineApiRecord[];
}

export async function getWebhookMetrics(): Promise<WebhookMetrics> {
  const data = await apiFetch<MetricsApiResponse>("/api/v1/webhook-deliveries/metrics/");
  return {
    deliverySuccessRate: data.delivery_success_rate,
    retryCount: data.retry_count,
    dlqCount: data.dlq_count,
    breakerStatus: data.breaker_status,
  };
}

export async function listWebhookDeliveries(
  pageSize = 20,
): Promise<WebhookDeliverySummary[]> {
  const data = await apiFetch<DeliveriesApiResponse>(
    `/api/v1/webhook-deliveries/?page_size=${pageSize}`,
  );

  return data.results.map((item) => ({
    id: item.id,
    eventType: item.event_type,
    status: item.status,
    attemptCount: item.attempt_count,
    maxAttempts: item.max_attempts,
    createdAt: item.created_at,
    updatedAt: item.updated_at,
  }));
}

export async function getWebhookTimeline(
  deliveryId: string,
): Promise<WebhookTimeline> {
  const data = await apiFetch<TimelineApiResponse>(
    `/api/v1/webhook-deliveries/${deliveryId}/timeline/`,
  );

  return {
    deliveryId: data.delivery_id,
    status: data.status,
    events: data.events.map((event) => ({
      type: event.type,
      timestamp: event.timestamp,
      attemptNumber: event.attempt_number,
      status: event.status,
      attemptDelaySeconds: event.attempt_delay_seconds,
      event: event.event,
    })),
  };
}
