"""Async integration delivery worker logic."""

from __future__ import annotations

import logging
from datetime import timedelta

from django.db import transaction
from django.utils import timezone

from api.models import IntegrationDelivery, IntegrationDeliveryAttempt
from api.services.integration_connectors import send_integration_message

logger = logging.getLogger(__name__)

BASE_RETRY_DELAY_SECONDS = 30


def _next_retry_at(attempt_number: int):
    delay = BASE_RETRY_DELAY_SECONDS * (2 ** (attempt_number - 1))
    return timezone.now() + timedelta(seconds=delay)


def _record_attempt(
    *,
    delivery: IntegrationDelivery,
    attempt_number: int,
    status: str,
    response_status: int | None = None,
    error_message: str = "",
) -> None:
    IntegrationDeliveryAttempt.objects.create(
        organization=delivery.organization,
        delivery=delivery,
        attempt_number=attempt_number,
        status=status,
        response_status=response_status,
        error_message=error_message,
    )


def process_integration_delivery(delivery_id: str) -> bool:
    with transaction.atomic():
        delivery = (
            IntegrationDelivery.objects.select_related("organization", "integration")
            .select_for_update()
            .filter(id=delivery_id)
            .first()
        )
        if delivery is None or delivery.status != IntegrationDelivery.Status.PENDING:
            return False
        if not delivery.integration.is_active:
            delivery.status = IntegrationDelivery.Status.FAILED
            delivery.last_error = "integration_inactive"
            delivery.save(update_fields=["status", "last_error", "updated_at"])
            return False
        if delivery.next_retry_at and delivery.next_retry_at > timezone.now():
            return False

        attempt_number = delivery.attempt_count + 1
        delivery.attempt_count = attempt_number
        delivery.last_attempt_at = timezone.now()

        try:
            response_status = send_integration_message(
                delivery.integration,
                event_type=delivery.event_type,
                payload=delivery.payload,
            )
        except Exception as exc:  # noqa: BLE001
            error_message = str(exc) or "delivery_failed"
            _record_attempt(
                delivery=delivery,
                attempt_number=attempt_number,
                status=IntegrationDeliveryAttempt.Status.FAILED,
                error_message=error_message,
            )
            delivery.last_response_status = None
            delivery.last_error = error_message

            if attempt_number >= delivery.max_attempts:
                delivery.status = IntegrationDelivery.Status.FAILED
                delivery.next_retry_at = None
            else:
                delivery.status = IntegrationDelivery.Status.PENDING
                delivery.next_retry_at = _next_retry_at(attempt_number)

            delivery.integration.last_error = error_message
            delivery.integration.save(update_fields=["last_error", "updated_at"])
            delivery.save(
                update_fields=[
                    "attempt_count",
                    "last_attempt_at",
                    "last_response_status",
                    "last_error",
                    "status",
                    "next_retry_at",
                    "updated_at",
                ]
            )
            logger.warning(
                "Integration delivery failed",
                extra={
                    "delivery_id": str(delivery.id),
                    "attempt": attempt_number,
                    "status": delivery.status,
                },
            )
            return False

        _record_attempt(
            delivery=delivery,
            attempt_number=attempt_number,
            status=IntegrationDeliveryAttempt.Status.SUCCESS,
            response_status=response_status,
        )
        delivery.status = IntegrationDelivery.Status.DELIVERED
        delivery.next_retry_at = None
        delivery.last_response_status = response_status
        delivery.last_error = ""
        delivery.integration.last_error = ""
        delivery.integration.save(update_fields=["last_error", "updated_at"])
        delivery.save(
            update_fields=[
                "attempt_count",
                "last_attempt_at",
                "last_response_status",
                "last_error",
                "status",
                "next_retry_at",
                "updated_at",
            ]
        )
        return True
