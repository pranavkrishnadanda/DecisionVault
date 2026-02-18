"use client";

import { useCallback, useMemo } from "react";
import type { DecisionDetailRecord } from "@/domain/decision-detail";
import { buildDecisionTimeline } from "@/domain/decision-detail";
import { useDecisionDetailQuery } from "@/hooks/use-decision-detail-query";
import { useDecisionRetryMutation } from "@/hooks/use-decision-retry-mutation";
import { selectSessionToken, useAuthStore } from "@/state/auth-store";
import { RetryPanel } from "@/ui/components/errors/retry-panel";
import { AuthGate } from "@/ui/features/auth/auth-gate";
import { DecisionStatusPill } from "@/ui/features/decisions/decision-status-pill";

function formatDateTime(value: string | null) {
  if (!value) {
    return "Not available";
  }

  return new Date(value).toLocaleString();
}

function DetailSkeleton() {
  return (
    <section
      aria-live="polite"
      className="space-y-3"
      data-testid="decision-detail-skeleton"
    >
      <div className="h-24 animate-pulse rounded-xl bg-slate-200/80" />
      <div className="h-24 animate-pulse rounded-xl bg-slate-200/80" />
      <div className="h-24 animate-pulse rounded-xl bg-slate-200/80" />
    </section>
  );
}

function SummaryPanel({ decision }: { decision: DecisionDetailRecord }) {
  return (
    <section className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
      <h2 className="text-sm font-semibold uppercase tracking-wide text-slate-500">
        Decision Summary
      </h2>
      <div className="mt-3 flex flex-wrap items-center gap-3">
        <h3 className="text-xl font-semibold text-slate-900">
          {decision.title}
        </h3>
        <DecisionStatusPill status={decision.status} />
      </div>
      <p className="mt-2 text-sm text-slate-700">{decision.description}</p>
      <dl className="mt-4 grid grid-cols-1 gap-3 text-sm sm:grid-cols-2">
        <div>
          <dt className="text-slate-500">Decision ID</dt>
          <dd className="font-mono text-slate-900">{decision.id}</dd>
        </div>
        <div>
          <dt className="text-slate-500">Priority</dt>
          <dd className="text-slate-900">{decision.priority}</dd>
        </div>
      </dl>
    </section>
  );
}

function WorkflowPanel({ decision }: { decision: DecisionDetailRecord }) {
  return (
    <section className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
      <h2 className="text-sm font-semibold uppercase tracking-wide text-slate-500">
        Workflow State
      </h2>
      <dl className="mt-3 grid grid-cols-1 gap-3 text-sm sm:grid-cols-2">
        <div>
          <dt className="text-slate-500">Started</dt>
          <dd className="text-slate-900">
            {formatDateTime(decision.workflowStartedAt)}
          </dd>
        </div>
        <div>
          <dt className="text-slate-500">Completed</dt>
          <dd className="text-slate-900">
            {formatDateTime(decision.workflowCompletedAt)}
          </dd>
        </div>
      </dl>
    </section>
  );
}

function AuditPanel({ decision }: { decision: DecisionDetailRecord }) {
  const timeline = useMemo(() => buildDecisionTimeline(decision), [decision]);

  return (
    <section className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
      <h2 className="text-sm font-semibold uppercase tracking-wide text-slate-500">
        Audit Timeline
      </h2>
      <ol className="mt-3 space-y-3">
        {timeline.map((event) => (
          <li
            className="rounded-md border border-slate-200 bg-slate-50 px-3 py-2"
            key={event.id}
          >
            <p className="text-sm font-medium text-slate-900">{event.label}</p>
            <p className="text-xs text-slate-500">
              {formatDateTime(event.timestamp)}
            </p>
            <p className="mt-1 text-xs text-slate-700">{event.description}</p>
          </li>
        ))}
      </ol>
    </section>
  );
}

function RetryPanelSection({
  canRetry,
  isRetrying,
  onRetry,
}: {
  canRetry: boolean;
  isRetrying: boolean;
  onRetry: () => void;
}) {
  return (
    <section className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
      <h2 className="text-sm font-semibold uppercase tracking-wide text-slate-500">
        Retry Controls
      </h2>
      {canRetry ? (
        <button
          className="mt-3 inline-flex rounded-md bg-slate-900 px-4 py-2 text-sm font-medium text-white disabled:opacity-60"
          disabled={isRetrying}
          onClick={onRetry}
          type="button"
        >
          {isRetrying ? "Retrying..." : "Retry decision"}
        </button>
      ) : (
        <p className="mt-3 text-sm text-slate-600">
          Only failed decisions can be retried.
        </p>
      )}
    </section>
  );
}

function ErrorInspectionPanel({
  decision,
}: {
  decision: DecisionDetailRecord;
}) {
  const serializedResult = useMemo(
    () => JSON.stringify(decision.agentResult, null, 2),
    [decision.agentResult],
  );
  const serializedMetadata = useMemo(
    () => JSON.stringify(decision.metadata, null, 2),
    [decision.metadata],
  );

  return (
    <section className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
      <h2 className="text-sm font-semibold uppercase tracking-wide text-slate-500">
        Error Inspection
      </h2>
      <p className="mt-3 text-sm text-slate-700">
        {decision.agentError || "No agent error recorded."}
      </p>
      <div className="mt-3 grid grid-cols-1 gap-3 lg:grid-cols-2">
        <pre className="overflow-auto rounded-md bg-slate-950 p-3 text-xs text-slate-100">
          {serializedResult}
        </pre>
        <pre className="overflow-auto rounded-md bg-slate-950 p-3 text-xs text-slate-100">
          {serializedMetadata}
        </pre>
      </div>
    </section>
  );
}

export function DecisionDetailPageClient({
  decisionId,
}: {
  decisionId: string;
}) {
  const sessionToken = useAuthStore(selectSessionToken);
  const isAuthenticated = Boolean(sessionToken);

  const { data, error, isError, isPending, refetch } = useDecisionDetailQuery(
    decisionId,
    isAuthenticated,
  );
  const { mutate, isPending: isRetrying } = useDecisionRetryMutation();

  const onRetryLoad = useCallback(() => {
    void refetch();
  }, [refetch]);

  const onRetryDecision = useCallback(() => {
    mutate(decisionId);
  }, [decisionId, mutate]);

  return (
    <AuthGate>
      <section className="space-y-4">
        <header>
          <h1 className="text-2xl font-semibold text-slate-900">
            Decision Detail
          </h1>
          <p className="text-sm text-slate-600">
            Trace workflow state, inspect failures, and trigger safe retries.
          </p>
        </header>

        {isPending ? <DetailSkeleton /> : null}

        {isError ? (
          <RetryPanel
            ctaLabel="Retry loading decision"
            message={
              error instanceof Error ? error.message : "Unexpected detail error"
            }
            onRetry={onRetryLoad}
            title="Unable to load decision detail"
          />
        ) : null}

        {!isPending && !isError && data ? (
          <section className="grid grid-cols-1 gap-4 xl:grid-cols-2">
            <SummaryPanel decision={data} />
            <WorkflowPanel decision={data} />
            <AuditPanel decision={data} />
            <RetryPanelSection
              canRetry={data.status === "failed"}
              isRetrying={isRetrying}
              onRetry={onRetryDecision}
            />
            <div className="xl:col-span-2">
              <ErrorInspectionPanel decision={data} />
            </div>
          </section>
        ) : null}
      </section>
    </AuthGate>
  );
}
