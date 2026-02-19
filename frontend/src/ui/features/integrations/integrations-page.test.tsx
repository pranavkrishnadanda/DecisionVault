import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { useAuthStore } from "@/state/auth-store";
import { IntegrationsPageClient } from "@/ui/features/integrations/integrations-page-client";

const mockUseSearchParams = vi.fn();
const mockUseIntegrationsQuery = vi.fn();
const mockUseUpdateIntegrationMutation = vi.fn();
const mockUseSlackConnectMutation = vi.fn();
const mockUseSlackChannelsQuery = vi.fn();
const mockUseCreateIntegrationMutation = vi.fn();
const mockUseIntegrationTestDeliveryMutation = vi.fn();

vi.mock("next/navigation", () => ({
  useSearchParams: () => mockUseSearchParams(),
}));

vi.mock("@/hooks/use-integrations-query", () => ({
  useIntegrationsQuery: (...args: unknown[]) =>
    mockUseIntegrationsQuery(...args),
  useUpdateIntegrationMutation: (...args: unknown[]) =>
    mockUseUpdateIntegrationMutation(...args),
  useSlackConnectMutation: (...args: unknown[]) =>
    mockUseSlackConnectMutation(...args),
  useSlackChannelsQuery: (...args: unknown[]) =>
    mockUseSlackChannelsQuery(...args),
  useCreateIntegrationMutation: (...args: unknown[]) =>
    mockUseCreateIntegrationMutation(...args),
  useIntegrationTestDeliveryMutation: (...args: unknown[]) =>
    mockUseIntegrationTestDeliveryMutation(...args),
}));

