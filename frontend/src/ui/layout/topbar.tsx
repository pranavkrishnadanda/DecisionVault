"use client";

export function Topbar({
  organizationId,
  role,
  isHydrating,
  onLogout,
}: {
  organizationId: string | null;
  role: string | null;
  isHydrating: boolean;
  onLogout: () => void;
}) {
  return (
    <header className="mb-4 rounded-xl border border-slate-200 bg-white/95 px-4 py-3 shadow-sm">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-lg font-semibold tracking-tight text-slate-900">
            DecisionVault Workspace
          </h1>
          <p className="text-sm text-slate-600">
            Organization: {organizationId ?? "Unavailable"}
          </p>
        </div>

        <div className="flex items-center gap-3">
          <div
            className={`h-2 w-24 rounded-full ${isHydrating ? "animate-pulse bg-amber-400" : "bg-emerald-500"}`}
            data-testid="global-loading-indicator"
          />
          <details className="relative">
            <summary className="cursor-pointer list-none rounded-md border border-slate-300 px-3 py-2 text-sm font-medium text-slate-800 hover:bg-slate-100">
              {role ?? "unknown role"}
            </summary>
            <div className="absolute right-0 z-10 mt-2 min-w-40 rounded-md border border-slate-200 bg-white p-2 shadow-lg">
              <p className="px-2 py-1 text-xs uppercase tracking-wide text-slate-500">
                Profile
              </p>
              <p className="px-2 py-1 text-sm text-slate-700">
                Role: {role ?? "unknown"}
              </p>
              <button
                className="mt-2 w-full rounded-md bg-slate-900 px-3 py-2 text-sm font-medium text-white"
                onClick={onLogout}
                type="button"
              >
                Sign out
              </button>
            </div>
          </details>
        </div>
      </div>
    </header>
  );
}
