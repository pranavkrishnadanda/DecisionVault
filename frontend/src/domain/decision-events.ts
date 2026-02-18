import type { DecisionRecord } from "@/domain/decision";

export const DECISION_UPSERT_EVENT = "decision.upsert";

export interface DecisionUpsertEvent {
  type: typeof DECISION_UPSERT_EVENT;
  decision: DecisionRecord;
}

export type DecisionEvent = DecisionUpsertEvent;

export function applyDecisionEvent(
  current: DecisionRecord[] | undefined,
  event: DecisionEvent,
): DecisionRecord[] {
  if (event.type !== DECISION_UPSERT_EVENT) {
    return current ?? [];
  }

  const existing = current ?? [];
  const next = [...existing];
  const index = next.findIndex((decision) => decision.id === event.decision.id);

  if (index >= 0) {
    next[index] = event.decision;
  } else {
    next.unshift(event.decision);
  }

  next.sort((left, right) => right.updatedAt.localeCompare(left.updatedAt));
  return next;
}
