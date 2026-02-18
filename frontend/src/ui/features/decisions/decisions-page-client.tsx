"use client";

import { useCallback, useMemo, useState } from "react";
import type { DecisionRecord } from "@/domain/decision";
import { useDecisionEvents } from "@/hooks/use-decision-events";
import { useDecisionsQuery } from "@/hooks/use-decisions-query";
import { selectSessionToken, useAuthStore } from "@/state/auth-store";
import { RetryPanel } from "@/ui/components/errors/retry-panel";
import { TableSkeleton } from "@/ui/components/skeleton/table-skeleton";
import { AuthGate } from "@/ui/features/auth/auth-gate";
import { DecisionList } from "@/ui/features/decisions/decision-list";
import { DecisionToolbar } from "@/ui/features/decisions/decision-toolbar";

function matchesDecisionQuery(decision: DecisionRecord, query: string) {
  if (!query) {
    return true;
  }

  const normalizedQuery = query.trim().toLowerCase();
  if (!normalizedQuery) {
    return true;
  }

  return (
    decision.id.toLowerCase().includes(normalizedQuery) ||
    decision.workflowName.toLowerCase().includes(normalizedQuery) ||
    decision.status.toLowerCase().includes(normalizedQuery)
  );
}

export function DecisionsPageClient() {
  const sessionToken = useAuthStore(selectSessionToken);
  const isAuthenticated = Boolean(sessionToken);
  const [searchQuery, setSearchQuery] = useState("");

  useDecisionEvents(isAuthenticated);

  const { data, error, isError, isPending, refetch } =
    useDecisionsQuery(isAuthenticated);

  const onRetry = useCallback(() => {
    void refetch();
  }, [refetch]);

  const onSearchChange = useCallback((value: string) => {
    setSearchQuery(value);
  }, []);

  const filteredDecisions = useMemo(() => {
    if (!data) {
      return [];
    }

    return data.filter((decision) =>
      matchesDecisionQuery(decision, searchQuery),
    );
  }, [data, searchQuery]);

  return (
    <AuthGate>
      <section className="space-y-5">
        <header className="rounded-2xl border border-slate-200 bg-gradient-to-r from-white via-slate-50 to-sky-50/80 p-5 shadow-sm">
          <div className="flex flex-wrap items-center gap-3">
            <span
              className="inline-flex h-10 w-10 items-center justify-center rounded-lg border border-slate-200 bg-white text-slate-700 shadow-sm"
              data-testid="decisions-header-icon"
            >
              <svg
                aria-label="Decision metrics icon"
                className="h-5 w-5"
                fill="none"
                role="img"
                stroke="currentColor"
                strokeWidth="1.8"
                viewBox="0 0 24 24"
              >
                <title>Decision metrics</title>
                <path d="M4 19h16M6 16V8m6 8V5m6 11v-6" strokeLinecap="round" />
              </svg>
            </span>

            <div className="min-w-0 flex-1">
              <h2 className="text-2xl font-semibold tracking-tight text-slate-900">
                Decision operations
              </h2>
              <p className="text-sm text-slate-600">
                Monitor approval paths, inspect failures, and replay retries.
              </p>
            </div>

            <span
              className="inline-flex items-center gap-2 rounded-full border border-emerald-200 bg-emerald-50 px-3 py-1 text-xs font-medium text-emerald-700"
              data-testid="decisions-live-indicator"
            >
              <span className="h-2 w-2 rounded-full bg-emerald-500" />
              Live updates are active
            </span>
          </div>
          <p className="mt-2 text-xs text-slate-500">
            Session: {sessionToken ? "authenticated" : "missing"}
          </p>
        </header>

        <DecisionToolbar
          onRefresh={onRetry}
          onSearchChange={onSearchChange}
          searchQuery={searchQuery}
        />

        <section className="rounded-2xl border border-slate-200 bg-white p-3 shadow-md">
          {isPending ? <TableSkeleton rows={8} /> : null}

          {isError ? (
            <RetryPanel
              ctaLabel="Retry loading decisions"
              message={
                error instanceof Error ? error.message : "Unexpected error"
              }
              onRetry={onRetry}
              title="Unable to load decisions"
            />
          ) : null}

          {!isPending && !isError && data ? (
            <DecisionList decisions={filteredDecisions} />
          ) : null}
        </section>
      </section>
    </AuthGate>
  );
}
