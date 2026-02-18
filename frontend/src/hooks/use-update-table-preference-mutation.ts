import { useMutation, useQueryClient } from "@tanstack/react-query";
import { updateTablePreference } from "@/api/table-preferences";

export function useUpdateTablePreferenceMutation() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: updateTablePreference,
    onSuccess: (result) => {
      queryClient.setQueryData(["table-preference", result.table], result);
    },
  });
}
