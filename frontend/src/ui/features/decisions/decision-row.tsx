import Link from "next/link";
import { type CSSProperties, memo } from "react";
import type { DecisionRecord } from "@/domain/decision";
import type {
  DecisionTableColumnKey,
  TableDensity,
} from "@/domain/table-preference";
import { DecisionStatusPill } from "@/ui/features/decisions/decision-status-pill";

interface DecisionRowProps {
  decision: DecisionRecord;
  columns: DecisionTableColumnKey[];
  density: TableDensity;
  gridTemplateColumns: string;
  style?: CSSProperties;
}

function renderCell(decision: DecisionRecord, column: DecisionTableColumnKey) {
  if (column === "id") {
    return (
      <Link
        className="truncate font-medium text-slate-900 underline-offset-2 hover:underline"
        href={`/decisions/${decision.id}`}
      >
        {decision.id}
      </Link>
    );
  }

  if (column === "workflow") {
    return (
      <span className="truncate text-slate-700">{decision.workflowName}</span>
    );
  }

  if (column === "status") {
    return <DecisionStatusPill status={decision.status} />;
  }

  return (
    <span className="text-slate-500">
      {new Date(decision.updatedAt).toLocaleString()}
    </span>
  );
}

function DecisionRowBase({
  columns,
  decision,
  density,
  gridTemplateColumns,
  style,
}: DecisionRowProps) {
  const densityClass =
    density === "compact"
      ? "px-4 py-2 text-xs"
      : density === "spacious"
        ? "px-4 py-4 text-sm"
        : "px-4 py-3 text-sm";

  return (
    <div
      className={`grid gap-2 rounded-md border border-slate-200 bg-white shadow-sm transition duration-150 hover:-translate-y-[1px] hover:border-slate-300 hover:shadow-md ${densityClass}`}
      data-density={density}
      data-testid="decision-row"
      style={{
        ...style,
        gridTemplateColumns,
      }}
    >
      {columns.map((column) => (
        <div key={`${decision.id}:${column}`}>
          {renderCell(decision, column)}
        </div>
      ))}
    </div>
  );
}

export const DecisionRow = memo(DecisionRowBase);
