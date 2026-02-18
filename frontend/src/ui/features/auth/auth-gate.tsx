"use client";

import Link from "next/link";
import { selectSessionToken, useAuthStore } from "@/state/auth-store";

export function AuthGate({ children }: { children: React.ReactNode }) {
  const sessionToken = useAuthStore(selectSessionToken);

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
