import { type ChangeEvent, useCallback, useRef } from "react";
import type {
  DecisionTableColumnKey,
  TableDensity,
} from "@/domain/table-preference";

interface DecisionToolbarProps {
  activeSavedViewId: string;
  canDeleteSavedView: boolean;
  density: TableDensity;
  isSavingTableSettings: boolean;
  isSavingView: boolean;
  isDeletingView: boolean;
  onDensityChange: (value: TableDensity) => void;
  onDeleteSavedView: () => void;
  onMoveColumnDown: (column: DecisionTableColumnKey) => void;
  onMoveColumnUp: (column: DecisionTableColumnKey) => void;
  onRefresh: () => void;
  onClearFilters: () => void;
  onSaveTableSettings: () => void;
  onSaveCurrentFilters: () => void;
  onSearchChange: (value: string) => void;
  onStatusChange: (value: string) => void;
  onToggleColumn: (column: DecisionTableColumnKey) => void;
  onFromDateChange: (value: string) => void;
  onToDateChange: (value: string) => void;
  onSavedViewSelect: (id: string) => void;
  savedViewOptions: Array<{ id: string; name: string }>;
  tableColumns: Array<{
    key: DecisionTableColumnKey;
    label: string;
    visible: boolean;
  }>;
  selectedStatus: string;
  fromDate: string;
  toDate: string;
  searchQuery: string;
}

