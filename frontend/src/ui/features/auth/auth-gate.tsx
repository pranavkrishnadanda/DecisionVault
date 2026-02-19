"use client";

import Link from "next/link";
import { useAccessControl } from "@/hooks/use-access-control";
import { selectSessionToken, useAuthStore } from "@/state/auth-store";

export function AuthGate({ children }: { children: React.ReactNode }) {
  const sessionToken = useAuthStore(selectSessionToken);
  const { isAccessHydrating } = useAccessControl();

  if (isAccessHydrating) {
    return (
      <section
        className="rounded-xl border border-slate-200 bg-white p-6"
        data-testid="auth-hydration-skeleton"
      >
        <div className="h-4 w-56 animate-pulse rounded bg-slate-200" />
        <div className="mt-3 h-3 w-80 animate-pulse rounded bg-slate-200" />
      </section>
    );
  }

  if (!sessionToken) {
    return (
      <section className="rounded-xl border border-amber-300/50 bg-amber-50 p-6 text-slate-900">
        <h2 className="text-lg font-semibold">Authentication required</h2>
        <p className="mt-2 text-sm text-slate-700">
          Enter a valid session token to access operator controls.
        </p>
        <Link
          className="mt-4 inline-flex rounded-md bg-slate-900 px-4 py-2 text-sm font-medium text-white"
          href="/auth/login"
        >
          Go to login
        </Link>
      </section>
    );
  }

  return <>{children}</>;
}
