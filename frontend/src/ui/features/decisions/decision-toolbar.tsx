interface DecisionToolbarProps {
  onRefresh: () => void;
}

export function DecisionToolbar({ onRefresh }: DecisionToolbarProps) {
  return (
    <div className="flex flex-col gap-3 rounded-xl border border-slate-200 bg-slate-50/70 p-3 sm:flex-row sm:items-center sm:justify-between">
      <input
        aria-label="Search decisions"
        className="h-10 w-full rounded-md border border-slate-300 bg-white px-3 text-sm text-slate-500 outline-none placeholder:text-slate-400 sm:max-w-sm"
        placeholder="Search decisions"
        readOnly
        type="search"
        value=""
      />

      <button
        className="inline-flex h-10 items-center justify-center rounded-md bg-slate-900 px-4 text-sm font-medium text-white transition hover:bg-slate-800"
        onClick={onRefresh}
        type="button"
      >
        Refresh decisions
      </button>
    </div>
  );
}
