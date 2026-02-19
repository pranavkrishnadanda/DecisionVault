"use client";

import { usePathname } from "next/navigation";
import { useCallback, useMemo, useState } from "react";
import { logoutSessionRequest } from "@/api/session";
import { useAccessControl } from "@/hooks/use-access-control";
import { selectSessionToken, useAuthStore } from "@/state/auth-store";
import { Sidebar, type SidebarItem } from "@/ui/layout/sidebar";
import { Topbar } from "@/ui/layout/topbar";

const SHELL_ITEMS: SidebarItem[] = [
  { href: "/decisions", label: "Decisions", key: "decisions" },
  { href: "/webhooks", label: "Webhooks", key: "webhooks" },
  { href: "/integrations", label: "Integrations", key: "integrations" },
  { href: "/settings", label: "Settings", key: "settings" },
];

export function AppShell({ children }: { children: React.ReactNode }) {
  const [collapsed, setCollapsed] = useState(false);
  const pathname = usePathname();
  const { isAccessHydrating, organizationId, role } = useAccessControl();
  const sessionToken = useAuthStore(selectSessionToken);
  const clearSessionToken = useAuthStore((state) => state.clearSessionToken);

  const onToggleCollapsed = useCallback(() => {
    setCollapsed((current) => !current);
  }, []);

  const onLogout = useCallback(() => {
    clearSessionToken();
    void logoutSessionRequest();
  }, [clearSessionToken]);

  const sidebarItems = useMemo(() => SHELL_ITEMS, []);

  return (
    <div className="min-h-screen bg-[radial-gradient(circle_at_top_left,_#dbeafe_0%,_#f8fafc_35%,_#f1f5f9_100%)] text-slate-900">
      <div className="mx-auto grid min-h-screen max-w-7xl grid-cols-1 gap-4 px-4 py-4 lg:grid-cols-[auto_1fr]">
        <Sidebar
          collapsed={collapsed}
          items={sidebarItems}
          onToggleCollapsed={onToggleCollapsed}
          pathname={pathname ?? "/decisions"}
        />
        <main className="rounded-2xl border border-slate-200/80 bg-white/90 p-5 shadow-lg backdrop-blur">
          <Topbar
            isAuthenticated={Boolean(sessionToken)}
            isHydrating={isAccessHydrating}
            onLogout={onLogout}
            organizationId={organizationId}
            role={role}
          />
          {children}
        </main>
      </div>
    </div>
  );
}
