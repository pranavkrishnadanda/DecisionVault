import { useVirtualizer, type VirtualItem } from "@tanstack/react-virtual";
import { useCallback, useMemo, useRef } from "react";
import type { DecisionRecord } from "@/domain/decision";
import { DecisionEmptyState } from "@/ui/features/decisions/decision-empty-state";
import { DecisionRow } from "@/ui/features/decisions/decision-row";

const INITIAL_LIST_RECT = { height: 520, width: 1200 };
const FALLBACK_VISIBLE_ROWS = 24;
const ROW_HEIGHT = 50;

export function DecisionList({ decisions }: { decisions: DecisionRecord[] }) {
  const parentRef = useRef<HTMLDivElement>(null);

  const getScrollElement = useCallback(() => parentRef.current, []);
  const estimateSize = useCallback(() => 50, []);

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
        <DecisionRow decision={decision} key={decision.id} style={rowStyle} />
      );
    },
    [decisions],
  );

  const totalHeightStyle = useMemo(() => {
    const totalHeight = hasVirtualItems
      ? rowVirtualizer.getTotalSize()
      : decisions.length * ROW_HEIGHT;

    return {
      height: `${totalHeight}px`,
      position: "relative" as const,
    };
  }, [decisions.length, hasVirtualItems, rowVirtualizer]);

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
          decision={decision}
          key={decision.id}
          style={{
            left: 0,
            position: "absolute",
            top: 0,
            transform: `translateY(${index * ROW_HEIGHT}px)`,
            width: "100%",
          }}
        />
      );
    });
  }, [decisions, hasVirtualItems]);

  if (decisions.length === 0) {
    return <DecisionEmptyState />;
  }

  return (
    <section className="space-y-3">
      <header className="grid grid-cols-[1.2fr_1fr_0.8fr_1fr] gap-2 px-3 text-xs font-semibold uppercase tracking-wider text-slate-500">
        <span>Decision ID</span>
        <span>Workflow</span>
        <span>Status</span>
        <span>Updated</span>
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
