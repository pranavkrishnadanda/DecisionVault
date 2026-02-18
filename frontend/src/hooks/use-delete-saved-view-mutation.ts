import { useMutation, useQueryClient } from "@tanstack/react-query";
import { deleteSavedView } from "@/api/saved-views";

export function useDeleteSavedViewMutation() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: deleteSavedView,
    onSuccess: () => {
      void queryClient.invalidateQueries({
        queryKey: ["saved-views"],
      });
    },
  });
}
