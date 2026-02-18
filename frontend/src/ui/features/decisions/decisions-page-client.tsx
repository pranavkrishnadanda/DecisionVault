"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import type { DecisionListFilters } from "@/api/decisions";
import {
  DECISIONS_COLUMN_LABELS,
  DECISIONS_DEFAULT_COLUMN_ORDER,
  DECISIONS_DEFAULT_DENSITY,
  DECISIONS_DEFAULT_VISIBLE_COLUMNS,
  DECISIONS_TABLE_KEY,
  type DecisionTableColumnKey,
  type TableDensity,
  type TablePreferenceRecord,
} from "@/domain/table-preference";
import { useCreateSavedViewMutation } from "@/hooks/use-create-saved-view-mutation";
import { useDecisionEvents } from "@/hooks/use-decision-events";
import { useDecisionsQuery } from "@/hooks/use-decisions-query";
import { useDeleteSavedViewMutation } from "@/hooks/use-delete-saved-view-mutation";
import { useSavedViewsQuery } from "@/hooks/use-saved-views-query";
import { useTablePreferenceQuery } from "@/hooks/use-table-preference-query";
import { useUpdateTablePreferenceMutation } from "@/hooks/use-update-table-preference-mutation";
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

function defaultTablePreference(): TablePreferenceRecord {
  return {
    table: DECISIONS_TABLE_KEY,
    visibleColumns: [...DECISIONS_DEFAULT_VISIBLE_COLUMNS],
    columnOrder: [...DECISIONS_DEFAULT_COLUMN_ORDER],
    density: DECISIONS_DEFAULT_DENSITY,
  };
}

function moveColumn(
  columns: DecisionTableColumnKey[],
  column: DecisionTableColumnKey,
  direction: -1 | 1,
) {
  const index = columns.indexOf(column);
  if (index < 0) {
    return columns;
  }

  const swapIndex = index + direction;
  if (swapIndex < 0 || swapIndex >= columns.length) {
    return columns;
  }

  const next = [...columns];
  const temp = next[index];
  next[index] = next[swapIndex] as DecisionTableColumnKey;
  next[swapIndex] = temp as DecisionTableColumnKey;
  return next;
}

function normalizeSavedFilters(
  filters: Partial<DecisionListFilters>,
): DecisionsFilterState {
  return {
    q: typeof filters.q === "string" ? filters.q : "",
    status: typeof filters.status === "string" ? filters.status : "",
    from: typeof filters.from === "string" ? filters.from : "",
    to: typeof filters.to === "string" ? filters.to : "",
  };
}

