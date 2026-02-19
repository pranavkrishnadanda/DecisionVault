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
  beforeEach(() => {
    mockReplace.mockReset();
    mockUseSearchParams.mockReset();
    mockUseCompleteSlackOAuthMutation.mockReset();
    mockUseAccessControl.mockReset();
    mockUseAuthStore.mockReset();

    mockUseSearchParams.mockReturnValue(
      new URLSearchParams("code=oauth-code&state=state-1&integration_id=int-2"),
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
  });

  it("completes oauth callback and resumes onboarding at trigger step", async () => {
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
          "http://localhost/oauth/slack/callback?integration_id=int-2",
      });
      expect(mockReplace).toHaveBeenCalledWith(
        "/integrations?onboarding=resume&integrationId=int-2&step=triggers&oauth=success",
      );
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
        "/integrations?onboarding=resume&integrationId=int-2&step=triggers&oauth=error",
      );
    });
  });

  it("blocks callback processing when auth is missing", () => {
    mockUseAuthStore.mockReturnValue(null);

    render(<SlackOAuthCallbackClient />);

    expect(screen.getByText(/authentication required/i)).toBeInTheDocument();
  });
});
