import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { act, renderHook, waitFor } from "@testing-library/react";
import type { ReactNode } from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { useSlackConnectMutation } from "@/hooks/use-integrations-query";

const mockGetSlackInstallUrl = vi.fn();

vi.mock("@/api/integrations", () => ({
  completeSlackOAuth: vi.fn(),
  createIntegration: vi.fn(),
  deleteIntegration: vi.fn(),
  getSlackInstallUrl: (...args: unknown[]) => mockGetSlackInstallUrl(...args),
  listIntegrationDeliveries: vi.fn(),
  listIntegrations: vi.fn(),
  listSlackChannels: vi.fn(),
  runSlackTestDelivery: vi.fn(),
  testIntegrationDelivery: vi.fn(),
  updateIntegration: vi.fn(),
}));

function createWrapper(client: QueryClient) {
  return function Wrapper({ children }: { children: ReactNode }) {
    return (
      <QueryClientProvider client={client}>{children}</QueryClientProvider>
    );
  };
}

describe("useSlackConnectMutation", () => {
  const originalSlackRedirectUri = process.env.NEXT_PUBLIC_SLACK_REDIRECT_URI;

  beforeEach(() => {
    mockGetSlackInstallUrl.mockReset();
    if (originalSlackRedirectUri === undefined) {
      delete process.env.NEXT_PUBLIC_SLACK_REDIRECT_URI;
    } else {
      process.env.NEXT_PUBLIC_SLACK_REDIRECT_URI = originalSlackRedirectUri;
    }
  });

  it("Given configured HTTPS redirect URI, when requesting install URL, then it uses env value", async () => {
    process.env.NEXT_PUBLIC_SLACK_REDIRECT_URI =
      "https://decisionvault.ngrok-free.app/oauth/slack/callback";
    mockGetSlackInstallUrl.mockResolvedValue(
      "https://slack.com/oauth/v2/authorize",
    );
    const queryClient = new QueryClient();

    const { result } = renderHook(() => useSlackConnectMutation(), {
      wrapper: createWrapper(queryClient),
    });

    act(() => {
      result.current.mutate({
        integrationId: "int-2",
        resumeStep: "triggers",
      });
    });

    await waitFor(() => {
      expect(mockGetSlackInstallUrl).toHaveBeenCalledWith(
        "int-2",
        "https://decisionvault.ngrok-free.app/oauth/slack/callback",
      );
    });
  });

  it("Given no configured redirect URI, when requesting install URL, then it falls back to canonical localhost callback", async () => {
    delete process.env.NEXT_PUBLIC_SLACK_REDIRECT_URI;
    mockGetSlackInstallUrl.mockResolvedValue(
      "https://slack.com/oauth/v2/authorize",
    );
    const queryClient = new QueryClient();

    const { result } = renderHook(() => useSlackConnectMutation(), {
      wrapper: createWrapper(queryClient),
    });

    act(() => {
      result.current.mutate({
        integrationId: "int-2",
        resumeStep: "triggers",
      });
    });

    await waitFor(() => {
      expect(mockGetSlackInstallUrl).toHaveBeenCalledWith(
        "int-2",
        "http://localhost:3000/oauth/slack/callback",
      );
    });
  });
});
