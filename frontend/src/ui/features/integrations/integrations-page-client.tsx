"use client";

import { useSearchParams } from "next/navigation";
import { useEffect, useRef, useState } from "react";
import { resolveIntegrationHealth } from "@/domain/integration";
import { useAccessControl } from "@/hooks/use-access-control";
import {
  useCreateIntegrationMutation,
  useIntegrationsQuery,
  useIntegrationTestDeliveryMutation,
  useSlackChannelsQuery,
  useSlackConnectMutation,
  useUpdateIntegrationMutation,
} from "@/hooks/use-integrations-query";
import { selectSessionToken, useAuthStore } from "@/state/auth-store";
import { RetryPanel } from "@/ui/components/errors/retry-panel";
import { AuthGate } from "@/ui/features/auth/auth-gate";

function formatConnector(connectorType: string) {
  if (connectorType === "slack") {
    return "Slack";
  }
  if (connectorType === "teams") {
    return "Teams";
  }
  if (connectorType === "email") {
    return "Email";
  }
  return connectorType;
}

const ONBOARDING_TRIGGERS = [
  "decision.completed",
  "decision.failed",
  "webhook.failed",
] as const;

type FeedbackState = {
  type: "success" | "error";
  message: string;
} | null;

export function IntegrationsPageClient() {
  const searchParams = useSearchParams();
  const sessionToken = useAuthStore(selectSessionToken);
  const { isAccessHydrating, permissions } = useAccessControl();
  const isAuthenticated = Boolean(sessionToken) && !isAccessHydrating;
  const canReadIntegrations = permissions.canReadIntegrations;
  const canManageIntegrations = permissions.canManageIntegrations;

  const integrationsQuery = useIntegrationsQuery(
    isAuthenticated && canReadIntegrations,
  );
  const createIntegrationMutation = useCreateIntegrationMutation();
  const updateIntegrationMutation = useUpdateIntegrationMutation();
  const slackConnectMutation = useSlackConnectMutation();
  const [connectingIntegrationId, setConnectingIntegrationId] = useState("");
  const [feedback, setFeedback] = useState<FeedbackState>(null);
  const [isOnboardingOpen, setIsOnboardingOpen] = useState(false);
  const [onboardingStep, setOnboardingStep] = useState<1 | 2 | 3>(1);
  const [onboardingName, setOnboardingName] = useState("");
  const [selectedSlackChannelId, setSelectedSlackChannelId] = useState("");
  const [selectedTriggers, setSelectedTriggers] = useState<string[]>([]);
  const [createdIntegrationId, setCreatedIntegrationId] = useState<
    string | null
  >(null);
  const [testDeliveryError, setTestDeliveryError] = useState<string | null>(
    null,
  );
  const [completionDeliveryId, setCompletionDeliveryId] = useState<
    string | null
  >(null);
  const integrationTestDeliveryMutation = useIntegrationTestDeliveryMutation();
  const slackChannelsQuery = useSlackChannelsQuery(
    createdIntegrationId ?? "",
    isOnboardingOpen && onboardingStep === 2,
  );
  const hasAppliedResume = useRef(false);

  useEffect(() => {
    if (hasAppliedResume.current || !isAuthenticated || !canReadIntegrations) {
      return;
    }

    const onboarding = searchParams.get("onboarding");
    const integrationId = searchParams.get("integrationId");
    const step = searchParams.get("step");
    if (
      onboarding !== "resume" ||
      !integrationId ||
      integrationId.trim().length === 0 ||
      step !== "triggers"
    ) {
      return;
    }

    hasAppliedResume.current = true;
    setIsOnboardingOpen(true);
    setOnboardingStep(2);
    setCreatedIntegrationId(integrationId);
    setSelectedSlackChannelId("");
    setTestDeliveryError(null);
    setCompletionDeliveryId(null);

    const oauthStatus = searchParams.get("oauth");
    if (oauthStatus === "success") {
      setFeedback({
        type: "success",
        message: "Slack connected successfully. Continue with trigger setup.",
      });
    } else if (oauthStatus === "error") {
      setFeedback({
        type: "error",
        message: "Slack connection failed. Reconnect and retry.",
      });
    }

    const integration = (integrationsQuery.data ?? []).find(
      (item) => item.id === integrationId,
    );
    if (!integration) {
      return;
    }

    setOnboardingName(integration.name);
    const channelId =
      typeof integration.config.channel_id === "string"
        ? integration.config.channel_id
        : "";
    setSelectedSlackChannelId(channelId);
    setSelectedTriggers(
      integration.triggers.map((trigger) => trigger.eventType),
    );
  }, [
    canReadIntegrations,
    integrationsQuery.data,
    isAuthenticated,
    searchParams,
  ]);

  if (!isAuthenticated) {
    return (
      <AuthGate>
        <section />
      </AuthGate>
    );
  }

  if (!canReadIntegrations) {
    return (
      <AuthGate>
        <section className="rounded-xl border border-amber-300/50 bg-amber-50 p-6 text-slate-900">
          <h2 className="text-lg font-semibold">Access restricted</h2>
          <p className="mt-2 text-sm text-slate-700">
            Your role cannot access integrations in this organization.
          </p>
        </section>
      </AuthGate>
    );
  }

  if (integrationsQuery.isError) {
    return (
      <RetryPanel
        title="Integrations unavailable"
        message="Failed to load integrations data."
        ctaLabel="Retry loading integrations"
        onRetry={() => {
          void integrationsQuery.refetch();
        }}
      />
    );
  }

  const integrations = integrationsQuery.data ?? [];
  const hasRecords = integrations.length > 0;
  const isLoading = integrationsQuery.isPending;
  const canAdvanceOnboarding = onboardingName.trim().length > 0;
  const hasSelectedSlackChannel = selectedSlackChannelId.trim().length > 0;

  function openOnboarding() {
    setFeedback(null);
    setIsOnboardingOpen(true);
    setOnboardingStep(1);
    setOnboardingName("");
    setSelectedSlackChannelId("");
    setSelectedTriggers([]);
    setCreatedIntegrationId(null);
    setTestDeliveryError(null);
    setCompletionDeliveryId(null);
  }

  async function runTestDelivery(integrationId: string, channelId?: string) {
    try {
      const result = await integrationTestDeliveryMutation.mutateAsync(
        channelId ? { integrationId, channelId } : integrationId,
      );
      setTestDeliveryError(null);
      setCompletionDeliveryId(result.deliveryId);
      setOnboardingStep(3);
      setFeedback({
        type: "success",
        message: "Test delivery queued successfully.",
      });
      return true;
    } catch {
      const message = "Integration created, but test delivery failed.";
      setTestDeliveryError(message);
      setFeedback({
        type: "error",
        message,
      });
      return false;
    }
  }

  const healthLabels = integrations.reduce<Record<string, string>>(
    (result, integration) => {
      const health = resolveIntegrationHealth(integration);
      result[integration.id] = health;
      return result;
    },
    {},
  );

  return (
    <section className="space-y-6" data-testid="integrations-panel">
      {feedback && (
        <output
          aria-live="polite"
          className={
            feedback.type === "success"
              ? "rounded-xl border border-emerald-200 bg-emerald-50 p-3 text-sm text-emerald-900"
              : "rounded-xl border border-rose-200 bg-rose-50 p-3 text-sm text-rose-900"
          }
        >
          {feedback.message}
        </output>
      )}

      <header>
        <h2 className="text-3xl font-semibold tracking-tight text-slate-900">
          Integrations management
        </h2>
        <p className="mt-1 text-sm text-slate-600">
          Manage connector health, Slack OAuth, and trigger coverage.
        </p>
      </header>

      {isLoading && (
        <section className="rounded-xl border border-slate-200 bg-slate-50 p-4 text-sm text-slate-600">
          Loading integrations...
        </section>
      )}

      {!isLoading && !hasRecords && (
        <section className="rounded-xl border border-slate-200 bg-white p-4 text-sm text-slate-600">
          <p>No integrations configured yet.</p>
          <p className="mt-2 text-xs text-slate-500">
            Use onboarding to create your first Slack integration and activate
            triggers.
          </p>
          <button
            className="mt-3 rounded-md bg-slate-900 px-3 py-2 text-sm font-medium text-white disabled:cursor-not-allowed disabled:bg-slate-300"
            disabled={!canManageIntegrations}
            onClick={openOnboarding}
            type="button"
          >
            Start Slack onboarding
          </button>
        </section>
      )}

      {isOnboardingOpen && (
        <section className="rounded-xl border border-slate-200 bg-white p-4">
          <h3 className="text-lg font-semibold text-slate-900">
            Slack onboarding wizard
          </h3>
          <p className="mt-1 text-sm text-slate-600">
            Step {onboardingStep} of 3
          </p>

          {onboardingStep === 1 && (
            <div className="mt-4 space-y-3">
              <p className="text-sm text-slate-700">How this works</p>
              <p
                aria-label="integration name help"
                className="text-xs text-slate-500"
                role="tooltip"
              >
                Use a clear name so operators can identify this connector fast.
              </p>
              <label
                className="block text-sm font-medium text-slate-700"
                htmlFor="onboarding-name"
              >
                Integration name
              </label>
              <input
                className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
                id="onboarding-name"
                onChange={(event) => {
                  setOnboardingName(event.target.value);
                }}
                value={onboardingName}
              />
              <div className="flex gap-2">
                <button
                  className="rounded-md bg-slate-900 px-3 py-2 text-sm font-medium text-white disabled:cursor-not-allowed disabled:bg-slate-300"
                  disabled={!canAdvanceOnboarding}
                  onClick={() => {
                    setOnboardingStep(2);
                  }}
                  type="button"
                >
                  Next: Choose triggers
                </button>
                <button
                  className="rounded-md border border-slate-300 px-3 py-2 text-sm font-medium text-slate-700"
                  onClick={() => {
                    setIsOnboardingOpen(false);
                  }}
                  type="button"
                >
                  Cancel
                </button>
              </div>
            </div>
          )}

          {onboardingStep === 2 && (
            <div className="mt-4 space-y-3">
              <h4 className="text-sm font-semibold text-slate-900">
                Trigger setup walkthrough
              </h4>
              <p
                aria-label="trigger walkthrough help"
                className="text-xs text-slate-500"
                role="tooltip"
              >
                Choose one or more triggers to activate event delivery for this
                integration.
              </p>
              <div className="space-y-2">
                {ONBOARDING_TRIGGERS.map((eventType) => {
                  const checked = selectedTriggers.includes(eventType);
                  return (
                    <label
                      className="flex items-center gap-2 text-sm text-slate-700"
                      htmlFor={`onboarding-trigger-${eventType}`}
                      key={eventType}
                    >
                      <input
                        checked={checked}
                        id={`onboarding-trigger-${eventType}`}
                        onChange={() => {
                          setSelectedTriggers((current) => {
                            if (current.includes(eventType)) {
                              return current.filter(
                                (item) => item !== eventType,
                              );
                            }
                            return [...current, eventType];
                          });
                        }}
                        type="checkbox"
                      />
                      {eventType}
                    </label>
                  );
                })}
              </div>
              {createdIntegrationId && (
                <div className="space-y-2">
                  <label
                    className="block text-sm font-medium text-slate-700"
                    htmlFor="onboarding-slack-channel"
                  >
                    Slack channel
                  </label>
                  {slackChannelsQuery.isPending && (
                    <p className="text-sm text-slate-600">
                      Loading Slack channels...
                    </p>
                  )}
                  {slackChannelsQuery.isError && (
                    <p className="text-sm text-rose-700">
                      Failed to load Slack channels.
                    </p>
                  )}
                  {!slackChannelsQuery.isPending &&
                    !slackChannelsQuery.isError && (
                      <select
                        className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
                        id="onboarding-slack-channel"
                        onChange={(event) => {
                          setSelectedSlackChannelId(event.target.value);
                        }}
                        value={selectedSlackChannelId}
                      >
                        <option value="">Select a channel</option>
                        {(slackChannelsQuery.data ?? []).map((channel) => (
                          <option key={channel.id} value={channel.id}>
                            {channel.name}
                          </option>
                        ))}
                      </select>
                    )}
                </div>
              )}
              <div className="flex gap-2">
                <button
                  className="rounded-md bg-slate-900 px-3 py-2 text-sm font-medium text-white"
                  disabled={
                    !canManageIntegrations ||
                    createIntegrationMutation.isPending ||
                    slackConnectMutation.isPending
                  }
                  onClick={async () => {
                    setFeedback(null);
                    setTestDeliveryError(null);
                    try {
                      const created =
                        await createIntegrationMutation.mutateAsync({
                          name: onboardingName.trim(),
                          connectorType: "slack",
                          config: { channelId: "__pending__" },
                          triggers: selectedTriggers.map((eventType) => ({
                            eventType,
                            isActive: true,
                          })),
                        });
                      setCreatedIntegrationId(created.id);
                      const installUrl = await slackConnectMutation.mutateAsync(
                        {
                          integrationId: created.id,
                          resumeStep: "triggers",
                        },
                      );
                      window.open(installUrl, "_self");
                    } catch {
                      setFeedback({
                        type: "error",
                        message:
                          "Failed to start Slack OAuth. Retry onboarding.",
                      });
                    }
                  }}
                  type="button"
                >
                  Connect with Slack
                </button>
                <button
                  className="rounded-md bg-slate-900 px-3 py-2 text-sm font-medium text-white"
                  disabled={
                    !canManageIntegrations ||
                    (Boolean(createdIntegrationId) && !hasSelectedSlackChannel)
                  }
                  onClick={async () => {
                    setFeedback(null);
                    setTestDeliveryError(null);
                    if (createdIntegrationId) {
                      await runTestDelivery(
                        createdIntegrationId,
                        selectedSlackChannelId.trim(),
                      );
                      return;
                    }
                    try {
                      const created =
                        await createIntegrationMutation.mutateAsync({
                          name: onboardingName.trim(),
                          connectorType: "slack",
                          config: {
                            channelId: hasSelectedSlackChannel
                              ? selectedSlackChannelId.trim()
                              : "__pending__",
                          },
                          triggers: selectedTriggers.map((eventType) => ({
                            eventType,
                            isActive: true,
                          })),
                        });
                      setCreatedIntegrationId(created.id);
                      await runTestDelivery(
                        created.id,
                        hasSelectedSlackChannel
                          ? selectedSlackChannelId.trim()
                          : undefined,
                      );
                    } catch {
                      setFeedback({
                        type: "error",
                        message: "Failed to create integration. Try again.",
                      });
                    }
                  }}
                  type="button"
                >
                  Finish setup
                </button>
                <button
                  className="rounded-md border border-slate-300 px-3 py-2 text-sm font-medium text-slate-700"
                  onClick={() => {
                    setOnboardingStep(1);
                  }}
                  type="button"
                >
                  Back
                </button>
              </div>
              {testDeliveryError && createdIntegrationId && (
                <section className="rounded-md border border-rose-200 bg-rose-50 p-3">
                  <p className="text-sm text-rose-900">{testDeliveryError}</p>
                  <button
                    className="mt-2 rounded-md bg-slate-900 px-3 py-2 text-sm font-medium text-white"
                    onClick={async () => {
                      await runTestDelivery(
                        createdIntegrationId,
                        selectedSlackChannelId.trim(),
                      );
                    }}
                    type="button"
                  >
                    Retry test delivery
                  </button>
                </section>
              )}
            </div>
          )}

          {onboardingStep === 3 && (
            <div className="mt-4 space-y-3">
              <h4 className="text-base font-semibold text-slate-900">
                Slack onboarding complete
              </h4>
              <p className="text-sm text-slate-700">
                Test delivery queued successfully.
              </p>
              {completionDeliveryId && (
                <p className="text-xs text-slate-500">
                  Delivery reference: {completionDeliveryId}
                </p>
              )}
              <div className="flex gap-2">
                <button
                  className="rounded-md border border-slate-300 px-3 py-2 text-sm font-medium text-slate-700"
                  onClick={() => {
                    setIsOnboardingOpen(false);
                  }}
                  type="button"
                >
                  Close onboarding
                </button>
              </div>
            </div>
          )}
        </section>
      )}

      {!isLoading && hasRecords && (
        <ul className="grid gap-4 sm:grid-cols-1 xl:grid-cols-2">
          {integrations.map((integration) => {
            const healthLabel = healthLabels[integration.id] ?? "healthy";
            return (
              <li
                key={integration.id}
                className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm"
              >
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <div>
                    <h3 className="text-base font-semibold text-slate-900">
                      {integration.name}
                    </h3>
                    <p className="text-sm text-slate-600">
                      {formatConnector(integration.connectorType)}
                    </p>
                  </div>
                  <p
                    className="rounded-md border border-slate-300 px-2 py-1 text-xs uppercase tracking-wide text-slate-700"
                    data-testid={`integration-health-${integration.id}`}
                  >
                    {healthLabel}
                  </p>
                </div>

                {integration.lastError.trim().length > 0 && (
                  <p className="mt-3 rounded-md border border-amber-200 bg-amber-50 px-3 py-2 text-sm text-amber-900">
                    {integration.lastError}
                  </p>
                )}

                <section className="mt-4 space-y-2">
                  <h4 className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                    Trigger management
                  </h4>
                  <ul className="space-y-2">
                    {integration.triggers.length === 0 && (
                      <li className="rounded-md border border-slate-200 bg-slate-50 px-3 py-2 text-sm text-slate-600">
                        <p className="font-medium text-slate-900">
                          Trigger setup walkthrough
                        </p>
                        <p className="mt-1">No triggers configured.</p>
                        <p
                          aria-label="trigger walkthrough help"
                          className="mt-1 text-xs text-slate-500"
                          role="tooltip"
                        >
                          Use onboarding for first trigger selection, then
                          manage trigger activation in integration settings.
                        </p>
                      </li>
                    )}
                    {integration.triggers.map((trigger) => (
                      <li
                        key={trigger.id}
                        className="rounded-md border border-slate-200 px-3 py-2 text-sm"
                      >
                        <div className="flex items-center justify-between gap-2">
                          <span className="font-medium text-slate-900">
                            {trigger.eventType}
                          </span>
                          <span className="text-xs uppercase tracking-wide text-slate-600">
                            {trigger.isActive ? "active" : "inactive"}
                          </span>
                        </div>
                        {trigger.messageTemplate.trim().length > 0 && (
                          <p className="mt-1 text-xs text-slate-600">
                            {trigger.messageTemplate}
                          </p>
                        )}
                      </li>
                    ))}
                  </ul>
                </section>

                <div className="mt-4 flex flex-wrap gap-2">
                  <button
                    className="rounded-md bg-slate-900 px-3 py-2 text-sm font-medium text-white disabled:cursor-not-allowed disabled:bg-slate-300"
                    disabled={!canManageIntegrations}
                    onClick={() => {
                      setFeedback(null);
                      updateIntegrationMutation.mutate({
                        integrationId: integration.id,
                        patch: { isActive: !integration.isActive },
                      });
                    }}
                    type="button"
                  >
                    {integration.isActive
                      ? `Disable ${integration.name}`
                      : `Enable ${integration.name}`}
                  </button>

                  <button
                    className="rounded-md border border-slate-300 px-3 py-2 text-sm font-medium text-slate-700 disabled:cursor-not-allowed disabled:text-slate-400"
                    disabled={
                      integration.connectorType !== "slack" ||
                      !canManageIntegrations ||
                      slackConnectMutation.isPending
                    }
                    onClick={async () => {
                      setFeedback(null);
                      setConnectingIntegrationId(integration.id);
                      try {
                        const installUrl =
                          await slackConnectMutation.mutateAsync(
                            integration.id,
                          );
                        window.open(installUrl, "_self");
                      } catch {
                        setFeedback({
                          type: "error",
                          message:
                            "Failed to start Slack OAuth. Retry from integrations.",
                        });
                      } finally {
                        setConnectingIntegrationId("");
                      }
                    }}
                    type="button"
                  >
                    {connectingIntegrationId === integration.id
                      ? "Connecting..."
                      : `Connect Slack for ${integration.name}`}
                  </button>

                  <button
                    className="rounded-md border border-slate-300 px-3 py-2 text-sm text-slate-500"
                    disabled
                    type="button"
                  >
                    Test delivery unavailable
                  </button>
                </div>
              </li>
            );
          })}
        </ul>
      )}
    </section>
  );
}
