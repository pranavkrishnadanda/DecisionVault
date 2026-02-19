import { apiFetch } from "@/api/client";
import type {
  CreateIntegrationInput,
  IntegrationRecord,
  IntegrationTestDeliveryResult,
  IntegrationTriggerRecord,
  UpdateIntegrationPatch,
} from "@/domain/integration";

interface IntegrationTriggerApiRecord {
  id: string;
  event_type: string;
  message_template: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

interface IntegrationApiRecord {
  id: string;
  name: string;
  connector_type: "slack" | "teams" | "email";
  config: Record<string, unknown>;
  token_expires_at: string | null;
  is_active: boolean;
  last_error: string;
  triggers: IntegrationTriggerApiRecord[];
  created_at: string;
  updated_at: string;
}

interface SlackInstallUrlResponse {
  install_url: string;
}

interface SlackChannelsResponse {
  channels?: Array<{ id: string; name: string }>;
}

interface CompleteSlackOAuthInput {
  code: string;
  redirectUri: string;
}

interface TestIntegrationDeliveryApiResponse {
  accepted?: boolean;
  delivery_id?: string | null;
  id?: string | null;
}

function mapTrigger(
  record: IntegrationTriggerApiRecord,
): IntegrationTriggerRecord {
  return {
    id: record.id,
    eventType: record.event_type,
    messageTemplate: record.message_template,
    isActive: record.is_active,
    createdAt: record.created_at,
    updatedAt: record.updated_at,
  };
}

function mapIntegration(record: IntegrationApiRecord): IntegrationRecord {
  return {
    id: record.id,
    name: record.name,
    connectorType: record.connector_type,
    config: record.config,
    tokenExpiresAt: record.token_expires_at,
    isActive: record.is_active,
    lastError: record.last_error,
    triggers: record.triggers.map(mapTrigger),
    createdAt: record.created_at,
    updatedAt: record.updated_at,
  };
}

function mapConfigToApi(config: CreateIntegrationInput["config"]) {
  const result: Record<string, unknown> = {};
  if (typeof config.channelId === "string") {
    result.channel_id = config.channelId;
  }
  if (typeof config.messageTemplate === "string") {
    result.message_template = config.messageTemplate;
  }
  if (typeof config.smtpHost === "string") {
    result.smtp_host = config.smtpHost;
  }
  if (typeof config.fromEmail === "string") {
    result.from_email = config.fromEmail;
  }
  if (typeof config.toEmail === "string") {
    result.to_email = config.toEmail;
  }
  return result;
}

export async function listIntegrations(): Promise<IntegrationRecord[]> {
  const data = await apiFetch<IntegrationApiRecord[]>("/api/v1/integrations/");
  return data.map(mapIntegration);
}

export async function createIntegration(
  input: CreateIntegrationInput,
): Promise<IntegrationRecord> {
  const data = await apiFetch<IntegrationApiRecord>("/api/v1/integrations/", {
    method: "POST",
    body: JSON.stringify({
      name: input.name,
      connector_type: input.connectorType,
      config: mapConfigToApi(input.config),
      triggers: (input.triggers ?? []).map((trigger) => ({
        event_type: trigger.eventType,
        message_template: trigger.messageTemplate ?? "",
        is_active: trigger.isActive,
      })),
    }),
  });

  return mapIntegration(data);
}

export async function updateIntegration(
  integrationId: string,
  patch: UpdateIntegrationPatch,
): Promise<IntegrationRecord> {
  const payload: { is_active?: boolean } = {};
  if (typeof patch.isActive === "boolean") {
    payload.is_active = patch.isActive;
  }

  const data = await apiFetch<IntegrationApiRecord>(
    `/api/v1/integrations/${integrationId}/`,
    {
      method: "PATCH",
      body: JSON.stringify(payload),
    },
  );

  return mapIntegration(data);
}

export async function getSlackInstallUrl(
  integrationId: string,
  redirectUri: string,
): Promise<string> {
  const query = new URLSearchParams({
    redirect_uri: redirectUri,
  });
  const data = await apiFetch<SlackInstallUrlResponse>(
    `/api/v1/integrations/${integrationId}/slack/install-url/?${query.toString()}`,
  );
  return data.install_url;
}

export async function completeSlackOAuth(
  integrationId: string,
  input: CompleteSlackOAuthInput,
): Promise<IntegrationRecord> {
  const data = await apiFetch<IntegrationApiRecord>(
    `/api/v1/integrations/${integrationId}/slack/oauth-callback/`,
    {
      method: "POST",
      body: JSON.stringify({
        code: input.code,
        redirect_uri: input.redirectUri,
      }),
    },
  );
  return mapIntegration(data);
}

export async function listSlackChannels(
  integrationId: string,
): Promise<Array<{ id: string; name: string }>> {
  const data = await apiFetch<SlackChannelsResponse>(
    `/api/v1/integrations/${integrationId}/slack/channels/`,
  );
  if (!Array.isArray(data.channels)) {
    return [];
  }
  return data.channels
    .filter((item): item is { id: string; name: string } =>
      Boolean(
        item &&
          typeof item === "object" &&
          typeof item.id === "string" &&
          typeof item.name === "string",
      ),
    )
    .map((item) => ({ id: item.id, name: item.name }));
}

export async function testIntegrationDelivery(
  integrationId: string,
): Promise<IntegrationTestDeliveryResult> {
  const data = await apiFetch<TestIntegrationDeliveryApiResponse>(
    `/api/v1/integrations/${integrationId}/test-delivery/`,
    {
      method: "POST",
      body: JSON.stringify({}),
    },
  );

  return {
    accepted: Boolean(data.accepted ?? true),
    deliveryId: data.delivery_id ?? data.id ?? null,
  };
}

export async function runSlackTestDelivery(
  integrationId: string,
  channelId: string,
): Promise<IntegrationTestDeliveryResult> {
  const data = await apiFetch<TestIntegrationDeliveryApiResponse>(
    `/api/v1/integrations/${integrationId}/slack/test/`,
    {
      method: "POST",
      body: JSON.stringify({ channel_id: channelId }),
    },
  );

  return {
    accepted: Boolean(data.accepted ?? true),
    deliveryId: data.delivery_id ?? data.id ?? null,
  };
}
