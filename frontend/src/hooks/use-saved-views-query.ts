import { useQuery } from "@tanstack/react-query";
import { listSavedViews } from "@/api/saved-views";

export function useSavedViewsQuery(enabled: boolean) {
  return useQuery({
    queryKey: ["saved-views"],
    queryFn: listSavedViews,
    enabled,
    staleTime: 30_000,
    gcTime: 10 * 60_000,
    retry: 1,
    refetchOnWindowFocus: false,
  });
}
