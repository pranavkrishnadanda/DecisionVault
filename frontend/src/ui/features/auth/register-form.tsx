"use client";

import Link from "next/link";
import { type ChangeEvent, type FormEvent, useCallback, useState } from "react";
import { registerWithPassword } from "@/api/auth";
import { ApiError } from "@/api/client";
import { useAuthStore } from "@/state/auth-store";

interface RegisterFormProps {
  onRegistered: () => void;
}

export function RegisterForm({ onRegistered }: RegisterFormProps) {
  const [username, setUsername] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
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

  const onEmailChange = useCallback(
    (event: ChangeEvent<HTMLInputElement>) => {
      setEmail(event.target.value);
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

  const onConfirmPasswordChange = useCallback(
    (event: ChangeEvent<HTMLInputElement>) => {
      setConfirmPassword(event.target.value);
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
      const nextEmail = email.trim();

      if (!nextUsername || !nextEmail || !password || !confirmPassword) {
        setError("All fields are required");
        return;
      }

      if (password !== confirmPassword) {
        setError("Passwords do not match");
        return;
      }

      setIsSubmitting(true);
      setError(null);

      try {
        const accessToken = await registerWithPassword({
          username: nextUsername,
          email: nextEmail,
          password,
        });
        setSessionToken(accessToken);
        onRegistered();
      } catch (fetchError) {
        if (fetchError instanceof ApiError && fetchError.status === 400) {
          setError(
            "Registration failed. Username/email may already be in use.",
          );
        } else {
          setError("Registration failed. Please retry.");
        }
      } finally {
        setIsSubmitting(false);
      }
    },
    [confirmPassword, email, onRegistered, password, setSessionToken, username],
  );

  return (
    <form
      className="space-y-4 rounded-xl border border-slate-300 bg-white p-6"
      onSubmit={onSubmit}
    >
      <div>
        <h1 className="text-xl font-semibold text-slate-900">
          Create Operator Account
        </h1>
        <p className="mt-1 text-sm text-slate-600">
          Register a new operator profile and start an authenticated session.
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
        htmlFor="email"
      >
        Email
      </label>
      <input
        id="email"
        autoComplete="email"
        className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm outline-none ring-sky-500 focus:ring-2"
        name="email"
        onChange={onEmailChange}
        type="email"
        value={email}
      />

      <label
        className="block text-sm font-medium text-slate-800"
        htmlFor="password"
      >
        Password
      </label>
      <input
        id="password"
        autoComplete="new-password"
        className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm outline-none ring-sky-500 focus:ring-2"
        name="password"
        onChange={onPasswordChange}
        type="password"
        value={password}
      />

      <label
        className="block text-sm font-medium text-slate-800"
        htmlFor="confirmPassword"
      >
        Confirm password
      </label>
      <input
        id="confirmPassword"
        autoComplete="new-password"
        className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm outline-none ring-sky-500 focus:ring-2"
        name="confirmPassword"
        onChange={onConfirmPasswordChange}
        type="password"
        value={confirmPassword}
      />

      {error ? <p className="text-sm text-red-700">{error}</p> : null}

      <button
        className="inline-flex rounded-md bg-slate-900 px-4 py-2 text-sm font-medium text-white disabled:opacity-60"
        disabled={isSubmitting}
        type="submit"
      >
        {isSubmitting ? "Creating account..." : "Create account"}
      </button>

      <p className="text-sm text-slate-600">
        Already have an account?{" "}
        <Link
          className="font-medium text-slate-900 underline"
          href="/auth/login"
        >
          Sign in
        </Link>
      </p>
    </form>
  );
}
