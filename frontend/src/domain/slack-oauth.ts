function decodeBase64Url(value: string): string | null {
  if (!value) {
    return null;
  }

  const normalized = value.replace(/-/g, "+").replace(/_/g, "/");
  const padding = normalized.length % 4;
  const padded =
    padding === 0 ? normalized : normalized + "=".repeat(4 - padding);

  try {
    return atob(padded);
  } catch {
    return null;
  }
}

export function resolveIntegrationIdFromSlackState(
  state: string | null,
): string | null {
  if (!state || state.trim().length === 0) {
    return null;
  }

  const payloadSegment = state.split(":")[0];
  const decodedPayload = decodeBase64Url(payloadSegment);
  if (!decodedPayload) {
    return null;
  }

  try {
    const parsed = JSON.parse(decodedPayload) as { integration_id?: unknown };
    if (typeof parsed.integration_id === "string") {
      const integrationId = parsed.integration_id.trim();
      return integrationId.length > 0 ? integrationId : null;
    }
    return null;
  } catch {
    return null;
  }
}
