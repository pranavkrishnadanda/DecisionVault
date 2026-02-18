import { type ChangeEvent, useCallback } from "react";

interface DecisionToolbarProps {
  onRefresh: () => void;
  onSearchChange: (value: string) => void;
  searchQuery: string;
}

export function DecisionToolbar({
  onRefresh,
  onSearchChange,
  searchQuery,
}: DecisionToolbarProps) {
  const handleSearchChange = useCallback(
    (event: ChangeEvent<HTMLInputElement>) => {
      onSearchChange(event.target.value);
    },
    [onSearchChange],
  );

  const clearSearch = useCallback(() => {
    onSearchChange("");
  }, [onSearchChange]);

  return (
    <div className="flex flex-col gap-3 rounded-2xl border border-slate-200 bg-white p-3 shadow-sm sm:flex-row sm:items-center sm:justify-between">
      <div className="flex w-full gap-2 sm:max-w-xl">
        <input
          aria-label="Search decisions"
          className="h-10 w-full rounded-md border border-slate-300 bg-white px-3 text-sm text-slate-700 outline-none ring-sky-200 transition focus:border-sky-300 focus:ring-2 placeholder:text-slate-400"
          onChange={handleSearchChange}
          placeholder="Search decisions"
          type="search"
          value={searchQuery}
        />

        <button
          className="inline-flex h-10 items-center justify-center rounded-md border border-slate-300 bg-white px-4 text-sm font-medium text-slate-700 transition hover:bg-slate-50"
          disabled={!searchQuery}
          onClick={clearSearch}
          type="button"
        >
          Clear
        </button>
      </div>

      <button
        className="inline-flex h-10 items-center justify-center rounded-md bg-slate-900 px-4 text-sm font-medium text-white shadow-sm transition hover:bg-slate-800"
        onClick={onRefresh}
        type="button"
      >
        Refresh decisions
      </button>
    </div>
  );
}