describe("integrations page", () => {
  beforeEach(() => {
    mockUseSearchParams.mockReturnValue(new URLSearchParams());
    useAuthStore.setState({
      sessionToken: "jwt-token",
      accessContext: { role: "operator", organizationId: "org-1" },
      isAccessHydrating: false,
    });

    mockUseIntegrationsQuery.mockReset();
    mockUseUpdateIntegrationMutation.mockReset();
    mockUseSlackConnectMutation.mockReset();
    mockUseSlackChannelsQuery.mockReset();
    mockUseCreateIntegrationMutation.mockReset();
    mockUseIntegrationTestDeliveryMutation.mockReset();

    mockUseUpdateIntegrationMutation.mockReturnValue({
      mutate: vi.fn(),
      isPending: false,
    });
    mockUseSlackConnectMutation.mockReturnValue({
      mutateAsync: vi.fn(),
      isPending: false,
    });
    mockUseCreateIntegrationMutation.mockReturnValue({
      mutateAsync: vi.fn(),
      isPending: false,
    });
    mockUseSlackChannelsQuery.mockReturnValue({
      data: [],
      isPending: false,
      isError: false,
    });
    mockUseIntegrationTestDeliveryMutation.mockReturnValue({
      mutateAsync: vi.fn(),
      isPending: false,
    });
  });

  it("blocks access when token is missing", () => {
    useAuthStore.setState({
      sessionToken: null,
      accessContext: null,
      isAccessHydrating: false,
    });
    mockUseIntegrationsQuery.mockReturnValue({
      data: [],
      isPending: false,
      isError: false,
      refetch: vi.fn(),
    });

    render(<IntegrationsPageClient />);

    expect(screen.getByText(/authentication required/i)).toBeInTheDocument();
    expect(mockUseIntegrationsQuery).toHaveBeenCalledWith(false);
  });

  it("renders integrations, trigger states, and health indicators", () => {
    mockUseIntegrationsQuery.mockReturnValue({
      data: [
        {
          id: "int-healthy",
          name: "Slack Ops",
          connectorType: "slack",
          config: { channel_id: "COPS" },
          tokenExpiresAt: "2099-02-19T00:00:00.000Z",
          isActive: true,
          lastError: "",
          triggers: [
            {
              id: "t1",
              eventType: "decision.completed",
              messageTemplate: "done",
              isActive: true,
              createdAt: "2026-02-19T00:00:00.000Z",
              updatedAt: "2026-02-19T00:00:00.000Z",
            },
          ],
          createdAt: "2026-02-19T00:00:00.000Z",
          updatedAt: "2026-02-19T00:00:00.000Z",
        },
        {
          id: "int-degraded",
          name: "Slack Alerts",
          connectorType: "slack",
          config: { channel_id: "CALERTS" },
          tokenExpiresAt: null,
          isActive: true,
          lastError: "Slack timeout",
          triggers: [
            {
              id: "t2",
              eventType: "webhook.failed",
              messageTemplate: "fail",
              isActive: false,
              createdAt: "2026-02-19T00:00:00.000Z",
              updatedAt: "2026-02-19T00:00:00.000Z",
            },
          ],
          createdAt: "2026-02-19T00:00:00.000Z",
          updatedAt: "2026-02-19T00:00:00.000Z",
        },
      ],
      isPending: false,
      isError: false,
      refetch: vi.fn(),
    });

    render(<IntegrationsPageClient />);

    expect(screen.getByText("Slack Ops")).toBeInTheDocument();
    expect(screen.getByText("Slack Alerts")).toBeInTheDocument();
    expect(screen.getByText(/decision\.completed/i)).toBeInTheDocument();
    expect(screen.getByText(/webhook\.failed/i)).toBeInTheDocument();
    expect(
      screen.getByTestId("integration-health-int-healthy"),
    ).toHaveTextContent(/healthy/i);
    expect(
      screen.getByTestId("integration-health-int-degraded"),
    ).toHaveTextContent(/degraded/i);
    expect(
      screen.getAllByRole("button", { name: /test delivery unavailable/i }),
    ).toHaveLength(2);
  });

  it("toggles integration active state", () => {
    const mutate = vi.fn();
    mockUseIntegrationsQuery.mockReturnValue({
      data: [
        {
          id: "int-1",
          name: "Slack Ops",
          connectorType: "slack",
          config: { channel_id: "COPS" },
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
    mockUseUpdateIntegrationMutation.mockReturnValue({
      mutate,
      isPending: false,
    });

    render(<IntegrationsPageClient />);
    fireEvent.click(screen.getByRole("button", { name: /disable slack ops/i }));

    expect(mutate).toHaveBeenCalledWith({
      integrationId: "int-1",
      patch: { isActive: false },
    });
  });

  it("starts slack oauth connect flow", async () => {
    const mutateAsync = vi
      .fn()
      .mockResolvedValue("https://slack.com/oauth/v2/authorize?state=abc");
    mockUseIntegrationsQuery.mockReturnValue({
      data: [
        {
          id: "int-1",
          name: "Slack Ops",
          connectorType: "slack",
          config: { channel_id: "COPS" },
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
    mockUseSlackConnectMutation.mockReturnValue({
      mutateAsync,
      isPending: false,
    });

    const openSpy = vi.spyOn(window, "open").mockImplementation(() => null);

    render(<IntegrationsPageClient />);
    fireEvent.click(
      screen.getByRole("button", { name: /connect slack for slack ops/i }),
    );

    await waitFor(() => {
      expect(mutateAsync).toHaveBeenCalledWith("int-1");
      expect(openSpy).toHaveBeenCalledWith(
        "https://slack.com/oauth/v2/authorize?state=abc",
        "_self",
      );
    });
  });

  it("shows empty-state onboarding CTA", () => {
    mockUseIntegrationsQuery.mockReturnValue({
      data: [],
      isPending: false,
      isError: false,
      refetch: vi.fn(),
    });

    render(<IntegrationsPageClient />);

    expect(
      screen.getByText(/no integrations configured yet/i),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: /start slack onboarding/i }),
    ).toBeInTheDocument();
  });

  it("connects to slack from wizard step 2 by auto-creating integration and redirecting to oauth", async () => {
    const createMutateAsync = vi.fn().mockResolvedValue({
      id: "int-2",
      name: "Fraud Alerts",
      connectorType: "slack",
      config: { channel_id: "CALERTS" },
      tokenExpiresAt: null,
      isActive: true,
      lastError: "",
      triggers: [],
      createdAt: "2026-02-19T00:00:00.000Z",
      updatedAt: "2026-02-19T00:00:00.000Z",
    });
    const slackConnectMutateAsync = vi
      .fn()
      .mockResolvedValue("https://slack.com/oauth/v2/authorize?state=abc");

    mockUseCreateIntegrationMutation.mockReturnValue({
      mutateAsync: createMutateAsync,
      isPending: false,
    });
    mockUseSlackConnectMutation.mockReturnValue({
      mutateAsync: slackConnectMutateAsync,
      isPending: false,
    });
    mockUseIntegrationsQuery.mockReturnValue({
      data: [],
      isPending: false,
      isError: false,
      refetch: vi.fn(),
    });

    const openSpy = vi.spyOn(window, "open").mockImplementation(() => null);

    render(<IntegrationsPageClient />);

    fireEvent.click(
      screen.getByRole("button", { name: /start slack onboarding/i }),
    );
    fireEvent.change(screen.getByLabelText(/^integration name$/i), {
      target: { value: "Fraud Alerts" },
    });
    fireEvent.click(
      screen.getByRole("button", { name: /next: choose triggers/i }),
    );
    fireEvent.click(
      screen.getByRole("checkbox", { name: /decision\.completed/i }),
    );
    fireEvent.click(
      screen.getByRole("button", { name: /connect with slack/i }),
    );

    await waitFor(() => {
      expect(createMutateAsync).toHaveBeenCalledWith({
        name: "Fraud Alerts",
        connectorType: "slack",
        config: { channelId: "__pending__" },
        triggers: [
          {
            eventType: "decision.completed",
            isActive: true,
          },
        ],
      });
      expect(slackConnectMutateAsync).toHaveBeenCalledWith({
        integrationId: "int-2",
        resumeStep: "triggers",
      });
      expect(openSpy).toHaveBeenCalledWith(
        "https://slack.com/oauth/v2/authorize?state=abc",
        "_self",
      );
    });
  });

  it("resumes onboarding at trigger step after slack callback", async () => {
    const createMutateAsync = vi.fn();
    const testDeliveryMutateAsync = vi.fn().mockResolvedValue({
      accepted: true,
      deliveryId: "delivery-2",
    });
    mockUseSearchParams.mockReturnValue(
      new URLSearchParams(
        "onboarding=resume&integrationId=int-2&step=triggers&oauth=success",
      ),
    );
    mockUseCreateIntegrationMutation.mockReturnValue({
      mutateAsync: createMutateAsync,
      isPending: false,
    });
    mockUseIntegrationTestDeliveryMutation.mockReturnValue({
      mutateAsync: testDeliveryMutateAsync,
      isPending: false,
    });
    mockUseIntegrationsQuery.mockReturnValue({
      data: [
        {
          id: "int-2",
          name: "Fraud Alerts",
          connectorType: "slack",
          config: { channel_id: "CALERTS" },
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

    expect(
      screen.getByRole("heading", { name: /slack onboarding wizard/i }),
    ).toBeInTheDocument();
    expect(screen.getByText(/step 2 of 3/i)).toBeInTheDocument();
    expect(
      screen.getByText(/slack connected successfully/i),
    ).toBeInTheDocument();

    fireEvent.click(
      screen.getByRole("checkbox", { name: /decision\.completed/i }),
    );
    fireEvent.click(screen.getByRole("button", { name: /finish setup/i }));

    await waitFor(() => {
      expect(createMutateAsync).not.toHaveBeenCalled();
      expect(testDeliveryMutateAsync).toHaveBeenCalledWith({
        integrationId: "int-2",
        channelId: "CALERTS",
      });
      expect(
        screen.getByRole("heading", { name: /slack onboarding complete/i }),
      ).toBeInTheDocument();
    });
  });

  it("opens onboarding wizard and creates slack integration with trigger setup walkthrough", async () => {
    const createMutateAsync = vi.fn().mockResolvedValue({
      id: "int-2",
      name: "Fraud Alerts",
      connectorType: "slack",
      config: { channel_id: "CALERTS" },
      tokenExpiresAt: null,
      isActive: true,
      lastError: "",
      triggers: [],
      createdAt: "2026-02-19T00:00:00.000Z",
      updatedAt: "2026-02-19T00:00:00.000Z",
    });
    const testDeliveryMutateAsync = vi.fn().mockResolvedValue({
      accepted: true,
      deliveryId: "delivery-1",
    });
    mockUseCreateIntegrationMutation.mockReturnValue({
      mutateAsync: createMutateAsync,
      isPending: false,
    });
    mockUseIntegrationTestDeliveryMutation.mockReturnValue({
      mutateAsync: testDeliveryMutateAsync,
      isPending: false,
    });
    mockUseIntegrationsQuery.mockReturnValue({
      data: [],
      isPending: false,
      isError: false,
      refetch: vi.fn(),
    });

    render(<IntegrationsPageClient />);

    fireEvent.click(
      screen.getByRole("button", { name: /start slack onboarding/i }),
    );

    expect(
      screen.getByRole("heading", { name: /slack onboarding wizard/i }),
    ).toBeInTheDocument();
    expect(screen.getByText(/step 1 of 3/i)).toBeInTheDocument();
    expect(screen.getByText(/how this works/i)).toBeInTheDocument();
    expect(
      screen.getByRole("tooltip", { name: /integration name help/i }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("tooltip", { name: /integration name help/i }),
    ).toBeInTheDocument();

    fireEvent.change(screen.getByLabelText(/^integration name$/i), {
      target: { value: "Fraud Alerts" },
    });
    fireEvent.click(
      screen.getByRole("button", { name: /next: choose triggers/i }),
    );

    expect(screen.getByText(/step 2 of 3/i)).toBeInTheDocument();
    fireEvent.click(
      screen.getByRole("checkbox", { name: /decision\.completed/i }),
    );
    fireEvent.click(screen.getByRole("button", { name: /finish setup/i }));

    await waitFor(() => {
      expect(createMutateAsync).toHaveBeenCalledWith({
        name: "Fraud Alerts",
        connectorType: "slack",
        config: { channelId: "__pending__" },
        triggers: [
          {
            eventType: "decision.completed",
            isActive: true,
          },
        ],
      });
      expect(testDeliveryMutateAsync).toHaveBeenCalledWith("int-2");
    });

    expect(
      screen.getByRole("heading", {
        name: /slack onboarding complete/i,
      }),
    ).toBeInTheDocument();
    expect(
      screen.getAllByText(/test delivery queued successfully/i).length,
    ).toBeGreaterThan(0);
  });

  it("shows error feedback when onboarding submission fails", async () => {
    const mutateAsync = vi.fn().mockRejectedValue(new Error("create failed"));
    mockUseCreateIntegrationMutation.mockReturnValue({
      mutateAsync,
      isPending: false,
    });
    mockUseIntegrationsQuery.mockReturnValue({
      data: [],
      isPending: false,
      isError: false,
      refetch: vi.fn(),
    });

    render(<IntegrationsPageClient />);

    fireEvent.click(
      screen.getByRole("button", { name: /start slack onboarding/i }),
    );
    fireEvent.change(screen.getByLabelText(/^integration name$/i), {
      target: { value: "Fraud Alerts" },
    });
    fireEvent.click(
      screen.getByRole("button", { name: /next: choose triggers/i }),
    );
    fireEvent.click(screen.getByRole("button", { name: /finish setup/i }));

    await waitFor(() => {
      expect(
        screen.getByText(/failed to create integration\. try again\./i),
      ).toBeInTheDocument();
    });
  });

  it("shows error recovery path when test delivery fails and allows retry", async () => {
    const createMutateAsync = vi.fn().mockResolvedValue({
      id: "int-2",
      name: "Fraud Alerts",
      connectorType: "slack",
      config: { channel_id: "CALERTS" },
      tokenExpiresAt: null,
      isActive: true,
      lastError: "",
      triggers: [],
      createdAt: "2026-02-19T00:00:00.000Z",
      updatedAt: "2026-02-19T00:00:00.000Z",
    });
    const testDeliveryMutateAsync = vi
      .fn()
      .mockRejectedValueOnce(new Error("queue failed"))
      .mockResolvedValueOnce({
        accepted: true,
        deliveryId: "delivery-2",
      });
    mockUseCreateIntegrationMutation.mockReturnValue({
      mutateAsync: createMutateAsync,
      isPending: false,
    });
    mockUseIntegrationTestDeliveryMutation.mockReturnValue({
      mutateAsync: testDeliveryMutateAsync,
      isPending: false,
    });
    mockUseIntegrationsQuery.mockReturnValue({
      data: [],
      isPending: false,
      isError: false,
      refetch: vi.fn(),
    });

    render(<IntegrationsPageClient />);

    fireEvent.click(
      screen.getByRole("button", { name: /start slack onboarding/i }),
    );
    fireEvent.change(screen.getByLabelText(/^integration name$/i), {
      target: { value: "Fraud Alerts" },
    });
    fireEvent.click(
      screen.getByRole("button", { name: /next: choose triggers/i }),
    );
    fireEvent.click(screen.getByRole("button", { name: /finish setup/i }));

    await waitFor(() => {
      expect(
        screen.getAllByText(/integration created, but test delivery failed/i)
          .length,
      ).toBeGreaterThan(0);
    });

    fireEvent.click(
      screen.getByRole("button", { name: /retry test delivery/i }),
    );

    await waitFor(() => {
      expect(testDeliveryMutateAsync).toHaveBeenCalledTimes(2);
      expect(
        screen.getByRole("heading", { name: /slack onboarding complete/i }),
      ).toBeInTheDocument();
    });
  });

  it("shows trigger setup walkthrough for integrations missing triggers", () => {
    mockUseIntegrationsQuery.mockReturnValue({
      data: [
        {
          id: "int-without-trigger",
          name: "Slack Ops",
          connectorType: "slack",
          config: { channel_id: "COPS" },
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

    expect(screen.getByText(/trigger setup walkthrough/i)).toBeInTheDocument();
    expect(
      screen.getByRole("tooltip", { name: /trigger walkthrough help/i }),
    ).toBeInTheDocument();
  });

  it("shows slack channel selector loading state on resume", () => {
    mockUseSearchParams.mockReturnValue(
      new URLSearchParams(
        "onboarding=resume&integrationId=int-2&step=triggers&oauth=success",
      ),
    );
    mockUseIntegrationsQuery.mockReturnValue({
      data: [
        {
          id: "int-2",
          name: "Fraud Alerts",
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
      data: [],
      isPending: true,
      isError: false,
    });

    render(<IntegrationsPageClient />);

    expect(screen.getByText(/loading slack channels/i)).toBeInTheDocument();
  });

  it("shows slack channel selector error state on resume", () => {
    mockUseSearchParams.mockReturnValue(
      new URLSearchParams(
        "onboarding=resume&integrationId=int-2&step=triggers&oauth=success",
      ),
    );
    mockUseIntegrationsQuery.mockReturnValue({
      data: [
        {
          id: "int-2",
          name: "Fraud Alerts",
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
      data: [],
      isPending: false,
      isError: true,
    });

    render(<IntegrationsPageClient />);

    expect(
      screen.getByText(/failed to load slack channels/i),
    ).toBeInTheDocument();
  });

  it("renders slack channel dropdown and requires selection before finish", async () => {
    const testDeliveryMutateAsync = vi.fn().mockResolvedValue({
      accepted: true,
      deliveryId: "delivery-12",
    });
    mockUseSearchParams.mockReturnValue(
      new URLSearchParams(
        "onboarding=resume&integrationId=int-2&step=triggers&oauth=success",
      ),
    );
    mockUseIntegrationsQuery.mockReturnValue({
      data: [
        {
          id: "int-2",
          name: "Fraud Alerts",
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
        { id: "CALERTS", name: "fraud-alerts" },
      ],
      isPending: false,
      isError: false,
    });
    mockUseIntegrationTestDeliveryMutation.mockReturnValue({
      mutateAsync: testDeliveryMutateAsync,
      isPending: false,
    });

    render(<IntegrationsPageClient />);

    expect(screen.getByLabelText(/slack channel/i)).toBeInTheDocument();
    const finishButton = screen.getByRole("button", { name: /finish setup/i });
    expect(finishButton).toBeDisabled();

    fireEvent.change(screen.getByLabelText(/slack channel/i), {
      target: { value: "COPS" },
    });
    fireEvent.click(
      screen.getByRole("checkbox", { name: /decision\.completed/i }),
    );
    expect(finishButton).toBeEnabled();
    fireEvent.click(finishButton);

    await waitFor(() => {
      expect(testDeliveryMutateAsync).toHaveBeenCalledWith({
        integrationId: "int-2",
        channelId: "COPS",
      });
    });
  });
});
