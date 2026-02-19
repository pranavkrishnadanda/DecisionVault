import { Suspense } from "react";
import { SlackOAuthCallbackClient } from "@/ui/features/integrations/slack-oauth-callback-client";
import { AppShell } from "@/ui/layout/app-shell";

export default function SlackOAuthCallbackPage() {
  return (
    <AppShell>
      <Suspense
        fallback={
          <section className="p-4 text-sm text-slate-600">
            Completing Slack connection...
          </section>
        }
      >
        <SlackOAuthCallbackClient />
      </Suspense>
    </AppShell>
  );
}
