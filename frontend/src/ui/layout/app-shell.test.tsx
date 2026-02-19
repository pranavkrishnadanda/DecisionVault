import { fireEvent, render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it } from "vitest";
import { useAuthStore } from "@/state/auth-store";
import { AuthGate } from "@/ui/features/auth/auth-gate";
import { AppShell } from "@/ui/layout/app-shell";

describe("app shell", () => {
  beforeEach(() => {
    useAuthStore.setState({
      sessionToken: "jwt-token",
      accessContext: { role: "operator", organizationId: "org-1" },
      isAccessHydrating: false,
    });
    window.history.replaceState({}, "", "/decisions");
  });

  it("renders sidebar navigation for authenticated users", () => {
    render(
      <AppShell>
        <div>content</div>
      </AppShell>,
    );

    expect(
      screen.getByRole("navigation", { name: /primary/i }),
    ).toBeInTheDocument();
    expect(screen.getByText("Decisions")).toBeInTheDocument();
    expect(screen.getByText("Webhooks")).toBeInTheDocument();
    expect(screen.getByText("Integrations")).toBeInTheDocument();
    expect(screen.getByText("Settings")).toBeInTheDocument();
  });

  it("highlights active route link", () => {
    window.history.replaceState({}, "", "/webhooks");

    render(
      <AppShell>
        <div>content</div>
      </AppShell>,
    );

    expect(screen.getByTestId("sidebar-active-webhooks")).toBeInTheDocument();
    expect(
      screen.queryByTestId("sidebar-active-decisions"),
    ).not.toBeInTheDocument();
  });

  it("collapses and expands sidebar", () => {
    render(
      <AppShell>
        <div>content</div>
      </AppShell>,
    );

    const sidebar = screen.getByTestId("app-sidebar");
    expect(sidebar).toHaveAttribute("data-collapsed", "false");

    fireEvent.click(screen.getByRole("button", { name: /collapse sidebar/i }));
    expect(sidebar).toHaveAttribute("data-collapsed", "true");

    fireEvent.click(screen.getByRole("button", { name: /expand sidebar/i }));
    expect(sidebar).toHaveAttribute("data-collapsed", "false");
  });

  it("preserves auth gate blocking inside shell", () => {
    useAuthStore.setState({
      sessionToken: null,
      accessContext: null,
      isAccessHydrating: false,
    });

    render(
      <AppShell>
        <AuthGate>
          <div>secure content</div>
        </AuthGate>
      </AppShell>,
    );

    expect(screen.getByText(/authentication required/i)).toBeInTheDocument();
    expect(screen.queryByText("secure content")).not.toBeInTheDocument();
  });

  it("keeps stable active route on refresh render", () => {
    window.history.replaceState({}, "", "/settings");

    render(
      <AppShell>
        <div>content</div>
      </AppShell>,
    );

    expect(screen.getByTestId("sidebar-active-settings")).toBeInTheDocument();
  });
});
