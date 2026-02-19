import { AuthGate } from "@/ui/features/auth/auth-gate";
import { AppShell } from "@/ui/layout/app-shell";

export default function SettingsPage() {
  return (
    <AppShell>
      <AuthGate>
        <section className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
          <h2 className="text-xl font-semibold text-slate-900">Settings</h2>
          <p className="mt-2 text-sm text-slate-600">
            Configure workspace-level operator preferences.
          </p>
        </section>
      </AuthGate>
    </AppShell>
  );
}
