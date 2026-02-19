"use client";

import { useRouter, useSearchParams } from "next/navigation";
import { useEffect, useMemo, useRef, useState } from "react";
import { resolveSlackIntegrationStatus } from "@/domain/integration";
import { useAccessControl } from "@/hooks/use-access-control";
import {
  useCreateIntegrationMutation,
  useDeleteIntegrationMutation,
  useIntegrationDeliveriesQuery,
  useIntegrationsQuery,
  useIntegrationTestDeliveryMutation,
  useSlackChannelsQuery,
  useSlackConnectMutation,
} from "@/hooks/use-integrations-query";
import { selectSessionToken, useAuthStore } from "@/state/auth-store";
import { RetryPanel } from "@/ui/components/errors/retry-panel";
import { AuthGate } from "@/ui/features/auth/auth-gate";

type FeedbackState = {
  type: "success" | "error";
  message: string;
} | null;

function formatStatusLabel(
  status: ReturnType<typeof resolveSlackIntegrationStatus>,
) {
  if (status === "active") {
    return "Slack Active";
  }
  if (status === "degraded") {
    return "Degraded";
  }
  if (status === "expired") {
    return "Expired";
  }
  if (status === "disabled") {
    return "Disabled";
  }
  return "Failed";
}

export function IntegrationsPageClient() {
  const router = useRouter();
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
  const deleteIntegrationMutation = useDeleteIntegrationMutation();
  const slackConnectMutation = useSlackConnectMutation();
  const integrationTestDeliveryMutation = useIntegrationTestDeliveryMutation();

  const [feedback, setFeedback] = useState<FeedbackState>(null);
  const [resumeIntegrationId, setResumeIntegrationId] = useState<string | null>(
    null,
  );
  const [isResumeOauthSuccess, setIsResumeOauthSuccess] = useState(false);
  const [selectedSlackChannelId, setSelectedSlackChannelId] = useState("");
  const [didSendTestSucceed, setDidSendTestSucceed] = useState(false);

  const hasAppliedResume = useRef(false);

  const integrations = integrationsQuery.data ?? [];
  const slackIntegration = useMemo(
    () => integrations.find((item) => item.connectorType === "slack") ?? null,
    [integrations],
  );

  const slackIntegrationId = slackIntegration?.id ?? resumeIntegrationId ?? "";

  const slackChannelIdFromConfig =
    slackIntegration && typeof slackIntegration.config.channel_id === "string"
      ? slackIntegration.config.channel_id
      : "";
  const isSlackOAuthConnected = Boolean(
    slackIntegration &&
      (slackIntegration.tokenExpiresAt !== null ||
        (slackChannelIdFromConfig.trim().length > 0 &&
          slackChannelIdFromConfig !== "__pending__")),
  );
  const shouldFetchSlackChannels =
    slackIntegrationId.trim().length > 0 &&
    (isSlackOAuthConnected || isResumeOauthSuccess);
  const slackChannelsQuery = useSlackChannelsQuery(
    slackIntegrationId,
    shouldFetchSlackChannels,
  );
  const deliveriesQuery = useIntegrationDeliveriesQuery(
    slackIntegrationId,
    slackIntegrationId.trim().length > 0,
  );

  useEffect(() => {
    if (hasAppliedResume.current || !isAuthenticated || !canReadIntegrations) {
      return;
    }

    const onboarding = searchParams.get("onboarding");
    const integrationId = searchParams.get("integrationId");
    if (
      onboarding !== "resume" ||
      !integrationId ||
      integrationId.trim().length === 0
    ) {
      return;
    }

    hasAppliedResume.current = true;
    setResumeIntegrationId(integrationId);

    const oauthStatus = searchParams.get("oauth");
    if (oauthStatus === "success") {
      setIsResumeOauthSuccess(true);
      setFeedback({
        type: "success",
        message: "Slack connected. Select a channel and send a test.",
      });
    } else if (oauthStatus === "error") {
      setFeedback({
        type: "error",
        message: "Slack connection failed. Retry workspace connection.",
      });
    }

    router.replace("/integrations");
  }, [canReadIntegrations, isAuthenticated, router, searchParams]);

  useEffect(() => {
    if (!slackIntegration || selectedSlackChannelId.trim().length > 0) {
      return;
    }
    const channelId =
      typeof slackIntegration.config.channel_id === "string"
        ? slackIntegration.config.channel_id
        : "";
    if (channelId.trim().length > 0) {
      setSelectedSlackChannelId(channelId);
    }
  }, [selectedSlackChannelId, slackIntegration]);

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

  const lastDelivery = deliveriesQuery.data?.[0];
  const resolvedStatus = resolveSlackIntegrationStatus(
    {
      isActive: slackIntegration?.isActive ?? true,
      lastError: slackIntegration?.lastError ?? "",
      tokenExpiresAt: slackIntegration?.tokenExpiresAt ?? null,
    },
    lastDelivery,
  );
  const statusLabel = didSendTestSucceed
    ? "Slack Active"
    : formatStatusLabel(resolvedStatus);

  const channelName =
    (slackChannelsQuery.data ?? []).find(
      (item) => item.id === selectedSlackChannelId,
    )?.name ??
    (typeof slackIntegration?.config.channel_id === "string"
      ? slackIntegration.config.channel_id
      : "Not selected");

  const lastDeliveryLabel = lastDelivery?.createdAt
    ? new Date(lastDelivery.createdAt).toLocaleString()
    : "No deliveries yet";

  async function handleConnectSlackWorkspace() {
    setFeedback(null);
    try {
      const integrationId = slackIntegration?.id
        ? slackIntegration.id
        : (
            await createIntegrationMutation.mutateAsync({
              name: "Slack Workspace",
              connectorType: "slack",
              config: { channelId: "__pending__" },
              triggers: [],
            })
          ).id;

      setResumeIntegrationId(integrationId);
      const installUrl = await slackConnectMutation.mutateAsync({
        integrationId,
      });
      window.open(installUrl, "_self");
    } catch {
      setFeedback({
        type: "error",
        message: "Failed to connect Slack workspace.",
      });
    }
  }

  async function handleAddIntegration() {
    setFeedback(null);
    try {
      const suffix =
        integrations.filter((item) => item.connectorType === "slack").length +
        1;
      const created = await createIntegrationMutation.mutateAsync({
        name: `Slack Workspace ${suffix}`,
        connectorType: "slack",
        config: { channelId: "__pending__" },
        triggers: [],
      });

      setResumeIntegrationId(created.id);
      const installUrl = await slackConnectMutation.mutateAsync({
        integrationId: created.id,
      });
      window.open(installUrl, "_self");
    } catch {
      setFeedback({
        type: "error",
        message: "Failed to add integration.",
      });
    }
  }

  async function handleSendTest() {
    if (slackIntegrationId.trim().length === 0) {
      return;
    }
    const channelId = selectedSlackChannelId.trim();
    if (channelId.length === 0) {
      return;
    }

    setFeedback(null);
    setDidSendTestSucceed(false);
    try {
      await integrationTestDeliveryMutation.mutateAsync({
        integrationId: slackIntegrationId,
        channelId,
      });
      setDidSendTestSucceed(true);
      setFeedback({
        type: "success",
        message: "Slack Active",
      });
    } catch {
      setFeedback({
        type: "error",
        message: "Failed to send Slack test delivery.",
      });
    }
  }

  const isConnectPending =
    createIntegrationMutation.isPending || slackConnectMutation.isPending;
  const canSendTest =
    canManageIntegrations &&
    selectedSlackChannelId.trim().length > 0 &&
    !integrationTestDeliveryMutation.isPending;

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
          Connect Slack, choose a channel, and validate delivery health.
        </p>
        {slackIntegration && (
          <button
            className="mt-3 rounded-md bg-slate-900 px-3 py-2 text-sm font-medium text-white disabled:cursor-not-allowed disabled:bg-slate-300"
            disabled={!canManageIntegrations || isConnectPending}
            onClick={() => {
              void handleAddIntegration();
            }}
            type="button"
          >
            Add integration
          </button>
        )}
      </header>

      {integrationsQuery.isPending && (
        <section
          aria-busy="true"
          className="rounded-xl border border-slate-200 bg-slate-50 p-4"
        >
          <div className="h-4 w-40 animate-pulse rounded bg-slate-200" />
          <div className="mt-3 h-10 w-full animate-pulse rounded bg-slate-200" />
        </section>
      )}

      {!integrationsQuery.isPending && (
        <article className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div>
              <h3 className="text-base font-semibold text-slate-900">
                Slack integration
              </h3>
              <p className="text-sm text-slate-600">Workspace connection</p>
            </div>
            <span className="rounded-md border border-slate-300 px-2 py-1 text-xs uppercase tracking-wide text-slate-700">
              {statusLabel}
            </span>
          </div>

          <dl className="mt-4 grid gap-2 text-sm sm:grid-cols-2">
            <div>
              <dt className="text-slate-500">Channel</dt>
              <dd className="font-medium text-slate-900">{channelName}</dd>
            </div>
            <div>
              <dt className="text-slate-500">Last delivery</dt>
              <dd className="font-medium text-slate-900">
                {lastDeliveryLabel}
              </dd>
            </div>
          </dl>

          {slackIntegrationId.trim().length === 0 && (
            <div className="mt-4">
              <button
                className="rounded-md bg-slate-900 px-3 py-2 text-sm font-medium text-white disabled:cursor-not-allowed disabled:bg-slate-300"
                disabled={!canManageIntegrations || isConnectPending}
                onClick={() => {
                  void handleConnectSlackWorkspace();
                }}
                type="button"
              >
                {isConnectPending ? "Connecting..." : "Connect Slack Workspace"}
              </button>
            </div>
          )}

          {slackIntegrationId.trim().length > 0 && (
            <div className="mt-4 space-y-3">
              {slackChannelsQuery.isPending && (
                <p className="text-sm text-slate-600">
                  Loading Slack channels...
                </p>
              )}
              {slackChannelsQuery.isError && (
                <p className="rounded-md border border-rose-200 bg-rose-50 px-3 py-2 text-sm text-rose-900">
                  Failed to load Slack channels.
                </p>
              )}
              {!slackChannelsQuery.isPending && !slackChannelsQuery.isError && (
                <>
                  <label
                    className="block text-sm font-medium text-slate-700"
                    htmlFor="slack-channel"
                  >
                    Slack channel
                  </label>
                  <select
                    className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
                    id="slack-channel"
                    onChange={(event) => {
                      setSelectedSlackChannelId(event.target.value);
                      setDidSendTestSucceed(false);
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

                  <div className="flex gap-2">
                    <button
                      className="rounded-md border border-slate-300 px-3 py-2 text-sm font-medium text-slate-700 disabled:cursor-not-allowed disabled:text-slate-400"
                      disabled={!canManageIntegrations || isConnectPending}
                      onClick={() => {
                        void handleConnectSlackWorkspace();
                      }}
                      type="button"
                    >
                      Reconnect Slack Workspace
                    </button>
                    {slackIntegration && (
                      <button
                        className="rounded-md border border-rose-300 px-3 py-2 text-sm font-medium text-rose-700 disabled:cursor-not-allowed disabled:text-rose-300"
                        disabled={
                          !canManageIntegrations ||
                          deleteIntegrationMutation.isPending
                        }
                        onClick={() => {
                          if (!window.confirm("Remove integration?")) {
                            return;
                          }
                          deleteIntegrationMutation.mutate(slackIntegration.id);
                        }}
                        type="button"
                      >
                        Remove integration
                      </button>
                    )}
                    <button
                      className="rounded-md bg-slate-900 px-3 py-2 text-sm font-medium text-white disabled:cursor-not-allowed disabled:bg-slate-300"
                      disabled={!canSendTest}
                      onClick={() => {
                        void handleSendTest();
                      }}
                      type="button"
                    >
                      {integrationTestDeliveryMutation.isPending
                        ? "Sending test..."
                        : "Send Test"}
                    </button>
                  </div>
                </>
              )}
            </div>
          )}
        </article>
      )}
    </section>
  );
}
