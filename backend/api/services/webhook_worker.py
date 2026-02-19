"""Async webhook delivery worker logic."""

import logging
from datetime import timedelta

import httpx
from django.db import transaction
from django.utils import timezone

from api.models import (
    INTEGRATION_EVENT_WEBHOOK_FAILED,
    WebhookDelivery,
    WebhookDeliveryAttempt,
)
from api.services.integration_dispatcher import dispatch_event_to_integrations
from api.services.webhook_dispatcher import enqueue_webhook_dead_letter
from api.services.webhook_observability import (
    log_delivery_event,
    log_subscription_event,
)
from api.services.webhook_signing import build_signature_headers

logger = logging.getLogger(__name__)

REQUEST_TIMEOUT_SECONDS = 10
BASE_RETRY_DELAY_SECONDS = 30
RATE_LIMIT_WINDOW_SECONDS = 60
SUBSCRIPTION_RATE_LIMIT_PER_WINDOW = 60
CIRCUIT_BREAKER_WINDOW_SECONDS = 300
CIRCUIT_BREAKER_FAILURE_THRESHOLD = 5


def _next_retry_at(attempt_number: int):
    backoff_seconds = BASE_RETRY_DELAY_SECONDS * (2 ** (attempt_number - 1))
    return timezone.now() + timedelta(seconds=backoff_seconds)


def _record_attempt(
    delivery: WebhookDelivery,
    attempt_number: int,
    status: str,
    response_status: int | None = None,
    response_request_id: str = "",
    error_message: str = "",
) -> None:
    WebhookDeliveryAttempt.objects.create(
        organization=delivery.organization,
        delivery=delivery,
        attempt_number=attempt_number,
        status=status,
        response_status=response_status,
        response_request_id=response_request_id,
        error_message=error_message,
    )


def _is_rate_limited(delivery: WebhookDelivery) -> bool:
    window_floor = timezone.now() - timedelta(seconds=RATE_LIMIT_WINDOW_SECONDS)
    attempts = WebhookDeliveryAttempt.objects.filter(
        organization=delivery.organization,
        delivery__subscription=delivery.subscription,
        created_at__gte=window_floor,
    ).count()
    return attempts >= SUBSCRIPTION_RATE_LIMIT_PER_WINDOW


def _apply_circuit_breaker_on_failure(delivery: WebhookDelivery) -> None:
    window_floor = timezone.now() - timedelta(seconds=CIRCUIT_BREAKER_WINDOW_SECONDS)
    recent_failures = WebhookDeliveryAttempt.objects.filter(
        organization=delivery.organization,
        delivery__subscription=delivery.subscription,
        status=WebhookDeliveryAttempt.Status.FAILED,
        created_at__gte=window_floor,
    ).count()
    if recent_failures >= CIRCUIT_BREAKER_FAILURE_THRESHOLD:
        previous_is_active = delivery.subscription.is_active
        delivery.subscription.is_active = False
        delivery.subscription.save(update_fields=["is_active", "updated_at"])
        if previous_is_active:
            log_subscription_event(
                subscription=delivery.subscription,
                event="breaker_open",
                actor_type="system",
                actor_id="",
                previous_state={"is_active": previous_is_active},
                current_state={"is_active": delivery.subscription.is_active},
                metadata={"recent_failures": recent_failures},
            )
        logger.error(
            "Webhook subscription auto-disabled by circuit breaker",
            extra={
                "subscription_id": str(delivery.subscription_id),
                "organization_id": str(delivery.organization_id),
                "recent_failures": recent_failures,
            },
        )


def _finalize_terminal_failure(delivery: WebhookDelivery, reason: str) -> None:
    delivery.status = WebhookDelivery.Status.FAILED
    delivery.next_retry_at = None
    delivery.last_error = reason
    delivery.save(
        update_fields=[
            "attempt_count",
            "last_attempt_at",
            "last_response_status",
            "status",
            "next_retry_at",
            "last_error",
            "updated_at",
        ]
    )
    enqueue_webhook_dead_letter(str(delivery.id), reason=reason)
    log_delivery_event(
        delivery=delivery,
        event="dlq_routed",
        actor_type="system",
        actor_id="",
        previous_state=None,
        current_state={"status": delivery.status},
        metadata={"reason": reason},
    )
    dispatch_event_to_integrations(
        organization=delivery.organization,
        event_type=INTEGRATION_EVENT_WEBHOOK_FAILED,
        payload={
            "delivery_id": str(delivery.id),
            "subscription_id": str(delivery.subscription_id),
            "reason": reason,
        },
    )


