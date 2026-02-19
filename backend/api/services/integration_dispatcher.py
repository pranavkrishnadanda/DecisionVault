"""Integration dispatcher service."""

from __future__ import annotations

import logging
from typing import Iterable

import pika
from django.db import transaction

from api.models import (
    Integration,
    IntegrationDelivery,
    IntegrationTrigger,
    Organization,
)
from core.constants import INTEGRATION_DELIVERY_QUEUE
from core.rabbitmq import RabbitMQClient

logger = logging.getLogger(__name__)


class IntegrationQueueClient(RabbitMQClient):
    QUEUE_NAME = INTEGRATION_DELIVERY_QUEUE


def enqueue_integration_delivery(delivery_id: str) -> bool:
    message = {
        "type": "integration.delivery",
        "payload": {"delivery_id": delivery_id},
    }

    try:
        client = IntegrationQueueClient()
        client.publish(message)
        client.close()
        return True
    except pika.exceptions.AMQPError:
        logger.exception(
            "Integration delivery enqueue failed",
            extra={"delivery_id": delivery_id},
        )
        return False


def _matching_triggers(
    organization: Organization, event_type: str
) -> Iterable[IntegrationTrigger]:
    return (
        IntegrationTrigger.objects.select_related("integration")
        .filter(
            organization=organization,
            event_type=event_type,
            is_active=True,
            integration__is_active=True,
        )
        .only(
            "id",
            "organization_id",
            "integration_id",
            "event_type",
            "message_template",
        )
    )


@transaction.atomic
def dispatch_event_to_integrations(
    *, organization: Organization, event_type: str, payload: dict
) -> int:
    triggers = list(_matching_triggers(organization, event_type))
    if not triggers:
        return 0

    deliveries = [
        IntegrationDelivery(
            organization=organization,
            integration=trigger.integration,
            trigger=trigger,
            event_type=event_type,
            payload=payload,
        )
        for trigger in triggers
    ]

    created = IntegrationDelivery.objects.bulk_create(deliveries)
    for delivery in created:
        enqueue_integration_delivery(str(delivery.id))

    logger.info(
        "Integration deliveries scheduled",
        extra={
            "organization_id": str(organization.id),
            "event_type": event_type,
            "delivery_count": len(created),
        },
    )
    return len(created)
