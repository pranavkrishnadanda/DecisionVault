"""Webhook observability and recovery services."""

from __future__ import annotations

from typing import Any

from django.db import transaction
from django.db.models import Case, Count, F, IntegerField, Q, Sum, Value, When
from django.db.models.functions import Coalesce

from api.models import Organization, WebhookDelivery, WebhookSubscription
from decisions.models import AuditAction, AuditLog


def log_delivery_event(
    *,
    delivery: WebhookDelivery,
    event: str,
    actor_type: str,
    actor_id: str,
    previous_state: dict[str, Any] | None,
    current_state: dict[str, Any] | None,
    metadata: dict[str, Any] | None = None,
) -> AuditLog:
    return AuditLog.objects.create(
        organization=delivery.organization,
        entity_type="webhook_delivery",
        entity_id=delivery.id,
        action=AuditAction.UPDATE,
        actor_type=actor_type,
        actor_id=actor_id,
        previous_state=previous_state,
        current_state=current_state,
        metadata={"event": event, **(metadata or {})},
    )


def log_subscription_event(
    *,
    subscription: WebhookSubscription,
    event: str,
    actor_type: str,
    actor_id: str,
    previous_state: dict[str, Any] | None,
    current_state: dict[str, Any] | None,
    metadata: dict[str, Any] | None = None,
) -> AuditLog:
    return AuditLog.objects.create(
        organization=subscription.organization,
        entity_type="webhook_subscription",
        entity_id=subscription.id,
        action=AuditAction.UPDATE,
        actor_type=actor_type,
        actor_id=actor_id,
        previous_state=previous_state,
        current_state=current_state,
        metadata={"event": event, **(metadata or {})},
    )


def compute_webhook_metrics(*, organization: Organization) -> dict[str, Any]:
    queryset = WebhookDelivery.objects.filter(organization=organization)
    total_count = queryset.count()
    delivered_count = queryset.filter(status=WebhookDelivery.Status.DELIVERED).count()

    retry_count = (
        queryset.aggregate(
            total=Coalesce(
                Sum(
                    Case(
                        When(attempt_count__gt=1, then=F("attempt_count") - Value(1)),
                        default=Value(0),
                        output_field=IntegerField(),
                    )
                ),
                Value(0),
            )
        )["total"]
        or 0
    )

    dlq_count = queryset.filter(
        status=WebhookDelivery.Status.FAILED,
        attempt_count__gte=F("max_attempts"),
    ).count()

    breaker_status = WebhookSubscription.objects.filter(
        organization=organization
    ).aggregate(
        open=Count("id", filter=Q(is_active=False)),
        closed=Count("id", filter=Q(is_active=True)),
    )

    if total_count == 0:
        success_rate = 0.0
    else:
        success_rate = round((delivered_count / total_count) * 100, 2)

    return {
        "delivery_success_rate": success_rate,
        "retry_count": int(retry_count),
        "dlq_count": int(dlq_count),
        "breaker_status": {
            "open": int(breaker_status.get("open", 0) or 0),
            "closed": int(breaker_status.get("closed", 0) or 0),
        },
    }


def build_delivery_timeline(*, delivery: WebhookDelivery) -> dict[str, Any]:
    attempts = list(delivery.attempts.all().order_by("attempt_number", "created_at"))
    events: list[dict[str, Any]] = []

    previous_timestamp = None
    for attempt in attempts:
        delay_seconds = None
        if previous_timestamp is not None:
            delay_seconds = max(
                0,
                int((attempt.created_at - previous_timestamp).total_seconds()),
            )

        events.append(
            {
                "type": "attempt",
                "timestamp": attempt.created_at.isoformat(),
                "attempt_number": attempt.attempt_number,
                "status": attempt.status,
                "response_status": attempt.response_status,
                "error_message": attempt.error_message,
                "attempt_delay_seconds": delay_seconds,
            }
        )
        previous_timestamp = attempt.created_at

    audit_logs = AuditLog.objects.filter(
        organization=delivery.organization,
        entity_type="webhook_delivery",
        entity_id=delivery.id,
    ).order_by("timestamp")

    for audit in audit_logs:
        event_name = (audit.metadata or {}).get("event", "")
        if event_name == "throttled":
            event_type = "throttle"
        else:
            event_type = "audit"
        events.append(
            {
                "type": event_type,
                "timestamp": audit.timestamp.isoformat(),
                "event": event_name,
                "metadata": audit.metadata,
                "actor_type": audit.actor_type,
            }
        )

    events.sort(key=lambda item: item["timestamp"])

    return {
        "delivery_id": str(delivery.id),
        "status": delivery.status,
        "events": events,
    }


@transaction.atomic
def force_retry_delivery(
    *, delivery: WebhookDelivery, actor_id: str
) -> WebhookDelivery:
    from api.services.webhook_dispatcher import replay_webhook_delivery

    previous = {"status": delivery.status, "max_attempts": delivery.max_attempts}
    replay_webhook_delivery(delivery)
    delivery.refresh_from_db()

    log_delivery_event(
        delivery=delivery,
        event="force_retry",
        actor_type="user",
        actor_id=actor_id,
        previous_state=previous,
        current_state={
            "status": delivery.status,
            "max_attempts": delivery.max_attempts,
        },
    )
    return delivery


@transaction.atomic
def reactivate_webhook_subscription(
    *, subscription: WebhookSubscription, actor_id: str
) -> WebhookSubscription:
    previous = {"is_active": subscription.is_active}
    subscription.is_active = True
    subscription.save(update_fields=["is_active", "updated_at"])

    log_subscription_event(
        subscription=subscription,
        event="reactivated",
        actor_type="user",
        actor_id=actor_id,
        previous_state=previous,
        current_state={"is_active": subscription.is_active},
    )
    return subscription
