import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { useAuthStore } from "@/state/auth-store";
import { IntegrationsPageClient } from "@/ui/features/integrations/integrations-page-client";

const mockUseSearchParams = vi.fn();
const mockReplace = vi.fn();
const mockUseIntegrationsQuery = vi.fn();
const mockUseSlackConnectMutation = vi.fn();
const mockUseSlackChannelsQuery = vi.fn();
const mockUseCreateIntegrationMutation = vi.fn();
const mockUseIntegrationTestDeliveryMutation = vi.fn();
const mockUseIntegrationDeliveriesQuery = vi.fn();
const mockUseDeleteIntegrationMutation = vi.fn();

vi.mock("next/navigation", () => ({
  useSearchParams: () => mockUseSearchParams(),
  useRouter: () => ({ replace: mockReplace }),
}));

vi.mock("@/hooks/use-integrations-query", () => ({
  useIntegrationsQuery: (...args: unknown[]) =>
    mockUseIntegrationsQuery(...args),
  useSlackConnectMutation: (...args: unknown[]) =>
    mockUseSlackConnectMutation(...args),
  useSlackChannelsQuery: (...args: unknown[]) =>
    mockUseSlackChannelsQuery(...args),
  useCreateIntegrationMutation: (...args: unknown[]) =>
    mockUseCreateIntegrationMutation(...args),
  useIntegrationTestDeliveryMutation: (...args: unknown[]) =>
    mockUseIntegrationTestDeliveryMutation(...args),
  useIntegrationDeliveriesQuery: (...args: unknown[]) =>
    mockUseIntegrationDeliveriesQuery(...args),
  useUpdateIntegrationMutation: () => ({ mutate: vi.fn(), isPending: false }),
  useDeleteIntegrationMutation: (...args: unknown[]) =>
    mockUseDeleteIntegrationMutation(...args),
}));

