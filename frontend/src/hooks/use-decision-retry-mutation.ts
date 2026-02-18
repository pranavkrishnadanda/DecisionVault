import { useMutation, useQueryClient } from "@tanstack/react-query";
import { retryDecision } from "@/api/decision-detail";
import type { DecisionRecord } from "@/domain/decision";
import type { DecisionDetailRecord } from "@/domain/decision-detail";

export function useDecisionRetryMutation() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: retryDecision,
    onSuccess: (result, decisionId) => {
      queryClient.setQueryData(
        ["decision", decisionId],
        (current: DecisionDetailRecord | undefined) => {
          if (!current) {
            return current;
          }

          return {
            ...current,
            status: result.status,
            workflowCompletedAt: null,
            agentError: "",
            agentResult: {},
            updatedAt: new Date().toISOString(),
          };
        },
      );

      queryClient.setQueryData(
        ["decisions"],
        (current: DecisionRecord[] | undefined) => {
          if (!current) {
            return current;
          }

          return current.map((decision) => {
            if (decision.id !== decisionId) {
              return decision;
            }

            return {
              ...decision,
              status: result.status,
              updatedAt: new Date().toISOString(),
            };
          });
        },
      );
    },
  });
}
