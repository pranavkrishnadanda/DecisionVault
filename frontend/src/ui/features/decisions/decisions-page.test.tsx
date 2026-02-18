import { fireEvent, render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { useAuthStore } from "@/state/auth-store";
import { DecisionsPageClient } from "@/ui/features/decisions/decisions-page-client";

const mockUseDecisionsQuery = vi.fn();
const mockUseDecisionEvents = vi.fn();

vi.mock("@/hooks/use-decisions-query", () => ({
  useDecisionsQuery: (...args: unknown[]) => mockUseDecisionsQuery(...args),
}));
vi.mock("@/hooks/use-decision-events", () => ({
  useDecisionEvents: (...args: unknown[]) => mockUseDecisionEvents(...args),
}));

describe("decisions page", () => {
  beforeEach(() => {
    useAuthStore.setState({ sessionToken: "jwt-token" });
    mockUseDecisionsQuery.mockReset();
    mockUseDecisionEvents.mockReset();
  });

  it("renders skeletons during loading", () => {
    mockUseDecisionsQuery.mockReturnValue({
      data: undefined,
      isPending: true,
      isError: false,
      error: null,
      refetch: vi.fn(),
    });

    render(<DecisionsPageClient />);

    expect(screen.getByText(/decision operations/i)).toBeInTheDocument();
    expect(screen.getByText(/live updates are active/i)).toBeInTheDocument();
    expect(
      screen.getByPlaceholderText(/search decisions/i),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: /refresh decisions/i }),
    ).toBeInTheDocument();
    expect(screen.getAllByTestId("decision-skeleton-row")).toHaveLength(8);
  });

  it("renders rows when data is available", () => {
    mockUseDecisionsQuery.mockReturnValue({
      data: [
        {
          id: "d1",
          workflowName: "kyc",
          status: "draft",
          updatedAt: "2026-02-18T00:00:00.000Z",
        },
      ],
      isPending: false,
      isError: false,
      error: null,
      refetch: vi.fn(),
    });

    render(<DecisionsPageClient />);

    expect(screen.getByText("d1")).toBeInTheDocument();
    expect(screen.getByText("kyc")).toBeInTheDocument();
    expect(
      screen.getByTestId("decision-status-pill-draft"),
    ).toBeInTheDocument();
  });

  it("shows retry when query errors", () => {
    const refetch = vi.fn();
    mockUseDecisionsQuery.mockReturnValue({
      data: undefined,
      isPending: false,
      isError: true,
      error: new Error("boom"),
      refetch,
    });

    render(<DecisionsPageClient />);

    fireEvent.click(
      screen.getByRole("button", { name: /retry loading decisions/i }),
    );
    expect(refetch).toHaveBeenCalledTimes(1);
  });

  it("blocks access when token is missing", () => {
    useAuthStore.setState({ sessionToken: null });
    mockUseDecisionsQuery.mockReturnValue({
      data: [],
      isPending: false,
      isError: false,
      error: null,
      refetch: vi.fn(),
    });

    render(<DecisionsPageClient />);
    expect(screen.getByText(/authentication required/i)).toBeInTheDocument();
    expect(mockUseDecisionsQuery).toHaveBeenCalledWith(false);
    expect(mockUseDecisionEvents).toHaveBeenCalledWith(false);
  });

  it("virtualizes high-volume decision rows", () => {
    const decisions = Array.from({ length: 5000 }, (_, index) => ({
      id: `d-${index + 1}`,
      workflowName: "kyc",
      status: "draft" as const,
      updatedAt: "2026-02-18T00:00:00.000Z",
    }));

    mockUseDecisionsQuery.mockReturnValue({
      data: decisions,
      isPending: false,
      isError: false,
      error: null,
      refetch: vi.fn(),
    });

    render(<DecisionsPageClient />);

    const renderedRows = screen.getAllByTestId("decision-row");
    expect(renderedRows.length).toBeGreaterThan(0);
    expect(renderedRows.length).toBeLessThan(decisions.length);
  });

  it("starts decision event stream only when authenticated", () => {
    mockUseDecisionsQuery.mockReturnValue({
      data: [],
      isPending: false,
      isError: false,
      error: null,
      refetch: vi.fn(),
    });

    render(<DecisionsPageClient />);
    expect(mockUseDecisionEvents).toHaveBeenCalledWith(true);
  });

  it("shows empty state when no decisions are available", () => {
    mockUseDecisionsQuery.mockReturnValue({
      data: [],
      isPending: false,
      isError: false,
      error: null,
      refetch: vi.fn(),
    });

    render(<DecisionsPageClient />);

    expect(screen.getByText(/no decisions yet/i)).toBeInTheDocument();
    expect(
      screen.getByText(/new decisions will appear here in realtime/i),
    ).toBeInTheDocument();
  });

  it("refresh button triggers decision refetch", () => {
    const refetch = vi.fn();
    mockUseDecisionsQuery.mockReturnValue({
      data: [],
      isPending: false,
      isError: false,
      error: null,
      refetch,
    });

    render(<DecisionsPageClient />);
    fireEvent.click(screen.getByRole("button", { name: /refresh decisions/i }));

    expect(refetch).toHaveBeenCalledTimes(1);
  });
});
