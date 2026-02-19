import { Suspense } from "react";
import { IntegrationsPageClient } from "@/ui/features/integrations/integrations-page-client";
import { AppShell } from "@/ui/layout/app-shell";

export default function IntegrationsPage() {
  return (
    <AppShell>
      <Suspense
        fallback={
          <section className="p-4 text-sm text-slate-600">
            Loading integrations...
          </section>
        }
      >
        <IntegrationsPageClient />
      </Suspense>
    </AppShell>
  );
}
