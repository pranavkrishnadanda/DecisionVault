import { useVirtualizer, type VirtualItem } from "@tanstack/react-virtual";
import { useCallback, useMemo, useRef } from "react";
import type { DecisionRecord } from "@/domain/decision";
import {
  DECISIONS_COLUMN_LABELS,
  DECISIONS_DEFAULT_COLUMN_ORDER,
  type DecisionTableColumnKey,
  type TableDensity,
} from "@/domain/table-preference";
import { DecisionEmptyState } from "@/ui/features/decisions/decision-empty-state";
import { DecisionRow } from "@/ui/features/decisions/decision-row";

const INITIAL_LIST_RECT = { height: 520, width: 1200 };
const FALLBACK_VISIBLE_ROWS = 24;
const DEFAULT_ROW_HEIGHT = 50;
const ROW_HEIGHT_BY_DENSITY: Record<TableDensity, number> = {
  compact: 44,
  comfortable: 50,
  spacious: 58,
};

const COLUMN_WIDTH_BY_KEY: Record<DecisionTableColumnKey, string> = {
  id: "1.2fr",
  workflow: "1fr",
  status: "0.8fr",
  updated: "1fr",
};

interface DecisionListProps {
  decisions: DecisionRecord[];
  columnOrder: DecisionTableColumnKey[];
  density: TableDensity;
  visibleColumns: DecisionTableColumnKey[];
}

export function DecisionList({
  columnOrder,
  decisions,
  density,
  visibleColumns,
}: DecisionListProps) {
  const parentRef = useRef<HTMLDivElement>(null);

  const getScrollElement = useCallback(() => parentRef.current, []);
  const rowHeight = ROW_HEIGHT_BY_DENSITY[density] ?? DEFAULT_ROW_HEIGHT;

  const orderedVisibleColumns = useMemo(() => {
    const visibleColumnSet = new Set(visibleColumns);
    const filtered = columnOrder.filter((column) =>
      visibleColumnSet.has(column),
    );
    return filtered.length > 0 ? filtered : [DECISIONS_DEFAULT_COLUMN_ORDER[0]];
  }, [columnOrder, visibleColumns]);

  const gridTemplateColumns = useMemo(
    () =>
      orderedVisibleColumns
        .map((column) => COLUMN_WIDTH_BY_KEY[column])
        .join(" "),
    [orderedVisibleColumns],
  );

  const estimateSize = useCallback(() => rowHeight, [rowHeight]);

  const rowVirtualizer = useVirtualizer({
    count: decisions.length,
    initialRect: INITIAL_LIST_RECT,
    getScrollElement,
    estimateSize,
    overscan: 10,
  });

  const virtualItems = rowVirtualizer.getVirtualItems();
  const hasVirtualItems = virtualItems.length > 0;

  const renderVirtualRow = useCallback(
    (virtualItem: VirtualItem) => {
      const decision = decisions[virtualItem.index];
      if (!decision) {
        return null;
      }

      const rowStyle = {
        left: 0,
        position: "absolute" as const,
        top: 0,
        transform: `translateY(${virtualItem.start}px)`,
        width: "100%",
      };

      return (
        <DecisionRow
          columns={orderedVisibleColumns}
          decision={decision}
          density={density}
          gridTemplateColumns={gridTemplateColumns}
          key={decision.id}
          style={rowStyle}
        />
      );
    },
    [decisions, density, gridTemplateColumns, orderedVisibleColumns],
  );

  const totalHeightStyle = useMemo(() => {
    const totalHeight = hasVirtualItems
      ? rowVirtualizer.getTotalSize()
      : decisions.length * rowHeight;

    return {
      height: `${totalHeight}px`,
      position: "relative" as const,
    };
  }, [decisions.length, hasVirtualItems, rowHeight, rowVirtualizer]);

  const fallbackRows = useMemo(() => {
    if (hasVirtualItems) {
      return [];
    }

    const visibleCount = Math.min(decisions.length, FALLBACK_VISIBLE_ROWS);

    return Array.from({ length: visibleCount }, (_, index) => {
      const decision = decisions[index];
      if (!decision) {
        return null;
      }

      return (
        <DecisionRow
          columns={orderedVisibleColumns}
          decision={decision}
          density={density}
          gridTemplateColumns={gridTemplateColumns}
          key={decision.id}
          style={{
            left: 0,
            position: "absolute",
            top: 0,
            transform: `translateY(${index * rowHeight}px)`,
            width: "100%",
          }}
        />
      );
    });
  }, [
    decisions,
    density,
    gridTemplateColumns,
    hasVirtualItems,
    orderedVisibleColumns,
    rowHeight,
  ]);

  if (decisions.length === 0) {
    return <DecisionEmptyState />;
  }

  return (
    <section className="space-y-3">
      <header
        className="grid gap-2 px-3 text-xs font-semibold uppercase tracking-wider text-slate-500"
        style={{ gridTemplateColumns }}
      >
        {orderedVisibleColumns.map((column) => (
          <span key={column}>{DECISIONS_COLUMN_LABELS[column]}</span>
        ))}
      </header>
      <div
        className="h-[520px] overflow-auto rounded-md border border-slate-200 bg-slate-50/30 p-2"
        ref={parentRef}
      >
        <div style={totalHeightStyle}>
          {hasVirtualItems ? virtualItems.map(renderVirtualRow) : fallbackRows}
        </div>
      </div>
    </section>
  );
}
