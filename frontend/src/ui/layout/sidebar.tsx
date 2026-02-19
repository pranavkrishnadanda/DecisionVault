"use client";

import Link from "next/link";

export interface SidebarItem {
  href: string;
  label: string;
  key: string;
}

function getNavClassName(isActive: boolean) {
  if (isActive) {
    return "relative block rounded-md bg-slate-900 px-3 py-2 pl-4 font-medium text-white shadow-sm";
  }
  return "block rounded-md px-3 py-2 text-slate-600 transition-colors hover:bg-slate-100";
}

export function Sidebar({
  items,
  pathname,
  collapsed,
  onToggleCollapsed,
}: {
  items: SidebarItem[];
  pathname: string;
  collapsed: boolean;
  onToggleCollapsed: () => void;
}) {
  return (
    <aside
      className={`rounded-2xl border border-slate-200/80 bg-white/90 p-4 shadow-md backdrop-blur transition-all ${
        collapsed ? "w-20" : "w-full"
      }`}
      data-collapsed={collapsed ? "true" : "false"}
      data-testid="app-sidebar"
    >
      <div className="flex items-center justify-between">
        {!collapsed ? (
          <div>
            <h1 className="text-base font-semibold tracking-tight">
              DecisionVault
            </h1>
            <p className="mt-1 text-xs uppercase tracking-[0.2em] text-slate-500">
              Operator Console
            </p>
          </div>
        ) : (
          <h1 className="text-base font-semibold tracking-tight">DV</h1>
        )}
        <button
          aria-label={collapsed ? "Expand sidebar" : "Collapse sidebar"}
          className="rounded-md border border-slate-300 px-2 py-1 text-xs font-medium text-slate-700 hover:bg-slate-100"
          onClick={onToggleCollapsed}
          type="button"
        >
          {collapsed ? ">" : "<"}
        </button>
      </div>

      <nav aria-label="Primary" className="mt-6 space-y-2 text-sm">
        {items.map((item) => {
          const isActive =
            pathname === item.href || pathname.startsWith(`${item.href}/`);
          return (
            <Link
              className={getNavClassName(isActive)}
              data-testid={
                isActive
                  ? `sidebar-active-${item.key}`
                  : `sidebar-link-${item.key}`
              }
              href={item.href}
              key={item.key}
            >
              {isActive ? (
                <span className="absolute inset-y-1 left-1 w-1 rounded-full bg-sky-300" />
              ) : null}
              {collapsed ? (
                <span className="sr-only">{item.label}</span>
              ) : (
                item.label
              )}
            </Link>
          );
        })}
      </nav>
    </aside>
  );
}
