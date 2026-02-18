import type { DecisionStatus } from "@/domain/decision";

const STATUS_STYLES: Record<DecisionStatus, string> = {
  completed: "bg-emerald-100 text-emerald-800 border-emerald-200",
  draft: "bg-slate-100 text-slate-700 border-slate-200",
  failed: "bg-rose-100 text-rose-800 border-rose-200",
  pending: "bg-amber-100 text-amber-800 border-amber-200",
  processing: "bg-sky-100 text-sky-800 border-sky-200",
};

interface DecisionStatusPillProps {
  status: DecisionStatus;
}

export function DecisionStatusPill({ status }: DecisionStatusPillProps) {
  const styleClass = STATUS_STYLES[status];

  return (
    <span
      className={`inline-flex min-w-[88px] items-center justify-center rounded-full border px-2 py-1 text-xs font-semibold uppercase tracking-wide ${styleClass}`}
      data-testid={`decision-status-pill-${status}`}
    >
      {status}
    </span>
  );
}
