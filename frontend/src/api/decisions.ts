import { apiFetch } from "@/api/client";
import type { DecisionRecord } from "@/domain/decision";

interface DecisionListItem {
  id: string;
  title: string;
  status: DecisionRecord["status"];
  updated_at: string;
}

export async function listDecisions(): Promise<DecisionRecord[]> {
  const payload = await apiFetch<DecisionListItem[]>("/api/v1/decisions/", {
    method: "GET",
  });

  return payload.map((item) => ({
    id: item.id,
    workflowName: item.title,
    status: item.status,
    updatedAt: item.updated_at,
  }));
}
