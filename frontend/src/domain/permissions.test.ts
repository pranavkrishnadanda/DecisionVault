import { describe, expect, it } from "vitest";
import { getRolePermissions } from "@/domain/permissions";

describe("permissions", () => {
  it("denies all actions for unknown role", () => {
    const permissions = getRolePermissions(null);

    expect(permissions.canReadDecisions).toBe(false);
    expect(permissions.canManageSavedViews).toBe(false);
    expect(permissions.canManageTablePreferences).toBe(false);
    expect(permissions.canRetryDecision).toBe(false);
  });

  it("allows read-only access for viewer", () => {
    const permissions = getRolePermissions("viewer");

    expect(permissions.canReadDecisions).toBe(true);
    expect(permissions.canReadDecisionDetail).toBe(true);
    expect(permissions.canManageSavedViews).toBe(false);
    expect(permissions.canManageTablePreferences).toBe(false);
    expect(permissions.canRetryDecision).toBe(false);
  });

  it("allows mutation permissions for operator", () => {
    const permissions = getRolePermissions("operator");

    expect(permissions.canReadDecisions).toBe(true);
    expect(permissions.canManageSavedViews).toBe(true);
    expect(permissions.canManageTablePreferences).toBe(true);
    expect(permissions.canRetryDecision).toBe(true);
  });
});
