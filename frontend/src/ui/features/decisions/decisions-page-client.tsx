"use client";

import { useCallback } from "react";
import { useDecisionEvents } from "@/hooks/use-decision-events";
import { useDecisionsQuery } from "@/hooks/use-decisions-query";
import { selectSessionToken, useAuthStore } from "@/state/auth-store";
import { RetryPanel } from "@/ui/components/errors/retry-panel";
import { TableSkeleton } from "@/ui/components/skeleton/table-skeleton";
import { AuthGate } from "@/ui/features/auth/auth-gate";
import { DecisionList } from "@/ui/features/decisions/decision-list";

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
        <header>
          <h2 className="text-xl font-semibold tracking-tight text-slate-900">
            Decision operations
          </h2>
          <p className="mt-1 text-sm text-slate-600">
            Monitor approval paths, inspect failures, and replay retries.
          </p>
          <p className="mt-1 text-xs text-slate-400">
            Session: {sessionToken ? "active" : "missing"}
          </p>
        </header>

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
    </AuthGate>
  );
}
