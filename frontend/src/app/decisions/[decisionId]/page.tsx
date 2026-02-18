import { DecisionDetailPageClient } from "@/ui/features/decisions/decision-detail-page-client";
import { OperatorShell } from "@/ui/layout/operator-shell";

export default async function DecisionDetailPage({
  params,
}: {
  params: Promise<{ decisionId: string }>;
}) {
  const { decisionId } = await params;

  return (
    <OperatorShell>
      <DecisionDetailPageClient decisionId={decisionId} />
    </OperatorShell>
  );
}
