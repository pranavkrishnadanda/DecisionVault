import type {
  DecisionDetailRecord,
  DecisionRetryResult,
} from "@/domain/decision-detail";

export interface DecisionDetailApiRecord {
  id: string;
  title: string;
  description: string;
  status: DecisionDetailRecord["status"];
  priority: number;
  created_by: string;
  metadata: Record<string, unknown>;
  workflow_started_at: string | null;
  workflow_completed_at: string | null;
  agent_result: Record<string, unknown>;
  agent_error: string;
  created_at: string;
  updated_at: string;
}

export interface DecisionRetryApiResponse {
  id: string;
  status: DecisionRetryResult["status"];
  message: string;
}

export function mapDecisionDetailApiRecord(
  item: DecisionDetailApiRecord,
): DecisionDetailRecord {
  return {
    id: item.id,
    title: item.title,
    description: item.description,
    status: item.status,
    priority: item.priority,
    createdBy: item.created_by,
    metadata: item.metadata,
    workflowStartedAt: item.workflow_started_at,
    workflowCompletedAt: item.workflow_completed_at,
    agentResult: item.agent_result,
    agentError: item.agent_error,
    createdAt: item.created_at,
    updatedAt: item.updated_at,
  };
}
