import { act, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { useAuthStore } from "@/state/auth-store";
import { DecisionsPageClient } from "@/ui/features/decisions/decisions-page-client";
import { OperatorShell } from "@/ui/layout/operator-shell";

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
    window.history.replaceState({}, "", "/decisions");
    useAuthStore.setState({ sessionToken: "jwt-token" });
    mockUseDecisionsQuery.mockReset();
    mockUseDecisionEvents.mockReset();
    vi.useRealTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
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
    expect(screen.getByTestId("decisions-header-icon")).toBeInTheDocument();
    expect(screen.getByTestId("decisions-live-indicator")).toBeInTheDocument();
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
    expect(mockUseDecisionsQuery).toHaveBeenCalledWith(
      false,
      expect.objectContaining({ limit: 100, offset: 0 }),
    );
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

  it("debounces search query before server filter refetch input", () => {
    vi.useFakeTimers();
    mockUseDecisionsQuery.mockReturnValue({
      data: [],
      isPending: false,
      isError: false,
      error: null,
      refetch: vi.fn(),
    });

    render(<DecisionsPageClient />);

    const searchBox = screen.getByRole("searchbox", {
      name: /search decisions/i,
    });
    fireEvent.change(searchBox, {
      target: { value: "fraud" },
    });

    const latestBeforeDebounce =
      mockUseDecisionsQuery.mock.calls[
        mockUseDecisionsQuery.mock.calls.length - 1
      ];
    expect(latestBeforeDebounce?.[1]).toEqual(
      expect.objectContaining({ q: undefined }),
    );

    act(() => {
      vi.advanceTimersByTime(300);
    });

    const latestAfterDebounce =
      mockUseDecisionsQuery.mock.calls[
        mockUseDecisionsQuery.mock.calls.length - 1
      ];
    expect(latestAfterDebounce?.[1]).toEqual(
      expect.objectContaining({ q: "fraud" }),
    );
  });

  it("syncs filter fields into URL query params", () => {
    mockUseDecisionsQuery.mockReturnValue({
      data: [],
      isPending: false,
      isError: false,
      error: null,
      refetch: vi.fn(),
    });

    render(<DecisionsPageClient />);

    fireEvent.change(screen.getByRole("combobox", { name: /status filter/i }), {
      target: { value: "failed" },
    });
    fireEvent.change(screen.getByLabelText(/from date/i), {
      target: { value: "2026-02-01" },
    });
    fireEvent.change(screen.getByLabelText(/to date/i), {
      target: { value: "2026-02-18" },
    });

    expect(window.location.search).toContain("status=failed");
    expect(window.location.search).toContain("from=2026-02-01");
    expect(window.location.search).toContain("to=2026-02-18");
  });

  it("hydrates filter values from URL query params on reload", () => {
    window.history.replaceState(
      {},
      "",
      "/decisions?q=fraud&status=failed&from=2026-02-01&to=2026-02-18",
    );

    mockUseDecisionsQuery.mockReturnValue({
      data: [],
      isPending: false,
      isError: false,
      error: null,
      refetch: vi.fn(),
    });

    render(<DecisionsPageClient />);

    expect(
      screen.getByRole("searchbox", { name: /search decisions/i }),
    ).toHaveValue("fraud");
    expect(
      screen.getByRole("combobox", { name: /status filter/i }),
    ).toHaveValue("failed");
    expect(screen.getByLabelText(/from date/i)).toHaveValue("2026-02-01");
    expect(screen.getByLabelText(/to date/i)).toHaveValue("2026-02-18");
  });

  it("shows active sidebar accent strip on decisions nav item", () => {
    mockUseDecisionsQuery.mockReturnValue({
      data: [],
      isPending: false,
      isError: false,
      error: null,
      refetch: vi.fn(),
    });

    render(
      <OperatorShell>
        <DecisionsPageClient />
      </OperatorShell>,
    );

    expect(screen.getByTestId("sidebar-active-decisions")).toBeInTheDocument();
  });
});
