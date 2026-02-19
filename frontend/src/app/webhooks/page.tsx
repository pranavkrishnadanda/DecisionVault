import { OperatorShell } from "@/ui/layout/operator-shell";
import { WebhookOpsPageClient } from "@/ui/features/webhooks/webhook-ops-page-client";

export default function WebhooksPage() {
  return (
    <OperatorShell>
      <WebhookOpsPageClient />
    </OperatorShell>
  );
}
