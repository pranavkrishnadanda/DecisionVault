import { apiFetch } from "@/api/client";

export interface SlackIntegrationSummary {
  id: string;
  team_name: string;
  team_id?: string;
  installed_at?: string;
}

export interface SlackChannel {
  id: string;
  name: string;
  is_private: boolean;
  num_members: number;
  topic: string;
}

export interface SlackMessage {
  user_name: string;
  text: string;
  ts: string;
  thread_replies: SlackMessageReply[];
}

export interface SlackMessageReply {
  user_name: string;
  text: string;
  ts: string;
}

export interface SlackMessageResponse {
  messages: SlackMessage[];
  has_more: boolean;
  next_cursor: string;
}

export interface SlackTestResponse {
  success: boolean;
  error: string | null;
  message_ts: string | null;
}

export async function listSlackIntegrations(): Promise<SlackIntegrationSummary[]> {
  return apiFetch<SlackIntegrationSummary[]>("/api/slack/integrations");
}

export async function listSlackChannels(
  integrationId: string,
): Promise<SlackChannel[]> {
  const query = new URLSearchParams({ integration_id: integrationId });
  return apiFetch<SlackChannel[]>(`/api/slack/channels?${query.toString()}`);
}

export async function listSlackMessages(
  integrationId: string,
  channelId: string,
  oldest: string,
): Promise<SlackMessageResponse> {
  const query = new URLSearchParams({
    integration_id: integrationId,
    channel_id: channelId,
    oldest,
    limit: "100",
  });
  return apiFetch<SlackMessageResponse>(`/api/slack/messages?${query.toString()}`);
}

export async function sendSlackTest(input: {
  integrationId: string;
  channelId: string;
}): Promise<SlackTestResponse> {
  return apiFetch<SlackTestResponse>("/api/slack/test", {
    method: "POST",
    body: JSON.stringify({
      integration_id: input.integrationId,
      channel_id: input.channelId,
    }),
  });
}
