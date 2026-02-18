import { useQuery } from "@tanstack/react-query";
import { getDecisionDetail } from "@/api/decision-detail";

export function useDecisionDetailQuery(decisionId: string, enabled: boolean) {
  return useQuery({
    queryKey: ["decision", decisionId],
    queryFn: () => getDecisionDetail(decisionId),
    enabled,
    staleTime: 10_000,
    gcTime: 5 * 60_000,
    retry: 1,
    refetchOnWindowFocus: false,
  });
}
