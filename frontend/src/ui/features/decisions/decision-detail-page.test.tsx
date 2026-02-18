import { fireEvent, render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { useAuthStore } from "@/state/auth-store";
import { DecisionDetailPageClient } from "@/ui/features/decisions/decision-detail-page-client";

const mockUseDecisionDetailQuery = vi.fn();
const mockUseDecisionRetryMutation = vi.fn();

vi.mock("@/hooks/use-decision-detail-query", () => ({
  useDecisionDetailQuery: (...args: unknown[]) =>
    mockUseDecisionDetailQuery(...args),
}));

vi.mock("@/hooks/use-decision-retry-mutation", () => ({
  useDecisionRetryMutation: (...args: unknown[]) =>
    mockUseDecisionRetryMutation(...args),
}));

describe("decision detail page", () => {
  beforeEach(() => {
    useAuthStore.setState({ sessionToken: "jwt-token" });
    mockUseDecisionDetailQuery.mockReset();
    mockUseDecisionRetryMutation.mockReset();
  });

  it("blocks access when token is missing", () => {
    useAuthStore.setState({ sessionToken: null });
    mockUseDecisionDetailQuery.mockReturnValue({
      data: undefined,
      isPending: false,
      isError: false,
      error: null,
      refetch: vi.fn(),
    });
    mockUseDecisionRetryMutation.mockReturnValue({
      mutate: vi.fn(),
      isPending: false,
    });

    render(<DecisionDetailPageClient decisionId="dec-1" />);

    expect(screen.getByText(/authentication required/i)).toBeInTheDocument();
    expect(mockUseDecisionDetailQuery).toHaveBeenCalledWith("dec-1", false);
  });

  it("renders loading skeleton while fetching", () => {
    mockUseDecisionDetailQuery.mockReturnValue({
      data: undefined,
      isPending: true,
      isError: false,
      error: null,
      refetch: vi.fn(),
    });
    mockUseDecisionRetryMutation.mockReturnValue({
      mutate: vi.fn(),
      isPending: false,
    });

    render(<DecisionDetailPageClient decisionId="dec-1" />);

    expect(screen.getByTestId("decision-detail-skeleton")).toBeInTheDocument();
  });

  it("renders summary, workflow, audit, retry, and error inspection panels", () => {
    mockUseDecisionDetailQuery.mockReturnValue({
      data: {
        id: "dec-1",
        title: "Loan Risk Review",
        description: "Manual escalation for high-risk applicant",
        status: "failed",
        priority: 7,
        metadata: { source: "api" },
        createdBy: "operator",
        createdAt: "2026-02-18T10:00:00.000Z",
        updatedAt: "2026-02-18T10:20:00.000Z",
        workflowStartedAt: "2026-02-18T10:05:00.000Z",
        workflowCompletedAt: "2026-02-18T10:19:00.000Z",
        agentError: "score provider timeout",
        agentResult: { stage: "scoring", retries: 3 },
      },
      isPending: false,
      isError: false,
      error: null,
      refetch: vi.fn(),
    });
    mockUseDecisionRetryMutation.mockReturnValue({
      mutate: vi.fn(),
      isPending: false,
    });

    render(<DecisionDetailPageClient decisionId="dec-1" />);

    expect(
      screen.getByRole("heading", { name: /decision summary/i }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("heading", { name: /workflow state/i }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("heading", { name: /audit timeline/i }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("heading", { name: /retry controls/i }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("heading", { name: /error inspection/i }),
    ).toBeInTheDocument();
    expect(screen.getByText(/score provider timeout/i)).toBeInTheDocument();
  });

  it("shows retry panel on detail query error and retries", () => {
    const refetch = vi.fn();
    mockUseDecisionDetailQuery.mockReturnValue({
      data: undefined,
      isPending: false,
      isError: true,
      error: new Error("detail failed"),
      refetch,
    });
    mockUseDecisionRetryMutation.mockReturnValue({
      mutate: vi.fn(),
      isPending: false,
    });

    render(<DecisionDetailPageClient decisionId="dec-1" />);

    fireEvent.click(
      screen.getByRole("button", { name: /retry loading decision/i }),
    );
    expect(refetch).toHaveBeenCalledTimes(1);
  });

  it("calls retry mutation when decision status is failed", () => {
    const mutate = vi.fn();
    mockUseDecisionDetailQuery.mockReturnValue({
      data: {
        id: "dec-1",
        title: "Loan Risk Review",
        description: "Manual escalation for high-risk applicant",
        status: "failed",
        priority: 7,
        metadata: {},
        createdBy: "operator",
        createdAt: "2026-02-18T10:00:00.000Z",
        updatedAt: "2026-02-18T10:20:00.000Z",
        workflowStartedAt: "2026-02-18T10:05:00.000Z",
        workflowCompletedAt: "2026-02-18T10:19:00.000Z",
        agentError: "score provider timeout",
        agentResult: { stage: "scoring", retries: 3 },
      },
      isPending: false,
      isError: false,
      error: null,
      refetch: vi.fn(),
    });
    mockUseDecisionRetryMutation.mockReturnValue({
      mutate,
      isPending: false,
    });

    render(<DecisionDetailPageClient decisionId="dec-1" />);

    fireEvent.click(screen.getByRole("button", { name: /retry decision/i }));
    expect(mutate).toHaveBeenCalledWith("dec-1");
  });

  it("disables retry action for non-failed decisions", () => {
    mockUseDecisionDetailQuery.mockReturnValue({
      data: {
        id: "dec-1",
        title: "Loan Risk Review",
        description: "Manual escalation for high-risk applicant",
        status: "completed",
        priority: 7,
        metadata: {},
        createdBy: "operator",
        createdAt: "2026-02-18T10:00:00.000Z",
        updatedAt: "2026-02-18T10:20:00.000Z",
        workflowStartedAt: "2026-02-18T10:05:00.000Z",
        workflowCompletedAt: "2026-02-18T10:19:00.000Z",
        agentError: "",
        agentResult: { stage: "scoring", retries: 3 },
      },
      isPending: false,
      isError: false,
      error: null,
      refetch: vi.fn(),
    });
    mockUseDecisionRetryMutation.mockReturnValue({
      mutate: vi.fn(),
      isPending: false,
    });

    render(<DecisionDetailPageClient decisionId="dec-1" />);

    expect(
      screen.queryByRole("button", { name: /retry decision/i }),
    ).toBeNull();
    expect(
      screen.getByText(/only failed decisions can be retried/i),
    ).toBeInTheDocument();
  });
});
