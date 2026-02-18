import { DecisionsPageClient } from "@/ui/features/decisions/decisions-page-client";
import { OperatorShell } from "@/ui/layout/operator-shell";

export default function DecisionsPage() {
  return (
    <OperatorShell>
      <DecisionsPageClient />
    </OperatorShell>
  );
}
