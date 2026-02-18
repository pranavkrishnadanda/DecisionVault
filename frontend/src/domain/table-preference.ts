export type DecisionTableColumnKey = "id" | "workflow" | "status" | "updated";

export type TableDensity = "compact" | "comfortable" | "spacious";

export interface TablePreferenceRecord {
  table: string;
  visibleColumns: DecisionTableColumnKey[];
  columnOrder: DecisionTableColumnKey[];
  density: TableDensity;
}

export interface UpdateTablePreferenceInput {
  table: string;
  payload: {
    visibleColumns: DecisionTableColumnKey[];
    columnOrder: DecisionTableColumnKey[];
    density: TableDensity;
  };
}

export const DECISIONS_TABLE_KEY = "decisions";

export const DECISIONS_DEFAULT_VISIBLE_COLUMNS: DecisionTableColumnKey[] = [
  "id",
  "workflow",
  "status",
  "updated",
];

export const DECISIONS_DEFAULT_COLUMN_ORDER: DecisionTableColumnKey[] = [
  "id",
  "workflow",
  "status",
  "updated",
];

export const DECISIONS_DEFAULT_DENSITY: TableDensity = "comfortable";

export const DECISIONS_COLUMN_LABELS: Record<DecisionTableColumnKey, string> = {
  id: "Decision ID",
  workflow: "Workflow",
  status: "Status",
  updated: "Updated",
};
