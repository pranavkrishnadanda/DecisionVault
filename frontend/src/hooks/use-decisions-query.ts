import { useQuery } from "@tanstack/react-query";
import { type DecisionListFilters, listDecisions } from "@/api/decisions";

export function useDecisionsQuery(
  enabled: boolean,
  filters: DecisionListFilters,
) {
  return useQuery({
    queryKey: ["decisions", filters],
    queryFn: () => listDecisions(filters),
    enabled,
    staleTime: 15_000,
    gcTime: 5 * 60_000,
    retry: 2,
    refetchOnWindowFocus: false,
  });
}
