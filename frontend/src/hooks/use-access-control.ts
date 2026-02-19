"use client";

import { useMemo } from "react";
import { getRolePermissions } from "@/domain/permissions";
import {
  selectAccessContext,
  selectIsAccessHydrating,
  useAuthStore,
} from "@/state/auth-store";

export function useAccessControl() {
  const accessContext = useAuthStore(selectAccessContext);
  const isAccessHydrating = useAuthStore(selectIsAccessHydrating);

  const permissions = useMemo(
    () => getRolePermissions(accessContext?.role),
    [accessContext?.role],
  );

  return {
    isAccessHydrating,
    organizationId: accessContext?.organizationId ?? null,
    role: accessContext?.role ?? null,
    permissions,
  };
}
