"use client";

import Link from "next/link";
import { type ChangeEvent, type FormEvent, useCallback, useState } from "react";
import { loginWithPassword } from "@/api/auth";
import { ApiError } from "@/api/client";
import { useAuthStore } from "@/state/auth-store";

interface LoginFormProps {
  onAuthenticated: () => void;
}

export function LoginForm({ onAuthenticated }: LoginFormProps) {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const setSessionToken = useAuthStore((state) => state.setSessionToken);

  const onUsernameChange = useCallback(
    (event: ChangeEvent<HTMLInputElement>) => {
      setUsername(event.target.value);
      if (error) {
        setError(null);
      }
    },
    [error],
  );

  const onPasswordChange = useCallback(
    (event: ChangeEvent<HTMLInputElement>) => {
      setPassword(event.target.value);
      if (error) {
        setError(null);
      }
    },
    [error],
  );

  const onSubmit = useCallback(
    async (event: FormEvent<HTMLFormElement>) => {
      event.preventDefault();

      const nextUsername = username.trim();
      if (!nextUsername || !password) {
        setError("Username and password are required");
        return;
      }

      setIsSubmitting(true);
      setError(null);

      try {
        const accessToken = await loginWithPassword({
          username: nextUsername,
          password,
        });
        setSessionToken(accessToken);
        onAuthenticated();
      } catch (fetchError) {
        if (fetchError instanceof ApiError && fetchError.status === 401) {
          setError("Invalid username or password");
        } else {
          setError("Authentication failed. Please retry.");
        }
      } finally {
        setIsSubmitting(false);
      }
    },
    [onAuthenticated, password, setSessionToken, username],
  );

  return (
    <form
      className="space-y-4 rounded-xl border border-slate-300 bg-white p-6"
      onSubmit={onSubmit}
    >
      <div>
        <h1 className="text-xl font-semibold text-slate-900">Operator Login</h1>
        <p className="mt-1 text-sm text-slate-600">
          Sign in with operator credentials to get a short-lived session JWT.
        </p>
      </div>

      <label
        className="block text-sm font-medium text-slate-800"
        htmlFor="username"
      >
        Username
      </label>
      <input
        id="username"
        autoComplete="username"
        className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm outline-none ring-sky-500 focus:ring-2"
        name="username"
        onChange={onUsernameChange}
        type="text"
        value={username}
      />

      <label
        className="block text-sm font-medium text-slate-800"
        htmlFor="password"
      >
        Password
      </label>
      <input
        id="password"
        autoComplete="current-password"
        className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm outline-none ring-sky-500 focus:ring-2"
        name="password"
        onChange={onPasswordChange}
        type="password"
        value={password}
      />

      {error ? <p className="text-sm text-red-700">{error}</p> : null}

      <button
        className="inline-flex rounded-md bg-slate-900 px-4 py-2 text-sm font-medium text-white disabled:opacity-60"
        disabled={isSubmitting}
        type="submit"
      >
        {isSubmitting ? "Signing in..." : "Continue to dashboard"}
      </button>

      <p className="text-sm text-slate-600">
        New operator?{" "}
        <Link
          className="font-medium text-slate-900 underline"
          href="/auth/register"
        >
          Create account
        </Link>
      </p>
    </form>
  );
}
