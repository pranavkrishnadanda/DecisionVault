import { type CSSProperties, memo } from "react";
import type { DecisionRecord } from "@/domain/decision";
import { DecisionStatusPill } from "@/ui/features/decisions/decision-status-pill";

interface DecisionRowProps {
  decision: DecisionRecord;
  style?: CSSProperties;
}

function DecisionRowBase({ decision, style }: DecisionRowProps) {
  return (
    <div
      className="grid grid-cols-[1.2fr_1fr_0.8fr_1fr] gap-2 rounded-md border border-slate-200 bg-white px-4 py-3 text-sm transition-colors hover:border-slate-300 hover:bg-slate-50"
      data-testid="decision-row"
      style={style}
    >
      <span className="truncate font-medium text-slate-900">{decision.id}</span>
      <span className="truncate text-slate-700">{decision.workflowName}</span>
      <DecisionStatusPill status={decision.status} />
      <span className="text-slate-500">
        {new Date(decision.updatedAt).toLocaleString()}
      </span>
    </div>
  );
}

export const DecisionRow = memo(DecisionRowBase);
