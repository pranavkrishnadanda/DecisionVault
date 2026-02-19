import type { OrganizationRole } from "@/domain/auth";

export interface RolePermissions {
  canReadDecisions: boolean;
  canReadDecisionDetail: boolean;
  canManageSavedViews: boolean;
  canManageTablePreferences: boolean;
  canRetryDecision: boolean;
}

const DENY_ALL: RolePermissions = Object.freeze({
  canReadDecisions: false,
  canReadDecisionDetail: false,
  canManageSavedViews: false,
  canManageTablePreferences: false,
  canRetryDecision: false,
});

const VIEWER_PERMISSIONS: RolePermissions = Object.freeze({
  canReadDecisions: true,
  canReadDecisionDetail: true,
  canManageSavedViews: false,
  canManageTablePreferences: false,
  canRetryDecision: false,
});

const OPERATOR_PERMISSIONS: RolePermissions = Object.freeze({
  canReadDecisions: true,
  canReadDecisionDetail: true,
  canManageSavedViews: true,
  canManageTablePreferences: true,
  canRetryDecision: true,
});

export function getRolePermissions(
  role: OrganizationRole | null | undefined,
): RolePermissions {
  if (role === "viewer") {
    return VIEWER_PERMISSIONS;
  }
  if (role === "operator" || role === "admin") {
    return OPERATOR_PERMISSIONS;
  }
  return DENY_ALL;
}
