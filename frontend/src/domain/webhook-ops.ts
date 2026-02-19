export interface BreakerStatus {
  open: number;
  closed: number;
}

export interface WebhookMetrics {
  deliverySuccessRate: number;
  retryCount: number;
  dlqCount: number;
  breakerStatus: BreakerStatus;
}

export interface WebhookDeliverySummary {
  id: string;
  eventType: string;
  status: string;
  attemptCount: number;
  maxAttempts: number;
  createdAt: string;
  updatedAt: string;
}

export interface WebhookTimelineEvent {
  type: string;
  timestamp: string;
  attemptNumber?: number;
  status?: string;
  attemptDelaySeconds?: number | null;
  event?: string;
}

export interface WebhookTimeline {
  deliveryId: string;
  status: string;
  events: WebhookTimelineEvent[];
}
