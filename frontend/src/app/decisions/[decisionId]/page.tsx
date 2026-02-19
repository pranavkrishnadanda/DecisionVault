import { DecisionDetailPageClient } from "@/ui/features/decisions/decision-detail-page-client";
import { AppShell } from "@/ui/layout/app-shell";

export default async function DecisionDetailPage({
  params,
}: {
  params: Promise<{ decisionId: string }>;
}) {
  const { decisionId } = await params;

  return (
    <AppShell>
      <DecisionDetailPageClient decisionId={decisionId} />
    </AppShell>
  );
}