describe("integrations page slack inline flow", () => {
  beforeEach(() => {
    mockUseSearchParams.mockReturnValue(new URLSearchParams());
    mockReplace.mockReset();
    useAuthStore.setState({
      sessionToken: "jwt-token",
      accessContext: { role: "operator", organizationId: "org-1" },
      isAccessHydrating: false,
    });

    mockUseIntegrationsQuery.mockReset();
    mockUseSlackConnectMutation.mockReset();
    mockUseSlackChannelsQuery.mockReset();
    mockUseCreateIntegrationMutation.mockReset();
    mockUseIntegrationTestDeliveryMutation.mockReset();
    mockUseIntegrationDeliveriesQuery.mockReset();
    mockUseDeleteIntegrationMutation.mockReset();

    mockUseIntegrationsQuery.mockReturnValue({
      data: [],
      isPending: false,
      isError: false,
      refetch: vi.fn(),
    });
    mockUseSlackConnectMutation.mockReturnValue({
      mutateAsync: vi
        .fn()
        .mockResolvedValue("https://slack.com/oauth/v2/authorize?state=abc"),
      isPending: false,
    });
    mockUseCreateIntegrationMutation.mockReturnValue({
      mutateAsync: vi.fn().mockResolvedValue({
        id: "int-1",
        name: "Slack Workspace",
        connectorType: "slack",
        config: { channel_id: "__pending__" },
        tokenExpiresAt: null,
        isActive: true,
        lastError: "",
        triggers: [],
        createdAt: "2026-02-19T00:00:00.000Z",
        updatedAt: "2026-02-19T00:00:00.000Z",
      }),
      isPending: false,
    });
    mockUseSlackChannelsQuery.mockReturnValue({
      data: [],
      isPending: false,
      isError: false,
    });
    mockUseIntegrationTestDeliveryMutation.mockReturnValue({
      mutateAsync: vi
        .fn()
        .mockResolvedValue({ accepted: true, deliveryId: "del-1" }),
      isPending: false,
    });
    mockUseIntegrationDeliveriesQuery.mockReturnValue({
      data: [],
      isPending: false,
      isError: false,
    });
    mockUseDeleteIntegrationMutation.mockReturnValue({
      mutate: vi.fn(),
      isPending: false,
    });
  });

  it("renders connect button when no Slack integration exists", () => {
    render(<IntegrationsPageClient />);

    expect(
      screen.getByRole("button", { name: /connect slack workspace/i }),
    ).toBeInTheDocument();
    expect(screen.getByText(/^disabled$/i)).toBeInTheDocument();
  });

  it("shows channel picker after oauth resume and hides internal params", async () => {
    mockUseSearchParams.mockReturnValue(
      new URLSearchParams(
        "onboarding=resume&integrationId=int-2&step=triggers&oauth=success",
      ),
    );
    mockUseIntegrationsQuery.mockReturnValue({
      data: [
        {
          id: "int-2",
          name: "Slack Workspace",
          connectorType: "slack",
          config: {},
          tokenExpiresAt: null,
          isActive: true,
          lastError: "",
          triggers: [],
          createdAt: "2026-02-19T00:00:00.000Z",
          updatedAt: "2026-02-19T00:00:00.000Z",
        },
      ],
      isPending: false,
      isError: false,
      refetch: vi.fn(),
    });
    mockUseSlackChannelsQuery.mockReturnValue({
      data: [{ id: "COPS", name: "ops-alerts" }],
      isPending: false,
      isError: false,
    });

    render(<IntegrationsPageClient />);

    expect(screen.getByLabelText(/slack channel/i)).toBeInTheDocument();
    await waitFor(() => {
      expect(mockReplace).toHaveBeenCalledWith("/integrations");
    });
    expect(screen.queryByText(/onboarding=resume/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/step=triggers/i)).not.toBeInTheDocument();
  });

  it("shows channel picker for silent oauth resume params", async () => {
    mockUseSearchParams.mockReturnValue(
      new URLSearchParams("integrationId=int-2&oauth=success"),
    );
    mockUseIntegrationsQuery.mockReturnValue({
      data: [
        {
          id: "int-2",
          name: "Slack Workspace",
          connectorType: "slack",
          config: {},
          tokenExpiresAt: null,
          isActive: true,
          lastError: "",
          triggers: [],
          createdAt: "2026-02-19T00:00:00.000Z",
          updatedAt: "2026-02-19T00:00:00.000Z",
        },
      ],
      isPending: false,
      isError: false,
      refetch: vi.fn(),
    });
    mockUseSlackChannelsQuery.mockReturnValue({
      data: [{ id: "COPS", name: "ops-alerts" }],
      isPending: false,
      isError: false,
    });

    render(<IntegrationsPageClient />);

    expect(screen.getByLabelText(/slack channel/i)).toBeInTheDocument();
    await waitFor(() => {
      expect(mockReplace).toHaveBeenCalledWith("/integrations");
    });
  });

  it("enables send test only after channel selection", () => {
    mockUseIntegrationsQuery.mockReturnValue({
      data: [
        {
          id: "int-2",
          name: "Slack Workspace",
          connectorType: "slack",
          config: {},
          tokenExpiresAt: null,
          isActive: true,
          lastError: "",
          triggers: [],
          createdAt: "2026-02-19T00:00:00.000Z",
          updatedAt: "2026-02-19T00:00:00.000Z",
        },
      ],
      isPending: false,
      isError: false,
      refetch: vi.fn(),
    });
    mockUseSlackChannelsQuery.mockReturnValue({
      data: [
        { id: "COPS", name: "ops-alerts" },
        { id: "CALERTS", name: "alerts" },
      ],
      isPending: false,
      isError: false,
    });

    render(<IntegrationsPageClient />);

    const sendButton = screen.getByRole("button", { name: /send test/i });
    expect(sendButton).toBeDisabled();

    fireEvent.change(screen.getByLabelText(/slack channel/i), {
      target: { value: "COPS" },
    });

    expect(sendButton).toBeEnabled();
  });

  it("does not fetch channels before oauth connection is complete", () => {
    mockUseIntegrationsQuery.mockReturnValue({
      data: [
        {
          id: "int-2",
          name: "Slack Workspace",
          connectorType: "slack",
          config: { channel_id: "__pending__" },
          tokenExpiresAt: null,
          isActive: true,
          lastError: "",
          triggers: [],
          createdAt: "2026-02-19T00:00:00.000Z",
          updatedAt: "2026-02-19T00:00:00.000Z",
        },
      ],
      isPending: false,
      isError: false,
      refetch: vi.fn(),
    });

    render(<IntegrationsPageClient />);

    expect(mockUseSlackChannelsQuery).toHaveBeenCalledWith("int-2", false);
  });

  it("renders add and remove integration actions for slack card", () => {
    const mutate = vi.fn();
    mockUseDeleteIntegrationMutation.mockReturnValue({
      mutate,
      isPending: false,
    });
    mockUseIntegrationsQuery.mockReturnValue({
      data: [
        {
          id: "int-2",
          name: "Slack Workspace",
          connectorType: "slack",
          config: {},
          tokenExpiresAt: "2026-02-20T00:00:00.000Z",
          isActive: true,
          lastError: "",
          triggers: [],
          createdAt: "2026-02-19T00:00:00.000Z",
          updatedAt: "2026-02-19T00:00:00.000Z",
        },
      ],
      isPending: false,
      isError: false,
      refetch: vi.fn(),
    });
    const confirmSpy = vi
      .spyOn(window, "confirm")
      .mockImplementation(() => true);

    render(<IntegrationsPageClient />);

    expect(
      screen.getByRole("button", { name: /add integration/i }),
    ).toBeInTheDocument();

    fireEvent.click(
      screen.getByRole("button", { name: /remove integration/i }),
    );

    expect(confirmSpy).toHaveBeenCalled();
    expect(mutate).toHaveBeenCalledWith("int-2");
  });

  it("shows slack active badge after test success", async () => {
    const mutateAsync = vi
      .fn()
      .mockResolvedValue({ accepted: true, deliveryId: "del-9" });
    mockUseIntegrationTestDeliveryMutation.mockReturnValue({
      mutateAsync,
      isPending: false,
    });
    mockUseIntegrationsQuery.mockReturnValue({
      data: [
        {
          id: "int-2",
          name: "Slack Workspace",
          connectorType: "slack",
          config: {},
          tokenExpiresAt: null,
          isActive: true,
          lastError: "",
          triggers: [],
          createdAt: "2026-02-19T00:00:00.000Z",
          updatedAt: "2026-02-19T00:00:00.000Z",
        },
      ],
      isPending: false,
      isError: false,
      refetch: vi.fn(),
    });
    mockUseSlackChannelsQuery.mockReturnValue({
      data: [{ id: "COPS", name: "ops-alerts" }],
      isPending: false,
      isError: false,
    });

    render(<IntegrationsPageClient />);

    fireEvent.change(screen.getByLabelText(/slack channel/i), {
      target: { value: "COPS" },
    });
    fireEvent.click(screen.getByRole("button", { name: /send test/i }));

    await waitFor(() => {
      expect(mutateAsync).toHaveBeenCalledWith({
        integrationId: "int-2",
        channelId: "COPS",
      });
      expect(screen.getAllByText(/slack active/i).length).toBeGreaterThan(0);
    });
  });
});
