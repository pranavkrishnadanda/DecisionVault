import { useMutation, useQueryClient } from "@tanstack/react-query";
import { deleteSavedView } from "@/api/saved-views";
import type { SavedViewRecord } from "@/domain/saved-view";

export function useDeleteSavedViewMutation() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: deleteSavedView,
    onMutate: async (savedViewId: string) => {
      await queryClient.cancelQueries({
        queryKey: ["saved-views"],
      });

      const previousSavedViews = queryClient.getQueryData<SavedViewRecord[]>([
        "saved-views",
      ]);

      queryClient.setQueryData<SavedViewRecord[]>(["saved-views"], (current) =>
        (current ?? []).filter((view) => view.id !== savedViewId),
      );

      return { previousSavedViews };
    },
    onError: (_error, _savedViewId, context) => {
      if (context?.previousSavedViews) {
        queryClient.setQueryData(["saved-views"], context.previousSavedViews);
      }
    },
    onSettled: () => {
      void queryClient.invalidateQueries({
        queryKey: ["saved-views"],
      });
    },
  });
}
