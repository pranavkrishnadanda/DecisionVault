"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import type { DecisionListFilters } from "@/api/decisions";
import { useDecisionEvents } from "@/hooks/use-decision-events";
import { useDecisionsQuery } from "@/hooks/use-decisions-query";
import { selectSessionToken, useAuthStore } from "@/state/auth-store";
import { RetryPanel } from "@/ui/components/errors/retry-panel";
import { TableSkeleton } from "@/ui/components/skeleton/table-skeleton";
import { AuthGate } from "@/ui/features/auth/auth-gate";
import { DecisionList } from "@/ui/features/decisions/decision-list";
import { DecisionToolbar } from "@/ui/features/decisions/decision-toolbar";
import {
  DECISION_FILTER_SEARCH_DEBOUNCE_MS,
  DECISIONS_PAGE_LIMIT,
} from "@/ui/features/decisions/filter-constants";

interface DecisionsFilterState {
  q: string;
  status: string;
  from: string;
  to: string;
}

function readInitialFiltersFromUrl(): DecisionsFilterState {
  if (typeof window === "undefined") {
    return {
      q: "",
      status: "",
      from: "",
      to: "",
    };
  }

  const searchParams = new URLSearchParams(window.location.search);
  return {
    q: searchParams.get("q") ?? "",
    status: searchParams.get("status") ?? "",
    from: searchParams.get("from") ?? "",
    to: searchParams.get("to") ?? "",
  };
}

function useDebouncedValue(value: string, delayMs: number) {
  const [debouncedValue, setDebouncedValue] = useState(value);

  useEffect(() => {
    const timeout = window.setTimeout(() => {
      setDebouncedValue(value);
    }, delayMs);

    return () => {
      window.clearTimeout(timeout);
    };
  }, [delayMs, value]);

  return debouncedValue;
}

export function DecisionsPageClient() {
  const sessionToken = useAuthStore(selectSessionToken);
  const isAuthenticated = Boolean(sessionToken);
  const [filters, setFilters] = useState<DecisionsFilterState>(
    readInitialFiltersFromUrl,
  );
  const debouncedQuery = useDebouncedValue(
    filters.q,
    DECISION_FILTER_SEARCH_DEBOUNCE_MS,
  );

  useDecisionEvents(isAuthenticated);

  const queryFilters = useMemo<DecisionListFilters>(() => {
    return {
      q: debouncedQuery.trim() || undefined,
      status: filters.status || undefined,
      from: filters.from || undefined,
      to: filters.to || undefined,
      limit: DECISIONS_PAGE_LIMIT,
      offset: 0,
    };
  }, [debouncedQuery, filters.from, filters.status, filters.to]);

  const { data, error, isError, isPending, refetch } = useDecisionsQuery(
    isAuthenticated,
    queryFilters,
  );

  const onRetry = useCallback(() => {
    void refetch();
  }, [refetch]);

  const onSearchChange = useCallback((value: string) => {
    setFilters((current) => ({
      ...current,
      q: value,
    }));
  }, []);

  const onStatusChange = useCallback((value: string) => {
    setFilters((current) => ({
      ...current,
      status: value,
    }));
  }, []);

  const onFromDateChange = useCallback((value: string) => {
    setFilters((current) => ({
      ...current,
      from: value,
    }));
  }, []);

  const onToDateChange = useCallback((value: string) => {
    setFilters((current) => ({
      ...current,
      to: value,
    }));
  }, []);

  const onClearFilters = useCallback(() => {
    setFilters({
      q: "",
      status: "",
      from: "",
      to: "",
    });
  }, []);

  useEffect(() => {
    const searchParams = new URLSearchParams();
    if (filters.q.trim()) {
      searchParams.set("q", filters.q.trim());
    }
    if (filters.status) {
      searchParams.set("status", filters.status);
    }
    if (filters.from) {
      searchParams.set("from", filters.from);
    }
    if (filters.to) {
      searchParams.set("to", filters.to);
    }

    const queryString = searchParams.toString();
    const nextUrl = queryString
      ? `${window.location.pathname}?${queryString}`
      : window.location.pathname;
    window.history.replaceState({}, "", nextUrl);
  }, [filters]);

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
          fromDate={filters.from}
          onClearFilters={onClearFilters}
          onFromDateChange={onFromDateChange}
          onRefresh={onRetry}
          onSearchChange={onSearchChange}
          onStatusChange={onStatusChange}
          onToDateChange={onToDateChange}
          searchQuery={filters.q}
          selectedStatus={filters.status}
          toDate={filters.to}
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
            <DecisionList decisions={data} />
          ) : null}
        </section>
      </section>
    </AuthGate>
  );
}
