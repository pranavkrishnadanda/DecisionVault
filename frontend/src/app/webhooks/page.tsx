import { WebhookOpsPageClient } from "@/ui/features/webhooks/webhook-ops-page-client";
import { AppShell } from "@/ui/layout/app-shell";

export default function WebhooksPage() {
  return (
    <AppShell>
      <WebhookOpsPageClient />
    </AppShell>
  );
}
