import { useQueryClient } from "@tanstack/react-query";
import { useCallback, useEffect } from "react";
import { ApiError } from "@/api/client";
import { subscribeToDecisionEvents } from "@/api/decision-stream";
import {
  applyDecisionEvent,
  type DecisionEvent,
} from "@/domain/decision-events";
import { selectSessionToken, useAuthStore } from "@/state/auth-store";

export function useDecisionEvents(enabled: boolean): void {
  const queryClient = useQueryClient();
  const sessionToken = useAuthStore(selectSessionToken);
  const clearSessionToken = useAuthStore((state) => state.clearSessionToken);

  const onEvent = useCallback(
    (event: DecisionEvent) => {
      queryClient.setQueryData(["decisions"], (current: unknown) => {
        const safeCurrent = Array.isArray(current) ? current : undefined;
        return applyDecisionEvent(safeCurrent, event);
      });
    },
    [queryClient],
  );

  const onError = useCallback(
    (error: Error) => {
      if (error instanceof ApiError) {
        if (error.status === 401) {
          clearSessionToken();
          return;
        }

        // Stream endpoint failures should degrade silently without UI crashes.
        return;
      }

      console.error("Decision stream error", error);
    },
    [clearSessionToken],
  );

  useEffect(() => {
    if (!enabled || !sessionToken) {
      return;
    }

    return subscribeToDecisionEvents({
      token: sessionToken,
      onEvent,
      onError,
    });
  }, [enabled, onError, onEvent, sessionToken]);
}
