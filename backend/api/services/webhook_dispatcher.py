"""Webhook dispatcher service.

Creates persistent delivery jobs and enqueues async processing.
"""

import logging
from typing import Iterable

import pika
from django.db import transaction

from api.models import Organization, WebhookDelivery, WebhookSubscription
from core.constants import WEBHOOK_DELIVERY_QUEUE
from core.rabbitmq import RabbitMQClient

logger = logging.getLogger(__name__)


class WebhookQueueClient(RabbitMQClient):
    QUEUE_NAME = WEBHOOK_DELIVERY_QUEUE


def enqueue_webhook_delivery(delivery_id: str) -> bool:
    message = {
        "type": "webhook.delivery",
        "payload": {"delivery_id": delivery_id},
    }

    try:
        client = WebhookQueueClient()
        client.publish(message)
        client.close()
        return True
    except pika.exceptions.AMQPError:
        logger.exception(
            "Webhook delivery enqueue failed", extra={"delivery_id": delivery_id}
        )
        return False


def _matching_subscriptions(
    organization: Organization, event_type: str
) -> Iterable[WebhookSubscription]:
    return WebhookSubscription.objects.filter(
        organization=organization,
        is_active=True,
        events__contains=[event_type],
    ).only("id", "organization_id")


@transaction.atomic
def dispatch_event_to_webhooks(
    organization: Organization, event_type: str, payload: dict
) -> int:
    subscriptions = list(_matching_subscriptions(organization, event_type))
    if not subscriptions:
        return 0

    deliveries = [
        WebhookDelivery(
            organization=organization,
            subscription=subscription,
            event_type=event_type,
            payload=payload,
        )
        for subscription in subscriptions
    ]

    created_deliveries = WebhookDelivery.objects.bulk_create(deliveries)
    for delivery in created_deliveries:
        enqueue_webhook_delivery(str(delivery.id))

    logger.info(
        "Webhook deliveries scheduled",
        extra={
            "organization_id": str(organization.id),
            "event_type": event_type,
            "delivery_count": len(created_deliveries),
        },
    )
    return len(created_deliveries)


@transaction.atomic
def replay_webhook_delivery(delivery: WebhookDelivery) -> bool:
    """
    Replay failed delivery by re-queuing the same delivery record.

    Ensures there is at least one additional allowed attempt for the worker.
    """
    locked_delivery = (
        WebhookDelivery.objects.select_for_update().filter(id=delivery.id).first()
    )
    if locked_delivery is None:
        return False

    if locked_delivery.status != WebhookDelivery.Status.FAILED:
        raise ValueError("Only failed deliveries can be replayed.")

    if locked_delivery.attempt_count >= locked_delivery.max_attempts:
        locked_delivery.max_attempts = locked_delivery.attempt_count + 1

    locked_delivery.status = WebhookDelivery.Status.PENDING
    locked_delivery.next_retry_at = None
    locked_delivery.save(
        update_fields=[
            "status",
            "next_retry_at",
            "max_attempts",
            "updated_at",
        ]
    )
    return enqueue_webhook_delivery(str(locked_delivery.id))
