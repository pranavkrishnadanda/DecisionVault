import { apiFetch } from "@/api/client";
import {
  type DecisionApiRecord,
  mapDecisionApiRecord,
} from "@/api/decision-contracts";
import type { DecisionRecord } from "@/domain/decision";

export interface DecisionListFilters {
  q?: string;
  status?: string;
  from?: string;
  to?: string;
  limit: number;
  offset: number;
}

function toDecisionsQueryString(filters: DecisionListFilters): string {
  const searchParams = new URLSearchParams();
  if (filters.q) {
    searchParams.set("q", filters.q);
  }
  if (filters.status) {
    searchParams.set("status", filters.status);
  }
  if (filters.from) {
    searchParams.set("from", filters.from);
  }
  if (filters.to) {
    searchParams.set("to", filters.to);
  }
  searchParams.set("limit", String(filters.limit));
  searchParams.set("offset", String(filters.offset));

  const query = searchParams.toString();
  return query ? `?${query}` : "";
}

export async function listDecisions(
  filters: DecisionListFilters,
): Promise<DecisionRecord[]> {
  const payload = await apiFetch<DecisionApiRecord[]>(
    `/api/v1/decisions/${toDecisionsQueryString(filters)}`,
    {
      method: "GET",
    },
  );

  return payload.map(mapDecisionApiRecord);
}
