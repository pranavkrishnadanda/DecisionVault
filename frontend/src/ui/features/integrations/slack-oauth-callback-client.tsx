"use client";

import { useRouter, useSearchParams } from "next/navigation";
import { useEffect, useRef } from "react";
import { resolveIntegrationIdFromSlackState } from "@/domain/slack-oauth";
import { useAccessControl } from "@/hooks/use-access-control";
import { useCompleteSlackOAuthMutation } from "@/hooks/use-integrations-query";
import { selectSessionToken, useAuthStore } from "@/state/auth-store";
import { AuthGate } from "@/ui/features/auth/auth-gate";

function buildCallbackRedirect(
  integrationId: string,
  status: "success" | "error",
) {
  return `/integrations?integrationId=${integrationId}&oauth=${status}`;
}

function resolveRedirectUri() {
  const configuredRedirectUri =
    process.env.NEXT_PUBLIC_SLACK_REDIRECT_URI?.trim() ?? "";
  if (
    configuredRedirectUri.length > 0 &&
    configuredRedirectUri !== "undefined" &&
    configuredRedirectUri !== "null"
  ) {
    return configuredRedirectUri;
  }
  return `${window.location.origin}/oauth/slack/callback`;
}

export function SlackOAuthCallbackClient() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const sessionToken = useAuthStore(selectSessionToken);
  const { isAccessHydrating, permissions } = useAccessControl();
  const completeSlackOAuthMutation = useCompleteSlackOAuthMutation();
  const hasProcessed = useRef(false);

  const isAuthenticated = Boolean(sessionToken) && !isAccessHydrating;
  const canManageIntegrations = permissions.canManageIntegrations;

  useEffect(() => {
    if (hasProcessed.current || !isAuthenticated || !canManageIntegrations) {
      return;
    }
    hasProcessed.current = true;

    const integrationId =
      searchParams.get("integration_id") ??
      resolveIntegrationIdFromSlackState(searchParams.get("state"));
    const oauthError = searchParams.get("error");
    const code = searchParams.get("code");

    if (
      !integrationId ||
      integrationId.trim().length === 0 ||
      oauthError ||
      !code
    ) {
      router.replace(buildCallbackRedirect(integrationId ?? "", "error"));
      return;
    }

    const redirectUri = resolveRedirectUri();
    void completeSlackOAuthMutation
      .mutateAsync({
        integrationId,
        code,
        redirectUri,
      })
      .then(() => {
        router.replace(buildCallbackRedirect(integrationId, "success"));
      })
      .catch(() => {
        router.replace(buildCallbackRedirect(integrationId, "error"));
      });
  }, [
    canManageIntegrations,
    completeSlackOAuthMutation,
    isAuthenticated,
    router,
    searchParams,
  ]);

  if (!isAuthenticated) {
    return (
      <AuthGate>
        <section />
      </AuthGate>
    );
  }

  if (!canManageIntegrations) {
    return (
      <AuthGate>
        <section className="rounded-xl border border-amber-300/50 bg-amber-50 p-6 text-slate-900">
          <h2 className="text-lg font-semibold">Access restricted</h2>
          <p className="mt-2 text-sm text-slate-700">
            Your role cannot manage Slack integrations in this organization.
          </p>
        </section>
      </AuthGate>
    );
  }

  return (
    <section className="rounded-xl border border-slate-200 bg-white p-6">
      <h2 className="text-lg font-semibold text-slate-900">
        Completing Slack connection
      </h2>
      <p className="mt-2 text-sm text-slate-600">
        Redirecting back to integrations...
      </p>
    </section>
  );
}
