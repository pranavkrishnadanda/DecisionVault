import { type CSSProperties, memo } from "react";
import type { DecisionRecord } from "@/domain/decision";

interface DecisionRowProps {
  decision: DecisionRecord;
  style?: CSSProperties;
}

function DecisionRowBase({ decision, style }: DecisionRowProps) {
  return (
    <div
      className="grid grid-cols-[1.2fr_1fr_0.8fr_1fr] gap-2 rounded-md border border-slate-200 bg-white px-3 py-2 text-sm"
      data-testid="decision-row"
      style={style}
    >
      <span className="truncate font-medium text-slate-900">{decision.id}</span>
      <span className="truncate text-slate-700">{decision.workflowName}</span>
      <span className="text-slate-700">{decision.status}</span>
      <span className="text-slate-500">
        {new Date(decision.updatedAt).toLocaleString()}
      </span>
    </div>
  );
}

export const DecisionRow = memo(DecisionRowBase);
