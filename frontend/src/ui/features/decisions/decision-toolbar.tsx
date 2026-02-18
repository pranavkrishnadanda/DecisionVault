import { type ChangeEvent, useCallback } from "react";

interface DecisionToolbarProps {
  onRefresh: () => void;
  onClearFilters: () => void;
  onSearchChange: (value: string) => void;
  onStatusChange: (value: string) => void;
  onFromDateChange: (value: string) => void;
  onToDateChange: (value: string) => void;
  selectedStatus: string;
  fromDate: string;
  toDate: string;
  searchQuery: string;
}

export function DecisionToolbar({
  fromDate,
  onClearFilters,
  onFromDateChange,
  onRefresh,
  onSearchChange,
  onStatusChange,
  onToDateChange,
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

  return (
    <div className="flex flex-col gap-3 rounded-2xl border border-slate-200 bg-white p-3 shadow-sm">
      <div className="grid grid-cols-1 gap-2 lg:grid-cols-[minmax(0,1fr)_160px_170px_170px_auto_auto]">
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

        <button
          className="inline-flex h-10 items-center justify-center rounded-md border border-slate-300 bg-white px-4 text-sm font-medium text-slate-700 transition hover:bg-slate-50"
          disabled={!searchQuery && !selectedStatus && !fromDate && !toDate}
          onClick={clearFilters}
          type="button"
        >
          Clear
        </button>

        <button
          className="inline-flex h-10 items-center justify-center rounded-md bg-slate-900 px-4 text-sm font-medium text-white shadow-sm transition hover:bg-slate-800"
          onClick={onRefresh}
          type="button"
        >
          Refresh decisions
        </button>
      </div>
    </div>
  );
}
