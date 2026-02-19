import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { OperatorShell } from "@/ui/layout/operator-shell";

describe("operator shell sidebar active state", () => {
  it("highlights decisions on decisions routes", () => {
    window.history.replaceState({}, "", "/decisions");

    render(
      <OperatorShell>
        <div>content</div>
      </OperatorShell>,
    );

    expect(screen.getByTestId("sidebar-active-decisions")).toBeInTheDocument();
    expect(
      screen.queryByTestId("sidebar-active-webhooks"),
    ).not.toBeInTheDocument();
  });

  it("highlights webhooks on webhooks route", () => {
    window.history.replaceState({}, "", "/webhooks");

    render(
      <OperatorShell>
        <div>content</div>
      </OperatorShell>,
    );

    expect(screen.getByTestId("sidebar-active-webhooks")).toBeInTheDocument();
    expect(
      screen.queryByTestId("sidebar-active-decisions"),
    ).not.toBeInTheDocument();
  });
});
