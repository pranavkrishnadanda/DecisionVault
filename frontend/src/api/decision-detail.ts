import { apiFetch } from "@/api/client";
import {
  type DecisionDetailApiRecord,
  type DecisionRetryApiResponse,
  mapDecisionDetailApiRecord,
} from "@/api/decision-detail-contracts";
import type {
  DecisionDetailRecord,
  DecisionRetryResult,
} from "@/domain/decision-detail";

export async function getDecisionDetail(
  decisionId: string,
): Promise<DecisionDetailRecord> {
  const payload = await apiFetch<DecisionDetailApiRecord>(
    `/api/v1/decisions/${decisionId}/`,
    {
      method: "GET",
    },
  );

  return mapDecisionDetailApiRecord(payload);
}

export async function retryDecision(
  decisionId: string,
): Promise<DecisionRetryResult> {
  const payload = await apiFetch<DecisionRetryApiResponse>(
    `/api/v1/decisions/${decisionId}/retry/`,
    {
      method: "POST",
      body: JSON.stringify({}),
    },
  );

  return payload;
}
