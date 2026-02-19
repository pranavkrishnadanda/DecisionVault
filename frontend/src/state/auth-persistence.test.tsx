import { render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { refreshSessionRequest } from "@/api/session";
import { useAuthStore } from "@/state/auth-store";
import { AuthGate } from "@/ui/features/auth/auth-gate";

vi.mock("@/api/session", () => ({
  refreshSessionRequest: vi.fn(),
}));

describe("auth persistence", () => {
  beforeEach(() => {
    useAuthStore.setState({
      sessionToken: null,
      accessContext: null,
      isAccessHydrating: false,
    });
    vi.mocked(refreshSessionRequest).mockReset();
  });

  it("shows hydration skeleton before auth boot resolves", () => {
    useAuthStore.setState({
      sessionToken: null,
      accessContext: null,
      isAccessHydrating: true,
    });

    render(
      <AuthGate>
        <div>protected</div>
      </AuthGate>,
    );

    expect(screen.getByTestId("auth-hydration-skeleton")).toBeInTheDocument();
    expect(screen.queryByText("protected")).not.toBeInTheDocument();
  });

  it("survives reload by hydrating session via refresh", async () => {
    vi.mocked(refreshSessionRequest).mockResolvedValue("boot-access-token");

    await useAuthStore.getState().refreshSession();

    await waitFor(() => {
      expect(useAuthStore.getState().sessionToken).toBe("boot-access-token");
    });
  });
});
