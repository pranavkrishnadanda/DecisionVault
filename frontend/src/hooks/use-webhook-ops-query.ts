import { useMemo } from "react";
import { useQuery } from "@tanstack/react-query";
import {
  getWebhookMetrics,
  getWebhookTimeline,
  listWebhookDeliveries,
} from "@/api/webhook-ops";

export function useWebhookMetricsQuery(enabled: boolean) {
  return useQuery({
    queryKey: ["webhook-metrics"],
    queryFn: () => getWebhookMetrics(),
    enabled,
    staleTime: 15_000,
    gcTime: 5 * 60_000,
    retry: 1,
    refetchOnWindowFocus: false,
  });
}

export function useWebhookDeliveriesQuery(enabled: boolean) {
  return useQuery({
    queryKey: ["webhook-deliveries", { pageSize: 20 }],
    queryFn: () => listWebhookDeliveries(20),
    enabled,
    staleTime: 15_000,
    gcTime: 5 * 60_000,
    retry: 1,
    refetchOnWindowFocus: false,
  });
}

export function useWebhookTimelineQuery(
  enabled: boolean,
  selectedDeliveryId: string | null,
) {
  const timelineEnabled = useMemo(
    () => enabled && Boolean(selectedDeliveryId),
    [enabled, selectedDeliveryId],
  );

  return useQuery({
    queryKey: ["webhook-timeline", selectedDeliveryId],
    queryFn: () => getWebhookTimeline(selectedDeliveryId as string),
    enabled: timelineEnabled,
    staleTime: 15_000,
    gcTime: 5 * 60_000,
    retry: 1,
    refetchOnWindowFocus: false,
  });
}
