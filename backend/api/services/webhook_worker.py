"""Async webhook delivery worker logic."""

import logging
from datetime import timedelta

import httpx
from django.db import transaction
from django.utils import timezone

from api.models import WebhookDelivery, WebhookDeliveryAttempt
from api.services.webhook_signing import build_signature_headers

logger = logging.getLogger(__name__)

REQUEST_TIMEOUT_SECONDS = 10
BASE_RETRY_DELAY_SECONDS = 30


def _next_retry_at(attempt_number: int):
    return timezone.now() + timedelta(seconds=BASE_RETRY_DELAY_SECONDS * attempt_number)


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
            **build_signature_headers(payload=payload, secret=delivery.subscription.signing_secret),
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
                delivery.status = WebhookDelivery.Status.FAILED
                delivery.next_retry_at = None
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

        should_retry = response.status_code >= 500 and attempt_number < delivery.max_attempts
        if should_retry:
            delivery.status = WebhookDelivery.Status.PENDING
            delivery.next_retry_at = _next_retry_at(attempt_number)
        else:
            delivery.status = WebhookDelivery.Status.FAILED
            delivery.next_retry_at = None

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
