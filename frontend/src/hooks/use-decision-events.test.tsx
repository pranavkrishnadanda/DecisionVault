import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { renderHook, waitFor } from "@testing-library/react";
import type { ReactNode } from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { ApiError } from "@/api/client";
import {
  DECISION_UPSERT_EVENT,
  type DecisionEvent,
} from "@/domain/decision-events";
import { useDecisionEvents } from "@/hooks/use-decision-events";
import { useAuthStore } from "@/state/auth-store";

const mockSubscribeToDecisionEvents = vi.fn();

vi.mock("@/api/decision-stream", () => ({
  subscribeToDecisionEvents: (...args: unknown[]) =>
    mockSubscribeToDecisionEvents(...args),
}));

describe("useDecisionEvents", () => {
  beforeEach(() => {
    useAuthStore.setState({ sessionToken: null });
    mockSubscribeToDecisionEvents.mockReset();
  });

  it("does not subscribe when disabled", () => {
    const queryClient = new QueryClient();
    const wrapper = ({ children }: { children: ReactNode }) => (
      <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
    );

    renderHook(() => useDecisionEvents(false), { wrapper });

    expect(mockSubscribeToDecisionEvents).not.toHaveBeenCalled();
  });

  it("upserts decision data from stream events", () => {
    useAuthStore.setState({ sessionToken: "jwt-token" });

    const queryClient = new QueryClient();
    queryClient.setQueryData(["decisions"], []);

    const wrapper = ({ children }: { children: ReactNode }) => (
      <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
    );

    mockSubscribeToDecisionEvents.mockImplementation(() => () => undefined);

    renderHook(() => useDecisionEvents(true), { wrapper });

    expect(mockSubscribeToDecisionEvents).toHaveBeenCalledTimes(1);
    const [subscriptionInput] = mockSubscribeToDecisionEvents.mock.calls[0] as [
      { onEvent: (event: DecisionEvent) => void },
    ];

    subscriptionInput.onEvent({
      type: DECISION_UPSERT_EVENT,
      decision: {
        id: "decision-1",
        workflowName: "kyc",
        status: "draft",
        updatedAt: "2026-02-18T00:00:00.000Z",
      },
    });

    expect(queryClient.getQueryData(["decisions"])).toEqual([
      {
        id: "decision-1",
        workflowName: "kyc",
        status: "draft",
        updatedAt: "2026-02-18T00:00:00.000Z",
      },
    ]);
  });

  it("clears auth session when stream returns unauthorized", async () => {
    useAuthStore.setState({ sessionToken: "expired-token" });

    const queryClient = new QueryClient();
    const wrapper = ({ children }: { children: ReactNode }) => (
      <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
    );

    mockSubscribeToDecisionEvents.mockImplementation(
      (input: { onError: (error: Error) => void }) => {
        input.onError(new ApiError("Unauthorized", 401, null));
        return () => undefined;
      },
    );

    renderHook(() => useDecisionEvents(true), { wrapper });

    await waitFor(() => {
      expect(useAuthStore.getState().sessionToken).toBeNull();
    });
  });
});
