import { apiFetch } from "@/api/client";
import type {
  DecisionTableColumnKey,
  TableDensity,
  TablePreferenceRecord,
  UpdateTablePreferenceInput,
} from "@/domain/table-preference";

interface TablePreferenceApiRecord {
  table: string;
  visible_columns: DecisionTableColumnKey[];
  column_order: DecisionTableColumnKey[];
  density: TableDensity;
}

function mapTablePreferenceApiRecord(
  payload: TablePreferenceApiRecord,
): TablePreferenceRecord {
  return {
    table: payload.table,
    visibleColumns: payload.visible_columns,
    columnOrder: payload.column_order,
    density: payload.density,
  };
}

export async function getTablePreference(
  table: string,
): Promise<TablePreferenceRecord> {
  const payload = await apiFetch<TablePreferenceApiRecord>(
    `/api/v1/table-preferences/${table}/`,
    {
      method: "GET",
    },
  );
  return mapTablePreferenceApiRecord(payload);
}

export async function updateTablePreference({
  table,
  payload,
}: UpdateTablePreferenceInput): Promise<TablePreferenceRecord> {
  const response = await apiFetch<TablePreferenceApiRecord>(
    `/api/v1/table-preferences/${table}/`,
    {
      method: "PUT",
      body: JSON.stringify({
        visible_columns: payload.visibleColumns,
        column_order: payload.columnOrder,
        density: payload.density,
      }),
    },
  );
  return mapTablePreferenceApiRecord(response);
}
