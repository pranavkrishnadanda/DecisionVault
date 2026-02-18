"""Queue contract tests for canonical RabbitMQ queue usage.

These tests enforce architectural alignment on a single queue name:
`decision_tasks`.
"""

import json
from unittest.mock import MagicMock, patch

import pika
import pytest
from django.conf import settings

from core.constants import DECISION_TASKS_QUEUE
from core.rabbitmq import RabbitMQClient
from decisions.services import RabbitMQService


class TestCanonicalQueueDefinition:
    """Ensure queue name is defined once and reused everywhere."""

    def test_canonical_queue_value_is_decision_tasks(self):
        """Canonical queue value must match architecture contract."""
        assert DECISION_TASKS_QUEUE == "decision_tasks"

    def test_core_rabbitmq_client_uses_canonical_queue_name(self):
        """core.rabbitmq must use canonical queue definition."""
        assert RabbitMQClient.QUEUE_NAME == DECISION_TASKS_QUEUE

    def test_decisions_rabbitmq_service_uses_canonical_queue_name(self):
        """decisions.services must use canonical queue definition."""
        assert RabbitMQService.QUEUE_NAME == DECISION_TASKS_QUEUE


class TestRabbitMQServiceUnit:
    """Unit tests for decisions.services RabbitMQ publishing."""

    @patch("decisions.services.pika.BlockingConnection")
    def test_publish_declares_and_routes_to_canonical_queue(self, mock_connection_cls):
        """Publish path must declare and route to canonical queue."""
        mock_connection = MagicMock()
        mock_channel = MagicMock()
        mock_connection.channel.return_value = mock_channel
        mock_connection.is_closed = False
        mock_channel.is_closed = False
        mock_connection_cls.return_value = mock_connection

        service = RabbitMQService(host="localhost", port=5672)

        published = service.publish("123e4567-e89b-12d3-a456-426614174000")

        assert published is True
        mock_channel.queue_declare.assert_called_once_with(
            queue=DECISION_TASKS_QUEUE,
            durable=True,
        )

        _, publish_kwargs = mock_channel.basic_publish.call_args
        assert publish_kwargs["routing_key"] == DECISION_TASKS_QUEUE

        payload = json.loads(publish_kwargs["body"])
        assert (
            payload["payload"]["decision_id"] == "123e4567-e89b-12d3-a456-426614174000"
        )

    @patch("decisions.services.pika.BlockingConnection")
    def test_publish_returns_false_when_rabbitmq_is_unavailable(
        self, mock_connection_cls
    ):
        """Publish should fail closed if broker connection cannot be established."""
        mock_connection_cls.side_effect = pika.exceptions.AMQPConnectionError()

        service = RabbitMQService(host="localhost", port=5672)

        assert service.publish("123e4567-e89b-12d3-a456-426614174000") is False


@pytest.mark.django_db
class TestRabbitMQServiceIntegration:
    """Integration tests using a real RabbitMQ instance."""

    @pytest.fixture(autouse=True)
    def purge_queue(self):
        """Purge canonical queue before/after each integration test."""
        connection = pika.BlockingConnection(
            pika.ConnectionParameters(
                host=settings.RABBITMQ_HOST,
                port=settings.RABBITMQ_PORT,
            )
        )
        channel = connection.channel()
        channel.queue_declare(queue=DECISION_TASKS_QUEUE, durable=True)
        channel.queue_purge(queue=DECISION_TASKS_QUEUE)
        connection.close()

        yield

        connection = pika.BlockingConnection(
            pika.ConnectionParameters(
                host=settings.RABBITMQ_HOST,
                port=settings.RABBITMQ_PORT,
            )
        )
        channel = connection.channel()
        channel.queue_purge(queue=DECISION_TASKS_QUEUE)
        connection.close()

    def test_publish_and_consume_from_canonical_queue(self):
        """Decision publisher must emit messages into decision_tasks queue."""
        service = RabbitMQService(
            host=settings.RABBITMQ_HOST,
            port=settings.RABBITMQ_PORT,
        )
        decision_id = "123e4567-e89b-12d3-a456-426614174000"

        published = service.publish(decision_id)
        assert published is True

        connection = pika.BlockingConnection(
            pika.ConnectionParameters(
                host=settings.RABBITMQ_HOST,
                port=settings.RABBITMQ_PORT,
            )
        )
        channel = connection.channel()

        method_frame, _, body = channel.basic_get(
            queue=DECISION_TASKS_QUEUE,
            auto_ack=True,
        )

        assert method_frame is not None
        message = json.loads(body)
        assert message["type"] == "decision.process"
        assert message["payload"]["decision_id"] == decision_id
        connection.close()
