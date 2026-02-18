import { type ChangeEvent, useCallback } from "react";

interface DecisionToolbarProps {
  activeSavedViewId: string;
  canDeleteSavedView: boolean;
  isSavingView: boolean;
  isDeletingView: boolean;
  onDeleteSavedView: () => void;
  onRefresh: () => void;
  onClearFilters: () => void;
  onSaveCurrentFilters: () => void;
  onSearchChange: (value: string) => void;
  onStatusChange: (value: string) => void;
  onFromDateChange: (value: string) => void;
  onToDateChange: (value: string) => void;
  onSavedViewSelect: (id: string) => void;
  savedViewOptions: Array<{ id: string; name: string }>;
  selectedStatus: string;
  fromDate: string;
  toDate: string;
  searchQuery: string;
}

export function DecisionToolbar({
  activeSavedViewId,
  canDeleteSavedView,
  fromDate,
  isDeletingView,
  isSavingView,
  onClearFilters,
  onDeleteSavedView,
  onFromDateChange,
  onRefresh,
  onSaveCurrentFilters,
  onSearchChange,
  onSavedViewSelect,
  onStatusChange,
  onToDateChange,
  savedViewOptions,
  selectedStatus,
  searchQuery,
  toDate,
}: DecisionToolbarProps) {
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
