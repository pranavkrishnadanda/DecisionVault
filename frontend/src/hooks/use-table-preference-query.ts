import { useQuery } from "@tanstack/react-query";
import { getTablePreference } from "@/api/table-preferences";

export function useTablePreferenceQuery(enabled: boolean, table: string) {
  return useQuery({
    queryKey: ["table-preference", table],
    queryFn: () => getTablePreference(table),
    enabled,
    staleTime: 60_000,
    gcTime: 10 * 60_000,
    retry: 2,
    refetchOnWindowFocus: false,
  });
}
