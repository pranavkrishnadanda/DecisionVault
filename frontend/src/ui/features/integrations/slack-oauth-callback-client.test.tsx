import { render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { SlackOAuthCallbackClient } from "@/ui/features/integrations/slack-oauth-callback-client";

const mockReplace = vi.fn();
const mockUseSearchParams = vi.fn();
const mockUseCompleteSlackOAuthMutation = vi.fn();
const mockUseAccessControl = vi.fn();
const mockUseAuthStore = vi.fn();

vi.mock("next/navigation", () => ({
  useRouter: () => ({
    replace: mockReplace,
  }),
  useSearchParams: () => mockUseSearchParams(),
}));

vi.mock("@/hooks/use-integrations-query", () => ({
  useCompleteSlackOAuthMutation: (...args: unknown[]) =>
    mockUseCompleteSlackOAuthMutation(...args),
}));

vi.mock("@/hooks/use-access-control", () => ({
  useAccessControl: (...args: unknown[]) => mockUseAccessControl(...args),
}));

vi.mock("@/state/auth-store", () => ({
  selectSessionToken: "selectSessionToken",
  useAuthStore: (...args: unknown[]) => mockUseAuthStore(...args),
}));

describe("slack oauth callback", () => {
  const originalSlackRedirectUri = process.env.NEXT_PUBLIC_SLACK_REDIRECT_URI;

  beforeEach(() => {
    mockReplace.mockReset();
    mockUseSearchParams.mockReset();
    mockUseCompleteSlackOAuthMutation.mockReset();
    mockUseAccessControl.mockReset();
    mockUseAuthStore.mockReset();

    mockUseSearchParams.mockReturnValue(
      new URLSearchParams(
        "code=oauth-code&state=eyJpbnRlZ3JhdGlvbl9pZCI6ImludC0yIn0:abc123",
      ),
    );
    mockUseCompleteSlackOAuthMutation.mockReturnValue({
      mutateAsync: vi.fn().mockResolvedValue({}),
      isPending: false,
    });
    mockUseAccessControl.mockReturnValue({
      isAccessHydrating: false,
      permissions: {
        canManageIntegrations: true,
      },
    });
    mockUseAuthStore.mockReturnValue("jwt-token");
    if (originalSlackRedirectUri === undefined) {
      delete process.env.NEXT_PUBLIC_SLACK_REDIRECT_URI;
    } else {
      process.env.NEXT_PUBLIC_SLACK_REDIRECT_URI = originalSlackRedirectUri;
    }
  });

  it("completes oauth callback and resumes integrations inline flow", async () => {
    const mutateAsync = vi.fn().mockResolvedValue({});
    mockUseCompleteSlackOAuthMutation.mockReturnValue({
      mutateAsync,
      isPending: false,
    });

    render(<SlackOAuthCallbackClient />);

    await waitFor(() => {
      expect(mutateAsync).toHaveBeenCalledWith({
        integrationId: "int-2",
        code: "oauth-code",
        redirectUri: "http://localhost:3000/oauth/slack/callback",
      });
      expect(mockReplace).toHaveBeenCalledWith(
        "/integrations?integrationId=int-2&oauth=success",
      );
    });
  });

  it("uses configured redirect URI for oauth completion", async () => {
    process.env.NEXT_PUBLIC_SLACK_REDIRECT_URI =
      "https://decisionvault.ngrok-free.app/oauth/slack/callback";
    const mutateAsync = vi.fn().mockResolvedValue({});
    mockUseCompleteSlackOAuthMutation.mockReturnValue({
      mutateAsync,
      isPending: false,
    });

    render(<SlackOAuthCallbackClient />);

    await waitFor(() => {
      expect(mutateAsync).toHaveBeenCalledWith({
        integrationId: "int-2",
        code: "oauth-code",
        redirectUri:
          "https://decisionvault.ngrok-free.app/oauth/slack/callback",
      });
    });
  });

  it("redirects with oauth error when slack callback fails", async () => {
    const mutateAsync = vi.fn().mockRejectedValue(new Error("oauth failed"));
    mockUseCompleteSlackOAuthMutation.mockReturnValue({
      mutateAsync,
      isPending: false,
    });

    render(<SlackOAuthCallbackClient />);

    await waitFor(() => {
      expect(mockReplace).toHaveBeenCalledWith(
        "/integrations?integrationId=int-2&oauth=error",
      );
    });
  });

  it("blocks callback processing when auth is missing", () => {
    mockUseAuthStore.mockReturnValue(null);

    render(<SlackOAuthCallbackClient />);

    expect(screen.getByText(/authentication required/i)).toBeInTheDocument();
  });
});
