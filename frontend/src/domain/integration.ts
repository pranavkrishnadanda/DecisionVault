export type IntegrationConnectorType = "slack" | "teams" | "email";

export interface IntegrationTriggerRecord {
  id: string;
  eventType: string;
  messageTemplate: string;
  isActive: boolean;
  createdAt: string;
  updatedAt: string;
}

export interface IntegrationRecord {
  id: string;
  name: string;
  connectorType: IntegrationConnectorType;
  config: Record<string, unknown>;
  tokenExpiresAt: string | null;
  isActive: boolean;
  lastError: string;
  triggers: IntegrationTriggerRecord[];
  createdAt: string;
  updatedAt: string;
}

export interface UpdateIntegrationPatch {
  isActive?: boolean;
}

export interface CreateIntegrationTriggerInput {
  eventType: string;
  messageTemplate?: string;
  isActive: boolean;
}

export interface CreateIntegrationInput {
  name: string;
  connectorType: IntegrationConnectorType;
  config: {
    channelId?: string;
    messageTemplate?: string;
    smtpHost?: string;
    fromEmail?: string;
    toEmail?: string;
  };
  triggers?: CreateIntegrationTriggerInput[];
}

export interface IntegrationTestDeliveryResult {
  accepted: boolean;
  deliveryId: string | null;
}

export interface IntegrationDeliveryRecord {
  id: string;
  status: "pending" | "delivered" | "failed";
  createdAt: string;
}

export type IntegrationHealthStatus =
  | "healthy"
  | "degraded"
  | "expired"
  | "disabled";

export type SlackIntegrationStatus =
  | "active"
  | "degraded"
  | "expired"
  | "disabled"
  | "failed";

export function resolveIntegrationHealth(
  integration: Pick<
    IntegrationRecord,
    "isActive" | "lastError" | "tokenExpiresAt"
  >,
  now = new Date(),
): IntegrationHealthStatus {
  if (!integration.isActive) {
    return "disabled";
  }
  if (integration.lastError.trim().length > 0) {
    return "degraded";
  }
  if (integration.tokenExpiresAt) {
    const expiresAt = new Date(integration.tokenExpiresAt);
    if (
      !Number.isNaN(expiresAt.getTime()) &&
      expiresAt.getTime() <= now.getTime()
    ) {
      return "expired";
    }
  }
  return "healthy";
}

export function resolveSlackIntegrationStatus(
  integration: Pick<
    IntegrationRecord,
    "isActive" | "lastError" | "tokenExpiresAt"
  >,
  lastDelivery?: Pick<IntegrationDeliveryRecord, "status">,
  now = new Date(),
): SlackIntegrationStatus {
  if (!integration.isActive) {
    return "disabled";
  }
  if (integration.tokenExpiresAt) {
    const expiresAt = new Date(integration.tokenExpiresAt);
    if (
      !Number.isNaN(expiresAt.getTime()) &&
      expiresAt.getTime() <= now.getTime()
    ) {
      return "expired";
    }
  }
  if (lastDelivery?.status === "failed") {
    return "failed";
  }
  if (integration.lastError.trim().length > 0) {
    return "degraded";
  }
  if (lastDelivery?.status === "delivered") {
    return "active";
  }
  return "degraded";
}
