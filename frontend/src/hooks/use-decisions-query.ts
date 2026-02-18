import { useQuery } from "@tanstack/react-query";
import { listDecisions } from "@/api/decisions";

export function useDecisionsQuery(enabled: boolean) {
  return useQuery({
    queryKey: ["decisions"],
    queryFn: listDecisions,
    enabled,
    staleTime: 15_000,
    gcTime: 5 * 60_000,
    retry: 2,
    refetchOnWindowFocus: false,
  });
}
