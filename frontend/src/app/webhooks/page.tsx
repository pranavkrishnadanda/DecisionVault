import { WebhookOpsPageClient } from "@/ui/features/webhooks/webhook-ops-page-client";
import { OperatorShell } from "@/ui/layout/operator-shell";

export default function WebhooksPage() {
  return (
    <OperatorShell>
      <WebhookOpsPageClient />
    </OperatorShell>
  );
}