def process_webhook_delivery(delivery_id: str) -> bool:
    with transaction.atomic():
        delivery = (
            WebhookDelivery.objects.select_related("organization", "subscription")
            .select_for_update()
            .filter(id=delivery_id)
            .first()
        )
        if delivery is None or delivery.status != WebhookDelivery.Status.PENDING:
            return False
        if not delivery.subscription.is_active:
            _finalize_terminal_failure(delivery, reason="subscription_inactive")
            return False
        if delivery.next_retry_at and delivery.next_retry_at > timezone.now():
            return False
        if _is_rate_limited(delivery):
            delivery.next_retry_at = timezone.now() + timedelta(seconds=5)
            delivery.save(update_fields=["next_retry_at", "updated_at"])
            log_delivery_event(
                delivery=delivery,
                event="throttled",
                actor_type="system",
                actor_id="",
                previous_state=None,
                current_state={"status": delivery.status},
                metadata={"reason": "rate_limit"},
            )
            return False

        attempt_number = delivery.attempt_count + 1
        delivery.attempt_count = attempt_number
        delivery.last_attempt_at = timezone.now()

        payload = {
            "event": delivery.event_type,
            "delivery_id": str(delivery.id),
            "data": delivery.payload,
        }
        headers = {
            "Content-Type": "application/json",
            **build_signature_headers(
                payload=payload, secret=delivery.subscription.signing_secret
            ),
        }

        try:
            with httpx.Client(timeout=REQUEST_TIMEOUT_SECONDS) as client:
                response = client.post(
                    delivery.subscription.target_url,
                    json=payload,
                    headers=headers,
                )
        except httpx.TimeoutException as exc:
            error_message = str(exc) or "timeout"
            _record_attempt(
                delivery=delivery,
                attempt_number=attempt_number,
                status=WebhookDeliveryAttempt.Status.FAILED,
                error_message=error_message,
            )
            delivery.last_error = error_message
            delivery.last_response_status = None
            if attempt_number >= delivery.max_attempts:
                _finalize_terminal_failure(delivery, reason=error_message)
            else:
                delivery.status = WebhookDelivery.Status.PENDING
                delivery.next_retry_at = _next_retry_at(attempt_number)
                delivery.save(
                    update_fields=[
                        "attempt_count",
                        "last_attempt_at",
                        "status",
                        "next_retry_at",
                        "last_error",
                        "last_response_status",
                        "updated_at",
                    ]
                )
            _apply_circuit_breaker_on_failure(delivery)
            logger.warning(
                "Webhook delivery timeout",
                extra={
                    "delivery_id": str(delivery.id),
                    "attempt": attempt_number,
                    "status": delivery.status,
                },
            )
            return False

        response_request_id = response.headers.get("X-Request-ID", "")
        delivery.last_response_status = response.status_code

        if 200 <= response.status_code < 300:
            _record_attempt(
                delivery=delivery,
                attempt_number=attempt_number,
                status=WebhookDeliveryAttempt.Status.SUCCESS,
                response_status=response.status_code,
                response_request_id=response_request_id,
            )
            delivery.status = WebhookDelivery.Status.DELIVERED
            delivery.next_retry_at = None
            delivery.last_error = ""
            delivery.save(
                update_fields=[
                    "attempt_count",
                    "last_attempt_at",
                    "status",
                    "next_retry_at",
                    "last_error",
                    "last_response_status",
                    "updated_at",
                ]
            )
            if delivery.subscription.is_active:
                # Success closes breaker failure streak by definition.
                pass
            return True

        error_message = f"http_{response.status_code}"
        _record_attempt(
            delivery=delivery,
            attempt_number=attempt_number,
            status=WebhookDeliveryAttempt.Status.FAILED,
            response_status=response.status_code,
            response_request_id=response_request_id,
            error_message=error_message,
        )

        should_retry = (
            response.status_code >= 500 and attempt_number < delivery.max_attempts
        )
        if should_retry:
            delivery.status = WebhookDelivery.Status.PENDING
            delivery.next_retry_at = _next_retry_at(attempt_number)
            delivery.last_error = error_message
            delivery.save(
                update_fields=[
                    "attempt_count",
                    "last_attempt_at",
                    "status",
                    "next_retry_at",
                    "last_error",
                    "last_response_status",
                    "updated_at",
                ]
            )
        else:
            _finalize_terminal_failure(delivery, reason=error_message)
        _apply_circuit_breaker_on_failure(delivery)

        logger.warning(
            "Webhook delivery request failed",
            extra={
                "delivery_id": str(delivery.id),
                "attempt": attempt_number,
                "response_status": response.status_code,
                "status": delivery.status,
                "request_id": response_request_id,
            },
        )
        return False