function areFilterStatesEqual(
  a: DecisionsFilterState,
  b: DecisionsFilterState,
) {
  return (
    a.q === b.q && a.status === b.status && a.from === b.from && a.to === b.to
  );
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
  const [activeSavedViewId, setActiveSavedViewId] = useState("");
  const [tablePreference, setTablePreference] =
    useState<TablePreferenceRecord | null>(null);

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
  const { data: savedViews = [] } = useSavedViewsQuery(isAuthenticated);
  const { mutate: createSavedView, isPending: isSavingView } =
    useCreateSavedViewMutation();
  const { mutate: deleteSavedView, isPending: isDeletingView } =
    useDeleteSavedViewMutation();
  const { data: hydratedTablePreference, isPending: isTablePreferencePending } =
    useTablePreferenceQuery(isAuthenticated, DECISIONS_TABLE_KEY);
  const { mutate: updateTablePreference, isPending: isSavingTableSettings } =
    useUpdateTablePreferenceMutation();

  useEffect(() => {
    if (hydratedTablePreference && !tablePreference) {
      setTablePreference(hydratedTablePreference);
    }
  }, [hydratedTablePreference, tablePreference]);

  const effectiveTablePreference = tablePreference ?? defaultTablePreference();
  const isTablePreferenceHydrating =
    isAuthenticated && isTablePreferencePending && !tablePreference;

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

  const onSavedViewSelect = useCallback(
    (id: string) => {
      setActiveSavedViewId(id);
      if (!id) {
        return;
      }

      const selected = savedViews.find((view) => view.id === id);
      if (!selected) {
        return;
      }

      setFilters(normalizeSavedFilters(selected.filters));
    },
    [savedViews],
  );

  const onSaveCurrentFilters = useCallback(() => {
    const hasFilters =
      Boolean(filters.q.trim()) ||
      Boolean(filters.status) ||
      Boolean(filters.from) ||
      Boolean(filters.to);
    if (!hasFilters) {
      return;
    }

    const generatedName = `Saved view ${new Date().toISOString().slice(0, 19)}`;
    createSavedView({
      name: generatedName,
      filters: {
        q: filters.q.trim() || undefined,
        status: filters.status || undefined,
        from: filters.from || undefined,
        to: filters.to || undefined,
      },
    });
  }, [createSavedView, filters.from, filters.q, filters.status, filters.to]);

  const onDeleteSavedView = useCallback(() => {
    if (!activeSavedViewId) {
      return;
    }
    deleteSavedView(activeSavedViewId);
    setActiveSavedViewId("");
    setFilters({
      q: "",
      status: "",
      from: "",
      to: "",
    });
  }, [activeSavedViewId, deleteSavedView]);

  const onToggleColumn = useCallback((column: DecisionTableColumnKey) => {
    setTablePreference((currentState) => {
      const current = currentState ?? defaultTablePreference();
      const isVisible = current.visibleColumns.includes(column);
      if (isVisible && current.visibleColumns.length === 1) {
        return current;
      }

      const nextVisibleColumns = isVisible
        ? current.visibleColumns.filter((item) => item !== column)
        : [...current.visibleColumns, column];

      return {
        ...current,
        visibleColumns: nextVisibleColumns,
      };
    });
  }, []);

  const onMoveColumnUp = useCallback((column: DecisionTableColumnKey) => {
    setTablePreference((currentState) => {
      const current = currentState ?? defaultTablePreference();
      return {
        ...current,
        columnOrder: moveColumn(current.columnOrder, column, -1),
      };
    });
  }, []);

  const onMoveColumnDown = useCallback((column: DecisionTableColumnKey) => {
    setTablePreference((currentState) => {
      const current = currentState ?? defaultTablePreference();
      return {
        ...current,
        columnOrder: moveColumn(current.columnOrder, column, 1),
      };
    });
  }, []);

  const onDensityChange = useCallback((value: TableDensity) => {
    setTablePreference((currentState) => {
      const current = currentState ?? defaultTablePreference();
      return {
        ...current,
        density: value,
      };
    });
  }, []);

  const onSaveTableSettings = useCallback(() => {
    const current = tablePreference ?? defaultTablePreference();
    updateTablePreference({
      table: DECISIONS_TABLE_KEY,
      payload: {
        visibleColumns: current.visibleColumns,
        columnOrder: current.columnOrder,
        density: current.density,
      },
    });
  }, [tablePreference, updateTablePreference]);

  const tableColumns = useMemo(
    () =>
      effectiveTablePreference.columnOrder.map((key) => ({
        key,
        label: DECISIONS_COLUMN_LABELS[key],
        visible: effectiveTablePreference.visibleColumns.includes(key),
      })),
    [
      effectiveTablePreference.columnOrder,
      effectiveTablePreference.visibleColumns,
    ],
  );

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

  useEffect(() => {
    if (!activeSavedViewId) {
      return;
    }

    const selected = savedViews.find((view) => view.id === activeSavedViewId);
    if (!selected) {
      setActiveSavedViewId("");
      return;
    }

    const selectedFilters = normalizeSavedFilters(selected.filters);
    if (!areFilterStatesEqual(filters, selectedFilters)) {
      setActiveSavedViewId("");
    }
  }, [activeSavedViewId, filters, savedViews]);

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
          activeSavedViewId={activeSavedViewId}
          canDeleteSavedView={Boolean(activeSavedViewId)}
          density={effectiveTablePreference.density}
          fromDate={filters.from}
          isDeletingView={isDeletingView}
          isSavingTableSettings={isSavingTableSettings}
          isSavingView={isSavingView}
          onClearFilters={onClearFilters}
          onDensityChange={onDensityChange}
          onDeleteSavedView={onDeleteSavedView}
          onFromDateChange={onFromDateChange}
          onMoveColumnDown={onMoveColumnDown}
          onMoveColumnUp={onMoveColumnUp}
          onRefresh={onRetry}
          onSaveTableSettings={onSaveTableSettings}
          onSaveCurrentFilters={onSaveCurrentFilters}
          onSearchChange={onSearchChange}
          onSavedViewSelect={onSavedViewSelect}
          onStatusChange={onStatusChange}
          onToggleColumn={onToggleColumn}
          onToDateChange={onToDateChange}
          savedViewOptions={savedViews.map((view) => ({
            id: view.id,
            name: view.name,
          }))}
          searchQuery={filters.q}
          selectedStatus={filters.status}
          tableColumns={tableColumns}
          toDate={filters.to}
        />

        <section className="rounded-2xl border border-slate-200 bg-white p-3 shadow-md">
          {isPending || isTablePreferenceHydrating ? (
            <TableSkeleton rows={8} />
          ) : null}

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

          {!isPending && !isTablePreferenceHydrating && !isError && data ? (
            <DecisionList
              columnOrder={effectiveTablePreference.columnOrder}
              decisions={data}
              density={effectiveTablePreference.density}
              visibleColumns={effectiveTablePreference.visibleColumns}
            />
          ) : null}
        </section>
      </section>
    </AuthGate>
  );
}
