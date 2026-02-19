import { Suspense } from "react";
import { SlackIntegrationPageClient } from "@/ui/features/slack/slack-integration-page-client";
import { AppShell } from "@/ui/layout/app-shell";

export default function SlackIntegrationPage() {
  return (
    <AppShell>
      <Suspense fallback={<section className="p-4 text-sm text-slate-600">Loading Slack...</section>}>
        <SlackIntegrationPageClient />
      </Suspense>
    </AppShell>
  );
}
