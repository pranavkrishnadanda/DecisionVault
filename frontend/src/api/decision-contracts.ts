import type { DecisionRecord } from "@/domain/decision";

export interface DecisionApiRecord {
  id: string;
  title: string;
  status: DecisionRecord["status"];
  updated_at: string;
}

export function mapDecisionApiRecord(item: DecisionApiRecord): DecisionRecord {
  return {
    id: item.id,
    workflowName: item.title,
    status: item.status,
    updatedAt: item.updated_at,
  };
}
