"use client";

import { useRouter } from "next/navigation";
import { useCallback } from "react";
import { RegisterForm } from "@/ui/features/auth/register-form";

export default function RegisterPage() {
  const router = useRouter();

  const onRegistered = useCallback(() => {
    router.replace("/decisions");
  }, [router]);

  return (
    <div className="mx-auto flex min-h-screen max-w-lg items-center px-4">
      <RegisterForm onRegistered={onRegistered} />
    </div>
  );
}
