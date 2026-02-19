"use client";

import { useMemo } from "react";
import { useAccessControl } from "@/hooks/use-access-control";
import {
  useWebhookDeliveriesQuery,
  useWebhookMetricsQuery,
  useWebhookTimelineQuery,
} from "@/hooks/use-webhook-ops-query";
import { selectSessionToken, useAuthStore } from "@/state/auth-store";
import { RetryPanel } from "@/ui/components/errors/retry-panel";
import { AuthGate } from "@/ui/features/auth/auth-gate";

function formatTimestamp(value: string) {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value;
  }
  return date.toLocaleString();
}

export function WebhookOpsPageClient() {
  const sessionToken = useAuthStore(selectSessionToken);
  const { isAccessHydrating, permissions } = useAccessControl();

  const isAuthenticated = Boolean(sessionToken) && !isAccessHydrating;
  const canRead = permissions.canReadDecisions;

  const metricsQuery = useWebhookMetricsQuery(isAuthenticated && canRead);
  const deliveriesQuery = useWebhookDeliveriesQuery(isAuthenticated && canRead);

  const selectedDeliveryId = useMemo(() => {
    if (!deliveriesQuery.data || deliveriesQuery.data.length === 0) {
      return null;
    }
    return deliveriesQuery.data[0]?.id ?? null;
  }, [deliveriesQuery.data]);

  const timelineQuery = useWebhookTimelineQuery(
    isAuthenticated && canRead,
    selectedDeliveryId,
  );

  if (!isAuthenticated) {
    return (
      <AuthGate>
        <section />
      </AuthGate>
    );
  }

  if (!canRead) {
    return (
      <AuthGate>
        <section className="rounded-xl border border-amber-300/50 bg-amber-50 p-6 text-slate-900">
          <h2 className="text-lg font-semibold">Access restricted</h2>
          <p className="mt-2 text-sm text-slate-700">
            Your role cannot access webhook observability in this organization.
          </p>
        </section>
      </AuthGate>
    );
  }

  if (
    metricsQuery.isError ||
    deliveriesQuery.isError ||
    timelineQuery.isError
  ) {
    return (
      <RetryPanel
        title="Webhook observability unavailable"
        message="Failed to load webhook observability data."
        ctaLabel="Retry loading webhook data"
        onRetry={() => {
          void metricsQuery.refetch();
          void deliveriesQuery.refetch();
          void timelineQuery.refetch();
        }}
      />
    );
  }

  const metrics = metricsQuery.data;
  const deliveries = deliveriesQuery.data ?? [];
  const timelineEvents = timelineQuery.data?.events ?? [];

  return (
    <section className="space-y-6" data-testid="webhook-ops-panel">
      <header>
        <h2 className="text-3xl font-semibold tracking-tight text-slate-900">
          Webhook operations
        </h2>
        <p className="mt-1 text-sm text-slate-600">
          Monitor delivery health, retries, and recovery timeline.
        </p>
      </header>

      <div className="grid gap-3 md:grid-cols-4">
        <article className="rounded-lg border border-slate-200 bg-slate-50 p-3">
          <p className="text-xs uppercase tracking-wide text-slate-500">
            Success rate
          </p>
          <p className="text-xl font-semibold text-slate-900">
            {metricsQuery.isPending
              ? "..."
              : `${metrics?.deliverySuccessRate ?? 0}%`}
          </p>
        </article>
        <article className="rounded-lg border border-slate-200 bg-slate-50 p-3">
          <p className="text-xs uppercase tracking-wide text-slate-500">
            Retries
          </p>
          <p className="text-xl font-semibold text-slate-900">
            {metricsQuery.isPending ? "..." : (metrics?.retryCount ?? 0)}
          </p>
        </article>
        <article className="rounded-lg border border-slate-200 bg-slate-50 p-3">
          <p className="text-xs uppercase tracking-wide text-slate-500">DLQ</p>
          <p className="text-xl font-semibold text-slate-900">
            {metricsQuery.isPending ? "..." : (metrics?.dlqCount ?? 0)}
          </p>
        </article>
        <article className="rounded-lg border border-slate-200 bg-slate-50 p-3">
          <p className="text-xs uppercase tracking-wide text-slate-500">
            Breaker
          </p>
          <p className="text-xl font-semibold text-slate-900">
            {metricsQuery.isPending
              ? "..."
              : `${metrics?.breakerStatus.open ?? 0} open / ${metrics?.breakerStatus.closed ?? 0} closed`}
          </p>
        </article>
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        <section className="rounded-lg border border-slate-200 p-3">
          <h3 className="text-sm font-semibold uppercase tracking-wide text-slate-500">
            Recent deliveries
          </h3>
          <ul className="mt-3 space-y-2">
            {deliveries.length === 0 && (
              <li className="text-sm text-slate-500">No deliveries yet.</li>
            )}
            {deliveries.map((delivery) => (
              <li
                key={delivery.id}
                className="rounded-md border border-slate-200 px-3 py-2 text-sm"
              >
                <p className="font-medium text-slate-900">
                  {delivery.eventType}
                </p>
                <p className="text-slate-600">{delivery.status}</p>
              </li>
            ))}
          </ul>
        </section>

        <section className="rounded-lg border border-slate-200 p-3">
          <h3 className="text-sm font-semibold uppercase tracking-wide text-slate-500">
            Timeline
          </h3>
          <ul className="mt-3 space-y-2">
            {timelineEvents.length === 0 && (
              <li className="text-sm text-slate-500">
                No timeline events available.
              </li>
            )}
            {timelineEvents.map((event) => (
              <li
                key={`${event.type}-${event.timestamp}-${event.attemptNumber ?? "na"}`}
                className="rounded-md border border-slate-200 px-3 py-2 text-sm"
              >
                <p className="font-medium text-slate-900">{event.type}</p>
                <p className="text-slate-600">
                  {formatTimestamp(event.timestamp)}
                </p>
              </li>
            ))}
          </ul>
        </section>
      </div>
    </section>
  );
}
