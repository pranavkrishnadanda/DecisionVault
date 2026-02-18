import Link from "next/link";

export function OperatorShell({ children }: { children: React.ReactNode }) {
  return (
    <div className="min-h-screen bg-[radial-gradient(circle_at_top_left,_#dbeafe_0%,_#f8fafc_38%,_#f1f5f9_100%)] text-slate-900">
      <div className="mx-auto grid min-h-screen max-w-7xl grid-cols-1 gap-4 px-4 py-4 lg:grid-cols-[220px_1fr]">
        <aside className="rounded-2xl border border-slate-200/80 bg-white/90 p-4 backdrop-blur">
          <h1 className="text-base font-semibold tracking-tight">
            DecisionVault
          </h1>
          <p className="mt-1 text-xs uppercase tracking-[0.2em] text-slate-500">
            Operator Console
          </p>

          <nav className="mt-6 space-y-2 text-sm">
            <Link
              className="block rounded-md bg-slate-900 px-3 py-2 font-medium text-white"
              href="/decisions"
            >
              Decisions
            </Link>
            <span className="block rounded-md px-3 py-2 text-slate-400">
              Workflows
            </span>
            <span className="block rounded-md px-3 py-2 text-slate-400">
              Audit Trails
            </span>
          </nav>
        </aside>

        <main className="rounded-2xl border border-slate-200/80 bg-white/90 p-5 shadow-sm backdrop-blur">
          {children}
        </main>
      </div>
    </div>
  );
}
