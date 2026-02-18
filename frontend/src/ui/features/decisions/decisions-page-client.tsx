"use client";

import { useCallback } from "react";
import { useDecisionEvents } from "@/hooks/use-decision-events";
import { useDecisionsQuery } from "@/hooks/use-decisions-query";
import { selectSessionToken, useAuthStore } from "@/state/auth-store";
import { RetryPanel } from "@/ui/components/errors/retry-panel";
import { TableSkeleton } from "@/ui/components/skeleton/table-skeleton";
import { AuthGate } from "@/ui/features/auth/auth-gate";
import { DecisionList } from "@/ui/features/decisions/decision-list";
import { DecisionToolbar } from "@/ui/features/decisions/decision-toolbar";

export function DecisionsPageClient() {
  const sessionToken = useAuthStore(selectSessionToken);
  const isAuthenticated = Boolean(sessionToken);

  useDecisionEvents(isAuthenticated);

  const { data, error, isError, isPending, refetch } =
    useDecisionsQuery(isAuthenticated);

  const onRetry = useCallback(() => {
    void refetch();
  }, [refetch]);

  return (
    <AuthGate>
      <section className="space-y-5">
        <header className="space-y-1">
          <h2 className="text-2xl font-semibold tracking-tight text-slate-900">
            Decision operations
          </h2>
          <p className="text-sm text-slate-600">
            Monitor approval paths, inspect failures, and replay retries.
          </p>
          <p className="text-xs text-slate-500">
            Live updates are active. Session:{" "}
            {sessionToken ? "authenticated" : "missing"}
          </p>
        </header>

        <DecisionToolbar onRefresh={onRetry} />

        <section className="rounded-xl border border-slate-200 bg-white p-3 shadow-sm">
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
            <DecisionList decisions={data} />
          ) : null}
        </section>
      </section>
    </AuthGate>
  );
}
