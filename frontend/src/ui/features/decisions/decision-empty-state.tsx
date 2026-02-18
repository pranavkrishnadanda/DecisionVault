export function DecisionEmptyState() {
  return (
    <section className="rounded-xl border border-dashed border-slate-300 bg-slate-50 px-6 py-12 text-center">
      <h3 className="text-lg font-semibold text-slate-900">No decisions yet</h3>
      <p className="mt-2 text-sm text-slate-600">
        New decisions will appear here in realtime once operators submit
        workflows.
      </p>
    </section>
  );
}
