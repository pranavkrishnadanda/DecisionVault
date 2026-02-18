import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { ApiError } from "@/api/client";
import { useAuthStore } from "@/state/auth-store";
import { AuthGate } from "@/ui/features/auth/auth-gate";
import { LoginForm } from "@/ui/features/auth/login-form";
import { RegisterForm } from "@/ui/features/auth/register-form";

const mockLoginWithPassword = vi.fn();
const mockRegisterWithPassword = vi.fn();

vi.mock("@/api/auth", () => ({
  loginWithPassword: (...args: unknown[]) => mockLoginWithPassword(...args),
  registerWithPassword: (...args: unknown[]) =>
    mockRegisterWithPassword(...args),
}));

describe("auth flow", () => {
  beforeEach(() => {
    useAuthStore.setState({ sessionToken: null });
    mockLoginWithPassword.mockReset();
    mockRegisterWithPassword.mockReset();
  });

  it("blocks dashboard content when unauthenticated", () => {
    render(
      <AuthGate>
        <div>secure content</div>
      </AuthGate>,
    );

    expect(screen.getByText(/authentication required/i)).toBeInTheDocument();
    expect(screen.queryByText("secure content")).not.toBeInTheDocument();
  });

  it("allows dashboard content when authenticated", () => {
    useAuthStore.setState({ sessionToken: "jwt-token" });

    render(
      <AuthGate>
        <div>secure content</div>
      </AuthGate>,
    );

    expect(screen.getByText("secure content")).toBeInTheDocument();
  });

  it("submits credentials, stores access token, and triggers success callback", async () => {
    const onAuthenticated = vi.fn();
    mockLoginWithPassword.mockResolvedValue("jwt-token");

    render(<LoginForm onAuthenticated={onAuthenticated} />);

    fireEvent.change(screen.getByLabelText(/username/i), {
      target: { value: "operator" },
    });
    fireEvent.change(screen.getByLabelText(/^password$/i), {
      target: { value: "pass1234" },
    });
    fireEvent.click(
      screen.getByRole("button", { name: /continue to dashboard/i }),
    );

    await waitFor(() => {
      expect(useAuthStore.getState().sessionToken).toBe("jwt-token");
    });
    expect(onAuthenticated).toHaveBeenCalledTimes(1);
  });

  it("shows invalid credential message on 401", async () => {
    mockLoginWithPassword.mockRejectedValue(
      new ApiError("Unauthorized", 401, null),
    );

    render(<LoginForm onAuthenticated={vi.fn()} />);

    fireEvent.change(screen.getByLabelText(/username/i), {
      target: { value: "operator" },
    });
    fireEvent.change(screen.getByLabelText(/^password$/i), {
      target: { value: "wrong-pass" },
    });
    fireEvent.click(
      screen.getByRole("button", { name: /continue to dashboard/i }),
    );

    await waitFor(() => {
      expect(
        screen.getByText(/invalid username or password/i),
      ).toBeInTheDocument();
    });
    expect(useAuthStore.getState().sessionToken).toBeNull();
  });

  it("registers a new user and stores token", async () => {
    const onRegistered = vi.fn();
    mockRegisterWithPassword.mockResolvedValue("new-jwt-token");

    render(<RegisterForm onRegistered={onRegistered} />);

    fireEvent.change(screen.getByLabelText(/username/i), {
      target: { value: "new-user" },
    });
    fireEvent.change(screen.getByLabelText(/email/i), {
      target: { value: "new-user@example.com" },
    });
    fireEvent.change(screen.getByLabelText(/^password$/i), {
      target: { value: "StrongPass123!" },
    });
    fireEvent.change(screen.getByLabelText(/confirm password/i), {
      target: { value: "StrongPass123!" },
    });
    fireEvent.click(screen.getByRole("button", { name: /create account/i }));

    await waitFor(() => {
      expect(useAuthStore.getState().sessionToken).toBe("new-jwt-token");
    });
    expect(onRegistered).toHaveBeenCalledTimes(1);
  });

  it("shows mismatch error on registration", async () => {
    render(<RegisterForm onRegistered={vi.fn()} />);

    fireEvent.change(screen.getByLabelText(/username/i), {
      target: { value: "new-user" },
    });
    fireEvent.change(screen.getByLabelText(/email/i), {
      target: { value: "new-user@example.com" },
    });
    fireEvent.change(screen.getByLabelText(/^password$/i), {
      target: { value: "StrongPass123!" },
    });
    fireEvent.change(screen.getByLabelText(/confirm password/i), {
      target: { value: "DifferentPass123!" },
    });
    fireEvent.click(screen.getByRole("button", { name: /create account/i }));

    await waitFor(() => {
      expect(screen.getByText(/passwords do not match/i)).toBeInTheDocument();
    });
  });
});
