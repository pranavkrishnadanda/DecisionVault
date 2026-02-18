import {
  QueryClient,
  QueryClientProvider,
  type QueryKey,
} from "@tanstack/react-query";
import { act, renderHook, waitFor } from "@testing-library/react";
import type { ReactNode } from "react";
import { describe, expect, it, vi } from "vitest";
import type { SavedViewRecord } from "@/domain/saved-view";
import { useDeleteSavedViewMutation } from "@/hooks/use-delete-saved-view-mutation";

const mockDeleteSavedView = vi.fn();

vi.mock("@/api/saved-views", () => ({
  deleteSavedView: (...args: unknown[]) => mockDeleteSavedView(...args),
}));

const SAVED_VIEWS_QUERY_KEY: QueryKey = ["saved-views"];

function createWrapper(client: QueryClient) {
  return function Wrapper({ children }: { children: ReactNode }) {
    return (
      <QueryClientProvider client={client}>{children}</QueryClientProvider>
    );
  };
}

describe("useDeleteSavedViewMutation", () => {
  it("removes deleted view from cache immediately", async () => {
    const queryClient = new QueryClient();
    const initialViews: SavedViewRecord[] = [
      {
        id: "view-1",
        name: "Pending",
        filters: { status: "pending" },
        createdAt: "2026-02-18T00:00:00.000Z",
        updatedAt: "2026-02-18T00:00:00.000Z",
      },
      {
        id: "view-2",
        name: "Failed",
        filters: { status: "failed" },
        createdAt: "2026-02-18T00:00:00.000Z",
        updatedAt: "2026-02-18T00:00:00.000Z",
      },
    ];

    queryClient.setQueryData(SAVED_VIEWS_QUERY_KEY, initialViews);

    mockDeleteSavedView.mockResolvedValue(undefined);

    const { result } = renderHook(() => useDeleteSavedViewMutation(), {
      wrapper: createWrapper(queryClient),
    });

    act(() => {
      result.current.mutate("view-1");
    });

    await waitFor(() => {
      const cachedAfterMutate = queryClient.getQueryData<SavedViewRecord[]>(
        SAVED_VIEWS_QUERY_KEY,
      );
      expect(cachedAfterMutate).toEqual([
        expect.objectContaining({ id: "view-2" }),
      ]);
    });

    expect(mockDeleteSavedView).toHaveBeenCalledWith(
      "view-1",
      expect.anything(),
    );
  });
});
