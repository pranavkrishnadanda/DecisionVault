"use client";

import { useRouter } from "next/navigation";
import { useCallback } from "react";
import { LoginForm } from "@/ui/features/auth/login-form";

export default function LoginPage() {
  const router = useRouter();

  const onAuthenticated = useCallback(() => {
    router.replace("/decisions");
  }, [router]);

  return (
    <div className="mx-auto flex min-h-screen max-w-lg items-center px-4">
      <LoginForm onAuthenticated={onAuthenticated} />
    </div>
  );
}
