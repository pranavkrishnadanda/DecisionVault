import { useMutation, useQueryClient } from "@tanstack/react-query";
import { createSavedView } from "@/api/saved-views";

export function useCreateSavedViewMutation() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: createSavedView,
    onSuccess: () => {
      void queryClient.invalidateQueries({
        queryKey: ["saved-views"],
      });
    },
  });
}
