import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  completeSlackOAuth,
  createIntegration,
  getSlackInstallUrl,
  listIntegrations,
  listSlackChannels,
  runSlackTestDelivery,
  testIntegrationDelivery,
  updateIntegration,
} from "@/api/integrations";
import type {
  CreateIntegrationInput,
  UpdateIntegrationPatch,
} from "@/domain/integration";

export function useIntegrationsQuery(enabled: boolean) {
  return useQuery({
    queryKey: ["integrations"],
    queryFn: listIntegrations,
    enabled,
    staleTime: 15_000,
    gcTime: 5 * 60_000,
    retry: 1,
    refetchOnWindowFocus: false,
  });
}

export function useSlackChannelsQuery(integrationId: string, enabled: boolean) {
  return useQuery({
    queryKey: ["integrations", integrationId, "slack", "channels"],
    queryFn: () => listSlackChannels(integrationId),
    enabled: enabled && integrationId.trim().length > 0,
    staleTime: 15_000,
    gcTime: 5 * 60_000,
    retry: 1,
    refetchOnWindowFocus: false,
  });
}

interface UpdateIntegrationMutationInput {
  integrationId: string;
  patch: UpdateIntegrationPatch;
}

export function useUpdateIntegrationMutation() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ integrationId, patch }: UpdateIntegrationMutationInput) =>
      updateIntegration(integrationId, patch),
    onSuccess: (updated) => {
      queryClient.setQueryData(["integrations"], (current: unknown) => {
        if (!Array.isArray(current)) {
          return current;
        }
        return current.map((item) => {
          if (
            !item ||
            typeof item !== "object" ||
            !("id" in item) ||
            (item as { id?: string }).id !== updated.id
          ) {
            return item;
          }
          return updated;
        });
      });
    },
  });
}

export function useCreateIntegrationMutation() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (input: CreateIntegrationInput) => createIntegration(input),
    onSuccess: () => {
      void queryClient.invalidateQueries({
        queryKey: ["integrations"],
      });
    },
  });
}

function resolveSlackRedirectUri() {
  if (typeof window === "undefined") {
    return "http://localhost:3000/oauth/slack/callback";
  }
  return `${window.location.origin}/oauth/slack/callback`;
}

interface SlackConnectMutationInput {
  integrationId: string;
  resumeStep?: "triggers";
}

export function useSlackConnectMutation() {
  return useMutation({
    mutationFn: (input: string | SlackConnectMutationInput) => {
      const integrationId =
        typeof input === "string" ? input : input.integrationId;
      const redirectUrl = new URL(resolveSlackRedirectUri());

      if (typeof input !== "string") {
        redirectUrl.searchParams.set("integration_id", input.integrationId);
        if (input.resumeStep) {
          redirectUrl.searchParams.set("step", input.resumeStep);
        }
      }

      return getSlackInstallUrl(integrationId, redirectUrl.toString());
    },
  });
}

interface CompleteSlackOAuthMutationInput {
  integrationId: string;
  code: string;
  redirectUri: string;
}

export function useCompleteSlackOAuthMutation() {
  return useMutation({
    mutationFn: (input: CompleteSlackOAuthMutationInput) =>
      completeSlackOAuth(input.integrationId, {
        code: input.code,
        redirectUri: input.redirectUri,
      }),
  });
}

export function useIntegrationTestDeliveryMutation() {
  return useMutation({
    mutationFn: (
      input: string | { integrationId: string; channelId: string },
    ) => {
      if (typeof input === "string") {
        return testIntegrationDelivery(input);
      }
      return runSlackTestDelivery(input.integrationId, input.channelId);
    },
  });
}
