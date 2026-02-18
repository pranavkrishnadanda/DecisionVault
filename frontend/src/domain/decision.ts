export type DecisionStatus =
  | "draft"
  | "pending"
  | "processing"
  | "completed"
  | "failed";

export interface DecisionRecord {
  id: string;
  workflowName: string;
  status: DecisionStatus;
  updatedAt: string;
}
