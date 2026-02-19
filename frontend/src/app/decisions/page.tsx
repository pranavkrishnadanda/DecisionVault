import { DecisionsPageClient } from "@/ui/features/decisions/decisions-page-client";
import { AppShell } from "@/ui/layout/app-shell";

export default function DecisionsPage() {
  return (
    <AppShell>
      <DecisionsPageClient />
    </AppShell>
  );
}
