import type { DecisionStatus } from "@/domain/decision";

export interface DecisionDetailRecord {
  id: string;
  title: string;
  description: string;
  status: DecisionStatus;
  priority: number;
  createdBy: string;
  metadata: Record<string, unknown>;
  workflowStartedAt: string | null;
  workflowCompletedAt: string | null;
  agentResult: Record<string, unknown>;
  agentError: string;
  createdAt: string;
  updatedAt: string;
}

export interface DecisionRetryResult {
  id: string;
  status: DecisionStatus;
  message: string;
}

export interface TimelineEvent {
  id: string;
  label: string;
  timestamp: string;
  description: string;
}

export function buildDecisionTimeline(
  decision: DecisionDetailRecord,
): TimelineEvent[] {
  const events: TimelineEvent[] = [
    {
      id: `${decision.id}-created`,
      label: "Created",
      timestamp: decision.createdAt,
      description: `Decision created by ${decision.createdBy}`,
    },
  ];

  if (decision.workflowStartedAt) {
    events.push({
      id: `${decision.id}-workflow-started`,
      label: "Workflow Started",
      timestamp: decision.workflowStartedAt,
      description: "Decision entered workflow processing",
    });
  }

  if (decision.workflowCompletedAt) {
    events.push({
      id: `${decision.id}-workflow-completed`,
      label: "Workflow Completed",
      timestamp: decision.workflowCompletedAt,
      description: `Workflow finished with status ${decision.status}`,
    });
  }

  events.push({
    id: `${decision.id}-updated`,
    label: "Last Updated",
    timestamp: decision.updatedAt,
    description: "Most recent persisted state update",
  });

  return events;
}
