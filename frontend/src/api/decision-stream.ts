import { ApiError } from "@/api/client";
import {
  type DecisionApiRecord,
  mapDecisionApiRecord,
} from "@/api/decision-contracts";
import {
  DECISION_UPSERT_EVENT,
  type DecisionEvent,
} from "@/domain/decision-events";

interface DecisionStreamPayload {
  type: string;
  decision: DecisionApiRecord;
}

interface SubscribeDecisionEventsInput {
  token: string;
  onEvent: (event: DecisionEvent) => void;
  onError: (error: Error) => void;
}

function parseEventChunk(chunk: string): DecisionEvent | null {
  const lines = chunk
    .split("\n")
    .map((line) => line.trim())
    .filter((line) => line.length > 0);

  let eventType = "";
  let data = "";

  for (const line of lines) {
    if (line.startsWith("event:")) {
      eventType = line.slice(6).trim();
    }
    if (line.startsWith("data:")) {
      data = line.slice(5).trim();
    }
  }

  if (!eventType || !data) {
    return null;
  }

  if (eventType !== DECISION_UPSERT_EVENT) {
    return null;
  }

  const payload = JSON.parse(data) as DecisionStreamPayload;

  if (!payload.decision) {
    return null;
  }

  return {
    type: DECISION_UPSERT_EVENT,
    decision: mapDecisionApiRecord(payload.decision),
  };
}

export function subscribeToDecisionEvents({
  token,
  onEvent,
  onError,
}: SubscribeDecisionEventsInput): () => void {
  const controller = new AbortController();
  let closed = false;

  const startStream = async () => {
    const response = await fetch("/api/v1/decisions/stream/", {
      method: "GET",
      headers: {
        Accept: "text/event-stream",
        Authorization: `Bearer ${token}`,
      },
      cache: "no-store",
      signal: controller.signal,
    });

    if (!response.ok) {
      const requestId = response.headers.get("X-Request-ID");
      throw new ApiError("Decision stream failed", response.status, requestId);
    }

    if (!response.body) {
      throw new Error("Decision stream is unavailable");
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";

    while (!closed) {
      const read = await reader.read();
      if (read.done) {
        break;
      }

      buffer += decoder.decode(read.value, { stream: true });

      let splitIndex = buffer.indexOf("\n\n");
      while (splitIndex >= 0) {
        const chunk = buffer.slice(0, splitIndex);
        buffer = buffer.slice(splitIndex + 2);
        const event = parseEventChunk(chunk);
        if (event) {
          onEvent(event);
        }

        splitIndex = buffer.indexOf("\n\n");
      }
    }
  };

  void startStream().catch((error: Error) => {
    if (!closed && error.name !== "AbortError") {
      onError(error);
    }
  });

  return () => {
    closed = true;
    controller.abort();
  };
}
