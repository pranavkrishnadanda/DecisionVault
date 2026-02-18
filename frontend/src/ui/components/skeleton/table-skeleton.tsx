export function TableSkeleton({ rows = 8 }: { rows?: number }) {
  const skeletonRows: string[] = [];
  for (let row = 1; row <= rows; row += 1) {
    skeletonRows.push(`skeleton-${row}`);
  }

  return (
    <section aria-live="polite" className="space-y-2">
      {skeletonRows.map((rowId) => (
        <div
          className="h-10 animate-pulse rounded-md bg-slate-200/80"
          data-testid="decision-skeleton-row"
          key={rowId}
        />
      ))}
    </section>
  );
}
