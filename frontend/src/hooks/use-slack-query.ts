import { useMutation, useQuery } from "@tanstack/react-query";
import {
  listSlackChannels,
  listSlackIntegrations,
  listSlackMessages,
  sendSlackTest,
} from "@/api/slack";

export function useSlackIntegrationsQuery() {
  return useQuery({
    queryKey: ["slack", "integrations"],
    queryFn: listSlackIntegrations,
    staleTime: 10_000,
    retry: 1,
    refetchOnWindowFocus: false,
  });
}

export function useSlackChannelsQuery(integrationId: string, enabled: boolean) {
  return useQuery({
    queryKey: ["slack", integrationId, "channels"],
    queryFn: () => listSlackChannels(integrationId),
    enabled: enabled && integrationId.trim().length > 0,
    staleTime: 60_000,
    retry: 1,
    refetchOnWindowFocus: false,
  });
}

export function useSlackMessagesQuery(
  integrationId: string,
  channelId: string,
  oldest: string,
  enabled: boolean,
) {
  return useQuery({
    queryKey: ["slack", integrationId, channelId, "messages", oldest],
    queryFn: () => listSlackMessages(integrationId, channelId, oldest),
    enabled:
      enabled &&
      integrationId.trim().length > 0 &&
      channelId.trim().length > 0,
    staleTime: 5_000,
    retry: 1,
    refetchOnWindowFocus: false,
  });
}

export function useSlackTestMutation() {
  return useMutation({
    mutationFn: sendSlackTest,
  });
}