export function DecisionToolbar({
  activeSavedViewId,
  canDeleteSavedView,
  density,
  fromDate,
  isDeletingView,
  isSavingTableSettings,
  isSavingView,
  onClearFilters,
  onDensityChange,
  onDeleteSavedView,
  onFromDateChange,
  onMoveColumnDown,
  onMoveColumnUp,
  onRefresh,
  onSaveTableSettings,
  onSaveCurrentFilters,
  onSearchChange,
  onSavedViewSelect,
  onStatusChange,
  onToggleColumn,
  onToDateChange,
  savedViewOptions,
  selectedStatus,
  tableColumns,
  searchQuery,
  toDate,
}: DecisionToolbarProps) {
  const tableSettingsRef = useRef<HTMLDetailsElement | null>(null);

  const handleSearchChange = useCallback(
    (event: ChangeEvent<HTMLInputElement>) => {
      onSearchChange(event.target.value);
    },
    [onSearchChange],
  );

  const clearFilters = useCallback(() => {
    onClearFilters();
  }, [onClearFilters]);

  const handleStatusChange = useCallback(
    (event: ChangeEvent<HTMLSelectElement>) => {
      onStatusChange(event.target.value);
    },
    [onStatusChange],
  );

  const handleFromDateChange = useCallback(
    (event: ChangeEvent<HTMLInputElement>) => {
      onFromDateChange(event.target.value);
    },
    [onFromDateChange],
  );

  const handleToDateChange = useCallback(
    (event: ChangeEvent<HTMLInputElement>) => {
      onToDateChange(event.target.value);
    },
    [onToDateChange],
  );

  const handleSavedViewChange = useCallback(
    (event: ChangeEvent<HTMLSelectElement>) => {
      onSavedViewSelect(event.target.value);
    },
    [onSavedViewSelect],
  );

  const handleDensityChange = useCallback(
    (event: ChangeEvent<HTMLSelectElement>) => {
      onDensityChange(event.target.value as TableDensity);
    },
    [onDensityChange],
  );

  const handleSaveTableSettings = useCallback(() => {
    onSaveTableSettings();
    if (tableSettingsRef.current) {
      tableSettingsRef.current.open = false;
    }
  }, [onSaveTableSettings]);

  return (
    <div className="flex flex-col gap-3 rounded-2xl border border-slate-200 bg-white p-3 shadow-sm">
      <div className="grid grid-cols-1 gap-2 lg:grid-cols-[minmax(0,1fr)_180px_170px_170px_180px]">
        <input
          aria-label="Search decisions"
          className="h-10 w-full rounded-md border border-slate-300 bg-white px-3 text-sm text-slate-700 outline-none ring-sky-200 transition focus:border-sky-300 focus:ring-2 placeholder:text-slate-400"
          onChange={handleSearchChange}
          placeholder="Search decisions"
          type="search"
          value={searchQuery}
        />

        <select
          aria-label="Status filter"
          className="h-10 rounded-md border border-slate-300 bg-white px-3 text-sm text-slate-700 outline-none ring-sky-200 transition focus:border-sky-300 focus:ring-2"
          onChange={handleStatusChange}
          value={selectedStatus}
        >
          <option value="">All statuses</option>
          <option value="draft">Draft</option>
          <option value="pending">Pending</option>
          <option value="processing">Processing</option>
          <option value="completed">Completed</option>
          <option value="failed">Failed</option>
        </select>

        <input
          aria-label="From date"
          className="h-10 rounded-md border border-slate-300 bg-white px-3 text-sm text-slate-700 outline-none ring-sky-200 transition focus:border-sky-300 focus:ring-2"
          onChange={handleFromDateChange}
          type="date"
          value={fromDate}
        />

        <input
          aria-label="To date"
          className="h-10 rounded-md border border-slate-300 bg-white px-3 text-sm text-slate-700 outline-none ring-sky-200 transition focus:border-sky-300 focus:ring-2"
          onChange={handleToDateChange}
          type="date"
          value={toDate}
        />

        <select
          aria-label="Saved views"
          className="h-10 rounded-md border border-slate-300 bg-white px-3 text-sm text-slate-700 outline-none ring-sky-200 transition focus:border-sky-300 focus:ring-2"
          onChange={handleSavedViewChange}
          value={activeSavedViewId}
        >
          <option value="">Saved views</option>
          {savedViewOptions.map((view) => (
            <option key={view.id} value={view.id}>
              {view.name}
            </option>
          ))}
        </select>
      </div>

      <div className="flex flex-wrap items-center justify-end gap-2">
        <details
          className="mr-auto relative"
          data-testid="table-settings-popover"
          ref={tableSettingsRef}
        >
          <summary className="inline-flex h-10 cursor-pointer list-none items-center justify-center rounded-md border border-slate-300 bg-white px-4 text-sm font-medium text-slate-700 transition hover:bg-slate-50">
            Table settings
          </summary>
          <div
            className="absolute left-0 top-full z-30 mt-2 w-[320px] rounded-md border border-slate-200 bg-white p-3 shadow-lg"
            data-testid="table-settings-panel"
          >
            <div className="space-y-2">
              <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                Columns
              </p>
              {tableColumns.map((column) => (
                <div
                  className="flex items-center justify-between gap-2"
                  key={column.key}
                >
                  <label className="inline-flex items-center gap-2 text-sm text-slate-700">
                    <input
                      aria-label={`Column ${column.label}`}
                      checked={column.visible}
                      onChange={() => onToggleColumn(column.key)}
                      type="checkbox"
                    />
                    {column.label}
                  </label>
                  <div className="flex items-center gap-1">
                    <button
                      aria-label={`Move ${column.label} up`}
                      className="h-7 rounded border border-slate-300 px-2 text-xs text-slate-700"
                      onClick={() => onMoveColumnUp(column.key)}
                      type="button"
                    >
                      Up
                    </button>
                    <button
                      aria-label={`Move ${column.label} down`}
                      className="h-7 rounded border border-slate-300 px-2 text-xs text-slate-700"
                      onClick={() => onMoveColumnDown(column.key)}
                      type="button"
                    >
                      Down
                    </button>
                  </div>
                </div>
              ))}
            </div>

            <div className="mt-3 space-y-2">
              <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                Density
              </p>
              <select
                aria-label="Density"
                className="h-9 w-full rounded-md border border-slate-300 bg-white px-2 text-sm text-slate-700"
                onChange={handleDensityChange}
                value={density}
              >
                <option value="compact">Compact</option>
                <option value="comfortable">Comfortable</option>
                <option value="spacious">Spacious</option>
              </select>
            </div>

            <button
              className="mt-3 inline-flex h-9 w-full items-center justify-center rounded-md bg-slate-900 px-3 text-sm font-medium text-white shadow-sm transition hover:bg-slate-800 disabled:opacity-60"
              disabled={isSavingTableSettings}
              onClick={handleSaveTableSettings}
              type="button"
            >
              {isSavingTableSettings ? "Saving..." : "Save table settings"}
            </button>
          </div>
        </details>

        <button
          className="inline-flex h-10 min-w-24 items-center justify-center whitespace-nowrap rounded-md border border-slate-300 bg-white px-4 text-sm font-medium text-slate-700 transition hover:bg-slate-50"
          disabled={!searchQuery && !selectedStatus && !fromDate && !toDate}
          onClick={clearFilters}
          type="button"
        >
          Clear
        </button>

        <button
          className="inline-flex h-10 min-w-40 items-center justify-center whitespace-nowrap rounded-md border border-slate-300 bg-white px-4 text-sm font-medium text-slate-700 transition hover:bg-slate-50 disabled:opacity-60"
          disabled={isSavingView}
          onClick={onSaveCurrentFilters}
          type="button"
        >
          {isSavingView ? "Saving..." : "Save current filters"}
        </button>

        <button
          className="inline-flex h-10 min-w-40 items-center justify-center whitespace-nowrap rounded-md border border-rose-300 bg-white px-4 text-sm font-medium text-rose-700 transition hover:bg-rose-50 disabled:opacity-60"
          disabled={!canDeleteSavedView || isDeletingView}
          onClick={onDeleteSavedView}
          type="button"
        >
          {isDeletingView ? "Deleting..." : "Delete saved view"}
        </button>

        <button
          className="inline-flex h-10 min-w-40 items-center justify-center whitespace-nowrap rounded-md bg-slate-900 px-4 text-sm font-medium text-white shadow-sm transition hover:bg-slate-800"
          onClick={onRefresh}
          type="button"
        >
          Refresh decisions
        </button>
      </div>
    </div>
  );
}
