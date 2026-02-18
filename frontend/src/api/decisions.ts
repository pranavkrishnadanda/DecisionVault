import { apiFetch } from "@/api/client";
import {
  type DecisionApiRecord,
  mapDecisionApiRecord,
} from "@/api/decision-contracts";
import type { DecisionRecord } from "@/domain/decision";

export async function listDecisions(): Promise<DecisionRecord[]> {
  const payload = await apiFetch<DecisionApiRecord[]>("/api/v1/decisions/", {
    method: "GET",
  });

  return payload.map(mapDecisionApiRecord);
}
