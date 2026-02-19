import Link from "next/link";

export function OperatorShell({ children }: { children: React.ReactNode }) {
  const pathname =
    typeof window === "undefined" ? "/decisions" : window.location.pathname;
  const isDecisionsRoute =
    pathname === "/decisions" || pathname.startsWith("/decisions/");
  const isWebhooksRoute =
    pathname === "/webhooks" || pathname.startsWith("/webhooks/");
  const activeNavClass =
    "relative block rounded-md bg-slate-900 px-3 py-2 pl-4 font-medium text-white shadow-sm";
  const inactiveNavClass =
    "block rounded-md px-3 py-2 text-slate-600 hover:bg-slate-100";

  return (
    <div className="min-h-screen bg-[radial-gradient(circle_at_top_left,_#dbeafe_0%,_#f8fafc_35%,_#f1f5f9_100%)] text-slate-900">
      <div className="mx-auto grid min-h-screen max-w-7xl grid-cols-1 gap-4 px-4 py-4 lg:grid-cols-[220px_1fr]">
        <aside className="rounded-2xl border border-slate-200/80 bg-white/90 p-4 shadow-md backdrop-blur">
          <h1 className="text-base font-semibold tracking-tight">
            DecisionVault
          </h1>
          <p className="mt-1 text-xs uppercase tracking-[0.2em] text-slate-500">
            Operator Console
          </p>

          <nav className="mt-6 space-y-2 text-sm">
            <Link
              className={isDecisionsRoute ? activeNavClass : inactiveNavClass}
              href="/decisions"
              data-testid={
                isDecisionsRoute
                  ? "sidebar-active-decisions"
                  : "sidebar-link-decisions"
              }
            >
              {isDecisionsRoute ? (
                <span className="absolute inset-y-1 left-1 w-1 rounded-full bg-sky-300" />
              ) : null}
              Decisions
            </Link>
            <span className="block rounded-md px-3 py-2 text-slate-400">
              Workflows
            </span>
            <span className="block rounded-md px-3 py-2 text-slate-400">
              Audit Trails
            </span>
            <Link
              className={isWebhooksRoute ? activeNavClass : inactiveNavClass}
              href="/webhooks"
              data-testid={
                isWebhooksRoute
                  ? "sidebar-active-webhooks"
                  : "sidebar-link-webhooks"
              }
            >
              {isWebhooksRoute ? (
                <span className="absolute inset-y-1 left-1 w-1 rounded-full bg-sky-300" />
              ) : null}
              Webhooks
            </Link>
          </nav>
        </aside>

        <main className="rounded-2xl border border-slate-200/80 bg-white/90 p-5 shadow-lg backdrop-blur">
          {children}
        </main>
      </div>
    </div>
  );
}
