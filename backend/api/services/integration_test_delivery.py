from __future__ import annotations

from django.utils import timezone

from api.models import Integration, IntegrationDelivery, IntegrationDeliveryAttempt
from api.services.integration_connectors import (
    SlackServiceError,
    send_slack_test_message,
)


def run_slack_test_delivery(
    integration: Integration, *, channel_id: str
) -> IntegrationDelivery:
    delivery = IntegrationDelivery.objects.create(
        organization=integration.organization,
        integration=integration,
        event_type="integration.test",
        payload={"channel_id": channel_id},
        max_attempts=1,
    )

    attempt_number = 1
    try:
        response_status = send_slack_test_message(integration, channel_id=channel_id)
    except SlackServiceError as exc:
        IntegrationDeliveryAttempt.objects.create(
            organization=delivery.organization,
            delivery=delivery,
            attempt_number=attempt_number,
            status=IntegrationDeliveryAttempt.Status.FAILED,
            response_status=None,
            error_message=exc.message,
        )
        delivery.status = IntegrationDelivery.Status.FAILED
        delivery.attempt_count = attempt_number
        delivery.last_attempt_at = timezone.now()
        delivery.last_response_status = None
        delivery.last_error = exc.message
        delivery.save(
            update_fields=[
                "status",
                "attempt_count",
                "last_attempt_at",
                "last_response_status",
                "last_error",
                "updated_at",
            ]
        )
        integration.last_error = exc.message
        integration.save(update_fields=["last_error", "updated_at"])
        raise

    IntegrationDeliveryAttempt.objects.create(
        organization=delivery.organization,
        delivery=delivery,
        attempt_number=attempt_number,
        status=IntegrationDeliveryAttempt.Status.SUCCESS,
        response_status=response_status,
        error_message="",
    )
    delivery.status = IntegrationDelivery.Status.DELIVERED
    delivery.attempt_count = attempt_number
    delivery.last_attempt_at = timezone.now()
    delivery.last_response_status = response_status
    delivery.last_error = ""
    delivery.save(
        update_fields=[
            "status",
            "attempt_count",
            "last_attempt_at",
            "last_response_status",
            "last_error",
            "updated_at",
        ]
    )
    integration.last_error = ""
    integration.save(update_fields=["last_error", "updated_at"])
    return delivery
